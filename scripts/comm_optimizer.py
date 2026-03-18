#!/usr/bin/env python3
"""
Edict 通信优化器
解决: 超时卡死、状态不透明、重试机制
"""
import os
import time
import logging
from typing import Optional, Callable, Any
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(name)s] %(message)s', datefmt='%H:%M:%S')
log = logging.getLogger('comm-optimizer')

# 导入通知
from scripts.notification import Notifier, notify_task_progress, notify_task_failed

class TaskState(Enum):
    """任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    WAITING = "waiting"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"

@dataclass
class AgentChain:
    """Agent调用链"""
    task_id: str
    steps: list = field(default_factory=list)
    current_step: int = 0
    state: TaskState = TaskState.PENDING
    started_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: Optional[str] = None
    error: Optional[str] = None

class CommOptimizer:
    """通信优化器"""
    
    def __init__(self):
        # 配置
        self.timeout = int(os.getenv('AGENT_TIMEOUT', '60'))  # 60秒超时
        self.max_retries = int(os.getenv('AGENT_MAX_RETRIES', '3'))
        self.enable_notification = os.getenv('NOTIFICATION_ENABLED', 'true').lower() == 'true'
        
        # 任务链
        self.chains: dict[str, AgentChain] = {}
        
        # 通知器
        self.notifier = Notifier()
        
        log.info(f"通信优化器初始化: timeout={self.timeout}s, retries={self.max_retries}")
    
    def start_chain(self, task_id: str, steps: list) -> AgentChain:
        """开始调用链"""
        chain = AgentChain(
            task_id=task_id,
            steps=steps,
            state=TaskState.RUNNING
        )
        
        self.chains[task_id] = chain
        
        # 通知开始
        if self.enable_notification:
            notify_task_progress(
                task_id,
                steps[0] if steps else "系统",
                "开始执行",
                f"共{len(steps)}步"
            )
        
        log.info(f"任务链开始: {task_id}, 步骤: {steps}")
        return chain
    
    def next_step(self, task_id: str, agent: str, result: Any = None) -> bool:
        """执行下一步"""
        
        if task_id not in self.chains:
            log.warning(f"任务链不存在: {task_id}")
            return False
        
        chain = self.chains[task_id]
        chain.current_step += 1
        
        # 检查是否完成
        if chain.current_step >= len(chain.steps):
            chain.state = TaskState.COMPLETED
            chain.completed_at = datetime.now().isoformat()
            
            if self.enable_notification:
                notify_task_completed(task_id, f"完成{len(chain.steps)}步")
            
            log.info(f"任务链完成: {task_id}")
            return True
        
        # 通知进展
        current_agent = chain.steps[chain.current_step]
        if self.enable_notification:
            notify_task_progress(
                task_id,
                current_agent,
                "执行中",
                f"第{chain.current_step+1}/{len(chain.steps)}步"
            )
        
        return True
    
    def handle_timeout(self, task_id: str, agent: str) -> bool:
        """处理超时"""
        
        if task_id not in self.chains:
            return False
        
        chain = self.chains[task_id]
        
        # 重试逻辑
        retries = getattr(chain, 'retry_count', 0)
        
        if retries < self.max_retries:
            # 增加重试次数
            chain.retry_count = retries + 1
            
            delay = 2 ** retries  # 指数退避
            log.warning(f"任务 {task_id} 超时, {delay}s后重试 ({retries+1}/{self.max_retries})")
            
            if self.enable_notification:
                notify_task_progress(
                    task_id,
                    agent,
                    f"超时重试({retries+1}/{self.max_retries})",
                    f"等待{delay}秒"
                )
            
            return True
        else:
            # 超时失败
            chain.state = TaskState.TIMEOUT
            chain.error = f"Agent {agent} 超时"
            chain.completed_at = datetime.now().isoformat()
            
            if self.enable_notification:
                notify_task_failed(task_id, f"{agent} 超时")
            
            log.error(f"任务链超时失败: {task_id}")
            return False
    
    def handle_error(self, task_id: str, agent: str, error: str) -> bool:
        """处理错误"""
        
        if task_id not in self.chains:
            return False
        
        chain = self.chains[task_id]
        chain.state = TaskState.FAILED
        chain.error = error
        chain.completed_at = datetime.now().isoformat()
        
        if self.enable_notification:
            notify_agent_error(agent, error)
            notify_task_failed(task_id, error)
        
        log.error(f"任务链失败: {task_id}, error: {error}")
        return True
    
    def get_status(self, task_id: str) -> Optional[dict]:
        """获取任务状态"""
        
        if task_id not in self.chains:
            return None
        
        chain = self.chains[task_id]
        
        return {
            'task_id': task_id,
            'state': chain.state.value,
            'progress': f"{chain.current_step}/{len(chain.steps)}",
            'current_agent': chain.steps[chain.current_step] if chain.current_step < len(chain.steps) else None,
            'started_at': chain.started_at,
            'completed_at': chain.completed_at,
            'error': chain.error
        }

if __name__ == '__main__':
    # 测试
    optimizer = CommOptimizer()
    
    # 模拟任务链
    optimizer.start_chain("JJC-001", ["太子", "中书省", "门下省", "尚书省", "工部"])
    
    # 模拟执行
    optimizer.next_step("JJC-001", "太子", "已处理")
    optimizer.next_step("JJC-001", "中书省", "已规划")
    
    # 查看状态
    status = optimizer.get_status("JJC-001")
    print(f"任务状态: {status}")
