#!/usr/bin/env python3
"""
Edict Agent 通信代理 - 企业级可靠性
支持: 超时配置化、指数退避、备用Agent、心跳检测、失败告警
"""
import os
import sys
import time
import json
import subprocess
import logging
from pathlib import Path
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Optional, Any
import threading

BASE = Path(__file__).parent.parent
sys.path.insert(0, str(BASE / 'scripts'))

logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s [%(name)s] %(levelname)s: %(message)s', 
    datefmt='%H:%M:%S'
)
log = logging.getLogger('agent-comm')

# ==================== 配置 ====================
class Config:
    """环境配置"""
    # 超时配置
    DEFAULT_TIMEOUT = int(os.getenv('AGENT_TIMEOUT', '30'))
    MAX_RETRIES = int(os.getenv('AGENT_MAX_RETRIES', '3'))
    BASE_DELAY = float(os.getenv('AGENT_BASE_DELAY', '2.0'))
    HEARTBEAT_INTERVAL = int(os.getenv('AGENT_HEARTBEAT_INTERVAL', '30'))
    
    # 告警配置
    ENABLE_ALERT = os.getenv('AGENT_ENABLE_ALERT', 'true').lower() == 'true'
    ALERT_WEBHOOK = os.getenv('AGENT_ALERT_WEBHOOK', '')
    
    # 备用Agent
    FALLBACK_AGENTS = json.loads(os.getenv('AGENT_FALLBACKS', '{}'))

config = Config()

# ==================== 数据类 ====================
class AgentStatus(Enum):
    IDLE = "idle"
    CALLING = "calling"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    UNREACHABLE = "unreachable"
    HEARTBEAT_LOST = "heartbeat_lost"

@dataclass
class AgentCallResult:
    success: bool
    status: AgentStatus
    response: Optional[str] = None
    error: Optional[str] = None
    duration_ms: int = 0
    retries: int = 0
    agent_id: str = ""

@dataclass  
class AgentHeartbeat:
    agent_id: str
    last_beat: float = field(default_factory=time.time)
    status: AgentStatus = AgentStatus.IDLE
    task_id: Optional[str] = None

# ==================== 核心类 ====================
class AgentCommunicator:
    """企业级Agent通信代理"""
    
    def __init__(self):
        self.agent_status: dict[str, AgentStatus] = {}
        self.agent_heartbeats: dict[str, AgentHeartbeat] = {}
        self.call_history: list[dict] = []
        self._heartbeat_thread: Optional[threading.Thread] = None
        self._running = False
    
    # ---- 通信方法 ----
    def call_agent(
        self,
        agent_id: str,
        message: str,
        task_id: Optional[str] = None,
        subagent: bool = False,
        timeout: Optional[int] = None,
        max_retries: Optional[int] = None,
        fallback_agent: Optional[str] = None
    ) -> AgentCallResult:
        """调用Agent - 带重试、超时、备用"""
        
        timeout = timeout or config.DEFAULT_TIMEOUT
        max_retries = max_retries or config.MAX_RETRIES
        
        last_error = None
        start_time = time.time()
        
        for attempt in range(max_retries + 1):
            try:
                # 更新状态
                self.agent_status[agent_id] = AgentStatus.CALLING
                self._update_heartbeat(agent_id, task_id)
                
                # 执行调用
                result = self._execute_call(agent_id, message, subagent, timeout)
                
                # 成功
                duration_ms = int((time.time() - start_time) * 1000)
                self.agent_status[agent_id] = AgentStatus.SUCCESS
                
                call_result = AgentCallResult(
                    success=True,
                    status=AgentStatus.SUCCESS,
                    response=result,
                    duration_ms=duration_ms,
                    retries=attempt,
                    agent_id=agent_id
                )
                
                self._record_call(call_result)
                return call_result
                
            except subprocess.TimeoutExpired:
                last_error = f"调用超时 ({timeout}s)"
                self.agent_status[agent_id] = AgentStatus.TIMEOUT
                log.warning(f"{agent_id} 调用超时 (尝试 {attempt + 1}/{max_retries + 1})")
                
            except Exception as e:
                last_error = str(e)
                self.agent_status[agent_id] = AgentStatus.FAILED
                log.error(f"{agent_id} 调用失败: {e}")
            
            # 重试前等待 (指数退避)
            if attempt < max_retries:
                delay = config.BASE_DELAY * (2 ** attempt)
                log.info(f"等待 {delay}s 后重试...")
                time.sleep(delay)
        
        # 尝试备用Agent
        fallback = fallback_agent or config.FALLBACK_AGENTS.get(agent_id)
        if fallback and fallback != agent_id:
            log.info(f"尝试备用Agent: {fallback}")
            return self.call_agent(fallback, message, task_id, subagent, timeout, max_retries, None)
        
        # 失败 - 告警
        duration_ms = int((time.time() - start_time) * 1000)
        call_result = AgentCallResult(
            success=False,
            status=self.agent_status.get(agent_id, AgentStatus.FAILED),
            error=last_error,
            duration_ms=duration_ms,
            retries=max_retries,
            agent_id=agent_id
        )
        
        self._record_call(call_result)
        self._send_alert(agent_id, call_result)
        
        return call_result
    
    def _execute_call(self, agent_id: str, message: str, subagent: bool, timeout: int) -> str:
        """实际执行Agent调用"""
        
        cmd = ['openclaw', 'agent', '--agent', agent_id]
        
        if subagent:
            cmd.extend(['--subagent'])
        
        cmd.extend(['-m', message, '--timeout', str(timeout)])
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout + 10
        )
        
        if result.returncode != 0:
            raise RuntimeError(f"Agent调用失败: {result.stderr}")
        
        return result.stdout
    
    # ---- 心跳方法 ----
    def _update_heartbeat(self, agent_id: str, task_id: Optional[str] = None):
        """更新心跳"""
        self.agent_heartbeats[agent_id] = AgentHeartbeat(
            agent_id=agent_id,
            last_beat=time.time(),
            status=AgentStatus.SUCCESS,
            task_id=task_id
        )
    
    def check_heartbeats(self) -> dict[str, dict]:
        """检查所有Agent心跳状态"""
        now = time.time()
        results = {}
        
        for agent_id, hb in self.agent_heartbeats.items():
            elapsed = now - hb.last_beat
            is_alive = elapsed < config.HEARTBEAT_INTERVAL * 3
            
            if not is_alive:
                self.agent_status[agent_id] = AgentStatus.HEARTBEAT_LOST
                self._send_alert(agent_id, None, "heartbeat_lost")
            
            results[agent_id] = {
                'elapsed_sec': int(elapsed),
                'alive': is_alive,
                'status': self.agent_status.get(agent_id, AgentStatus.IDLE).value,
                'task_id': hb.task_id
            }
        
        return results
    
    def start_heartbeat_monitor(self, interval: int = None):
        """启动心跳监控线程"""
        interval = interval or config.HEARTBEAT_INTERVAL
        self._running = True
        
        def monitor():
            while self._running:
                time.sleep(interval)
                statuses = self.check_heartbeats()
                for agent_id, status in statuses.items():
                    if not status['alive']:
                        log.warning(f"Agent {agent_id} 心跳丢失!")
        
        self._heartbeat_thread = threading.Thread(target=monitor, daemon=True)
        self._heartbeat_thread.start()
        log.info(f"心跳监控已启动 (间隔{interval}s)")
    
    def stop_heartbeat_monitor(self):
        """停止心跳监控"""
        self._running = False
        if self._heartbeat_thread:
            self._heartbeat_thread.join(timeout=5)
    
    # ---- 告警方法 ----
    def _send_alert(self, agent_id: str, result: Optional[AgentCallResult], alert_type: str = "call_failed"):
        """发送告警"""
        if not config.ENABLE_ALERT:
            return
        
        alert_msg = {
            'agent_id': agent_id,
            'alert_type': alert_type,
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
        }
        
        if result:
            alert_msg.update({
                'success': result.success,
                'error': result.error,
                'duration_ms': result.duration_ms,
                'retries': result.retries
            })
        
        log.warning(f"告警: {alert_msg}")
        
        # TODO: 发送到飞书/钉钉Webhook
    
    # ---- 记录方法 ----
    def _record_call(self, result: AgentCallResult):
        """记录调用历史"""
        self.call_history.append(asdict(result))
        # 只保留最近1000条
        self.call_history = self.call_history[-1000:]
    
    # ---- 状态方法 ----
    def get_status(self) -> dict:
        """获取Agent状态"""
        return {
            'agents': {k: v.value for k, v in self.agent_status.items()},
            'heartbeats': self.check_heartbeats(),
            'call_stats': {
                'total': len(self.call_history),
                'success': sum(1 for c in self.call_history if c['success']),
                'failed': sum(1 for c in self.call_history if not c['success'])
            }
        }

# ==================== CLI ====================
def main():
    import argparse
    parser = argparse.ArgumentParser(description='Edict Agent通信代理')
    parser.add_argument('--agent', '-a', required=True, help='目标Agent ID')
    parser.add_argument('--message', '-m', required=True, help='发送的消息')
    parser.add_argument('--task', '-t', help='关联任务ID')
    parser.add_argument('--subagent', '-s', action='store_true', help='作为subagent调用')
    parser.add_argument('--timeout', type=int, default=config.DEFAULT_TIMEOUT, help='超时时间(秒)')
    parser.add_argument('--retries', type=int, default=config.MAX_RETRIES, help='最大重试次数')
    parser.add_argument('--fallback', '-f', help='备用Agent ID')
    parser.add_argument('--status', action='store_true', help='查看Agent状态')
    parser.add_argument('--monitor', action='store_true', help='启动心跳监控')
    
    args = parser.parse_args()
    
    comm = AgentCommunicator()
    
    if args.monitor:
        comm.start_heartbeat_monitor()
        print("心跳监控已启动，按Ctrl+C退出")
        try:
            while True: time.sleep(1)
        except KeyboardInterrupt:
            comm.stop_heartbeat_monitor()
        return
    
    if args.status:
        print(json.dumps(comm.get_status(), indent=2, ensure_ascii=False))
        return
    
    result = comm.call_agent(
        args.agent,
        args.message,
        task_id=args.task,
        subagent=args.subagent,
        timeout=args.timeout,
        max_retries=args.retries,
        fallback_agent=args.fallback
    )
    
    print(f"状态: {result.status.value}")
    print(f"耗时: {result.duration_ms}ms")
    print(f"重试: {result.retries}次")
    
    if result.success:
        print(f"响应: {result.response[:200] if result.response else ''}...")
    else:
        print(f"错误: {result.error}")
    
    sys.exit(0 if result.success else 1)

if __name__ == '__main__':
    main()
