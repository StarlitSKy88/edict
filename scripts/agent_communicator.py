#!/usr/bin/env python3
"""
Agent 通信代理 - 解决 Agent 唤起失败、任务卡死问题
"""
import os
import sys
import time
import json
import subprocess
import logging
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Callable, Any

BASE = Path(__file__).parent.parent
sys.path.insert(0, str(BASE / 'scripts'))

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(name)s] %(message)s', datefmt='%H:%M:%S')
log = logging.getLogger('agent-comm')

class AgentStatus(Enum):
    IDLE = "idle"
    CALLING = "calling"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    UNREACHABLE = "unreachable"

@dataclass
class AgentCallResult:
    success: bool
    status: AgentStatus
    response: Optional[str] = None
    error: Optional[str] = None
    duration_ms: int = 0
    retries: int = 0

class AgentCommunicator:
    """Agent 通信代理 - 带重试、超时、心跳检测"""
    
    def __init__(
        self,
        timeout: int = 30,
        max_retries: int = 3,
        base_delay: float = 2.0,
        heartbeat_interval: int = 30
    ):
        self.timeout = timeout
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.heartbeat_interval = heartbeat_interval
        
        self.agent_status: dict[str, AgentStatus] = {}
        self.agent_heartbeat: dict[str, float] = {}
        self.call_history: list[AgentCallResult] = []
        
    def call_agent(
        self,
        agent_id: str,
        message: str,
        subagent: bool = False,
        fallback_agent: Optional[str] = None
    ) -> AgentCallResult:
        """调用 Agent 带重试和超时"""
        
        last_error = None
        start_time = time.time()
        
        for attempt in range(self.max_retries + 1):
            try:
                self.agent_status[agent_id] = AgentStatus.CALLING
                self.agent_heartbeat[agent_id] = time.time()
                
                # 执行调用
                result = self._do_call(agent_id, message, subagent)
                
                duration_ms = int((time.time() - start_time) * 1000)
                self.agent_status[agent_id] = AgentStatus.SUCCESS
                
                call_result = AgentCallResult(
                    success=True,
                    status=AgentStatus.SUCCESS,
                    response=result,
                    duration_ms=duration_ms,
                    retries=attempt
                )
                
                self.call_history.append(call_result)
                return call_result
                
            except subprocess.TimeoutExpired:
                last_error = f"调用超时 ({self.timeout}s)"
                self.agent_status[agent_id] = AgentStatus.TIMEOUT
                log.warning(f"{agent_id} 调用超时 (尝试 {attempt + 1}/{self.max_retries + 1})")
                
            except Exception as e:
                last_error = str(e)
                self.agent_status[agent_id] = AgentStatus.FAILED
                log.error(f"{agent_id} 调用失败: {e}")
            
            if attempt < self.max_retries:
                delay = self.base_delay * (2 ** attempt)
                log.info(f"等待 {delay}s 后重试...")
                time.sleep(delay)
        
        # 尝试备用 Agent
        if fallback_agent and fallback_agent != agent_id:
            log.info(f"尝试备用 Agent: {fallback_agent}")
            return self.call_agent(fallback_agent, message, subagent, None)
        
        duration_ms = int((time.time() - start_time) * 1000)
        call_result = AgentCallResult(
            success=False,
            status=self.agent_status.get(agent_id, AgentStatus.FAILED),
            error=last_error,
            duration_ms=duration_ms,
            retries=self.max_retries
        )
        
        self.call_history.append(call_result)
        return call_result
    
    def _do_call(self, agent_id: str, message: str, subagent: bool) -> str:
        """实际执行 Agent 调用"""
        
        if subagent:
            cmd = ['openclaw', 'agent', '--agent', agent_id, '-m', message, '--timeout', str(self.timeout)]
        else:
            cmd = ['openclaw', 'agent', '--agent', agent_id, '-m', message, '--timeout', str(self.timeout)]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=self.timeout + 10
        )
        
        if result.returncode != 0:
            raise RuntimeError(f"Agent 调用失败: {result.stderr}")
        
        return result.stdout
    
    def check_heartbeat(self) -> dict[str, dict]:
        """检查所有 Agent 心跳状态"""
        now = time.time()
        heartbeat_status = {}
        
        for agent_id, last_beat in self.agent_heartbeat.items():
            elapsed = now - last_beat
            is_alive = elapsed < self.heartbeat_interval * 3
            
            heartbeat_status[agent_id] = {
                'last_beat': last_beat,
                'elapsed_sec': int(elapsed),
                'alive': is_alive,
                'status': self.agent_status.get(agent_id, AgentStatus.IDLE).value
            }
            
            if not is_alive:
                log.warning(f"{agent_id} 可能卡死，距离上次心跳 {elapsed:.0f}s")
                self.agent_status[agent_id] = AgentStatus.UNREACHABLE
        
        return heartbeat_status
    
    def get_status(self) -> dict:
        """获取所有 Agent 状态"""
        return {
            'agents': {k: v.value for k, v in self.agent_status.items()},
            'heartbeat': self.check_heartbeat(),
            'call_history_count': len(self.call_history),
            'recent_calls': [
                {
                    'success': c.success,
                    'status': c.status.value,
                    'duration_ms': c.duration_ms,
                    'retries': c.retries
                }
                for c in self.call_history[-10:]
            ]
        }

# CLI 入口
def main():
    import argparse
    parser = argparse.ArgumentParser(description='Agent 通信代理')
    parser.add_argument('--agent', '-a', required=True, help='目标 Agent ID')
    parser.add_argument('--message', '-m', required=True, help='发送的消息')
    parser.add_argument('--subagent', '-s', action='store_true', help='作为 subagent 调用')
    parser.add_argument('--timeout', '-t', type=int, default=30, help='超时时间(秒)')
    parser.add_argument('--retries', '-r', type=int, default=3, help='最大重试次数')
    parser.add_argument('--fallback', '-f', help='备用 Agent ID')
    parser.add_argument('--status', action='store_true', help='查看 Agent 状态')
    
    args = parser.parse_args()
    
    if args.status:
        comm = AgentCommunicator()
        import json
        print(json.dumps(comm.get_status(), indent=2, ensure_ascii=False))
        return
    
    comm = AgentCommunicator(timeout=args.timeout, max_retries=args.retries)
    result = comm.call_agent(args.agent, args.message, args.subagent, args.fallback)
    
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
