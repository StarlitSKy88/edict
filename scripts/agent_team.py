#!/usr/bin/env python3
"""
Edict Agent Team - 多Agent协作系统
功能: 任务分发、状态同步、团队记忆、协作流程
"""
import os
import sys
import json
import time
import logging
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional, Any, Dict, List
from datetime import datetime
from enum import Enum

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(name)s] %(message)s', datefmt='%H:%M:%S')
log = logging.getLogger('agent-team')

BASE = Path(__file__).parent.parent
TEAM_DIR = BASE / 'data' / 'team'
TEAM_DIR.mkdir(parents=True, exist_ok=True)

# ==================== Agent定义 ====================
class AgentRole(Enum):
    """Agent角色"""
    TAIZI = "太子"           # 消息分拣
    ZHONGSHU = "中书省"       # 规划
    MENXIA = "门下省"         # 审核
    SHANGSHU = "尚书省"       # 调度
    HUBU = "户部"             # 财务
    LIBU = "吏部"             # 人事
    BINGBU = "兵部"           # 安全
    XINGBU = "刑部"           # 法务
    GONGBU = "工部"           # 技术
    ZAOCHAO = "钦天监"        # 观测

@dataclass
class AgentState:
    """Agent状态"""
    role: str
    name: str
    status: str = "idle"  # idle, working, waiting, done
    current_task: Optional[str] = None
    last_active: str = field(default_factory=lambda: datetime.now().isoformat())
    capabilities: List[str] = field(default_factory=list)

# ==================== 任务 ====================
class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"       # 待处理
    IN_PROGRESS = "in_progress"
    WAITING = "waiting"       # 等待中
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class TeamTask:
    """团队任务"""
    id: str
    title: str
    creator: str           # 创建者
    assignee: str          # 执行者
    status: str = TaskStatus.PENDING.value
    priority: int = 5      # 1-10
    context: str = ""       # 任务上下文
    result: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    history: List[dict] = field(default_factory=list)

# ==================== Agent Team ====================
class AgentTeam:
    """多Agent协作系统"""
    
    def __init__(self, team_id: str = "default"):
        self.team_id = team_id
        self.agents: Dict[str, AgentState] = {}
        self.tasks: Dict[str, TeamTask] = {}
        self.team_memory: List[dict] = []  # 团队共享记忆
        
        # 初始化Agent
        self._init_agents()
        
        # 加载已有数据
        self._load()
        
        log.info(f"Agent Team初始化: {team_id}, Agent数: {len(self.agents)}")
    
    def _init_agents(self):
        """初始化Agent"""
        agent_configs = {
            "taizi": AgentState("太子", "太子", capabilities=["classify", "reply", "create_task"]),
            "zhongshu": AgentState("中书省", "中书令", capabilities=["plan", "delegate", "review"]),
            "menxia": AgentState("门下省", "门下侍中", capabilities=["review", "approve", "reject"]),
            "shangshu": AgentState("尚书省", "尚书令", capabilities=["dispatch", "coordinate", "monitor"]),
            "hubu": AgentState("户部", "户部尚书", capabilities=["finance", "budget", "account"]),
            "libu": AgentState("吏部", "吏部尚书", capabilities=["hr", "recruit", "train"]),
            "bingbu": AgentState("兵部", "兵部尚书", capabilities=["security", "risk", "compliance"]),
            "xingbu": AgentState("刑部", "刑部尚书", capabilities=["legal", "audit", "review"]),
            "gongbu": AgentState("工部", "工部尚书", capabilities=["tech", "develop", "deploy"]),
            "zaochao": AgentState("钦天监", "钦天监正", capabilities=["analyze", "predict", "observe"]),
        }
        
        for agent_id, state in agent_configs.items():
            self.agents[agent_id] = state
    
    # ---- 任务管理 ----
    def create_task(
        self,
        task_id: str,
        title: str,
        creator: str,
        assignee: str,
        context: str = "",
        priority: int = 5
    ) -> TeamTask:
        """创建任务"""
        task = TeamTask(
            id=task_id,
            title=title,
            creator=creator,
            assignee=assignee,
            context=context,
            priority=priority,
            status=TaskStatus.IN_PROGRESS.value,
            history=[{
                'action': 'created',
                'by': creator,
                'time': datetime.now().isoformat()
            }]
        )
        
        self.tasks[task_id] = task
        self._update_agent_status(assignee, "working", task_id)
        self._save()
        
        log.info(f"任务创建: {task_id} -> {assignee}")
        
        return task
    
    def assign_task(self, task_id: str, assignee: str) -> bool:
        """指派任务"""
        if task_id not in self.tasks:
            return False
        
        task = self.tasks[task_id]
        old_assignee = task.assignee
        
        task.assignee = assignee
        task.history.append({
            'action': 'assigned',
            'from': old_assignee,
            'to': assignee,
            'time': datetime.now().isoformat()
        })
        
        self._update_agent_status(old_assignee, "idle")
        self._update_agent_status(assignee, "working", task_id)
        self._save()
        
        log.info(f"任务指派: {task_id} -> {assignee}")
        return True
    
    def complete_task(self, task_id: str, result: str) -> bool:
        """完成任务"""
        if task_id not in self.tasks:
            return False
        
        task = self.tasks[task_id]
        task.status = TaskStatus.COMPLETED.value
        task.result = result
        task.updated_at = datetime.now().isoformat()
        task.history.append({
            'action': 'completed',
            'result': result,
            'time': datetime.now().isoformat()
        })
        
        self._update_agent_status(task.assignee, "idle")
        self._save()
        
        log.info(f"任务完成: {task_id}")
        return True
    
    def fail_task(self, task_id: str, error: str) -> bool:
        """任务失败"""
        if task_id not in self.tasks:
            return False
        
        task = self.tasks[task_id]
        task.status = TaskStatus.FAILED.value
        task.history.append({
            'action': 'failed',
            'error': error,
            'time': datetime.now().isoformat()
        })
        
        self._update_agent_status(task.assignee, "idle")
        self._save()
        
        log.error(f"任务失败: {task_id} - {error}")
        return True
    
    # ---- Agent管理 ----
    def _update_agent_status(self, agent_id: str, status: str, task_id: str = None):
        """更新Agent状态"""
        if agent_id in self.agents:
            self.agents[agent_id].status = status
            self.agents[agent_id].current_task = task_id
            self.agents[agent_id].last_active = datetime.now().isoformat()
    
    def get_agent(self, agent_id: str) -> Optional[AgentState]:
        """获取Agent状态"""
        return self.agents.get(agent_id)
    
    def get_available_agents(self, capability: str = None) -> List[str]:
        """获取可用Agent"""
        available = []
        
        for agent_id, state in self.agents.items():
            if state.status == "idle":
                if capability is None or capability in state.capabilities:
                    available.append(agent_id)
        
        return available
    
    def get_busy_agents(self) -> Dict[str, str]:
        """获取忙碌的Agent"""
        return {
            agent_id: state.current_task
            for agent_id, state in self.agents.items()
            if state.status == "working"
        }
    
    # ---- 团队记忆 ----
    def add_memory(self, content: str, agent_id: str, tags: List[str] = None):
        """添加团队记忆"""
        memory = {
            'content': content,
            'agent_id': agent_id,
            'tags': tags or [],
            'time': datetime.now().isoformat()
        }
        
        self.team_memory.append(memory)
        
        # 只保留最近100条
        if len(self.team_memory) > 100:
            self.team_memory = self.team_memory[-100:]
        
        self._save()
    
    def get_recent_memories(self, limit: int = 10) -> List[dict]:
        """获取最近记忆"""
        return self.team_memory[-limit:]
    
    def search_memories(self, query: str) -> List[dict]:
        """搜索记忆"""
        results = []
        
        for mem in self.team_memory:
            if query.lower() in mem['content'].lower():
                results.append(mem)
        
        return results
    
    # ---- 持久化 ----
    def _save(self):
        """保存数据"""
        data = {
            'team_id': self.team_id,
            'agents': {k: asdict(v) for k, v in self.agents.items()},
            'tasks': {k: asdict(v) for k, v in self.tasks.items()},
            'team_memory': self.team_memory
        }
        
        file = TEAM_DIR / f'{self.team_id}.json'
        file.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    
    def _load(self):
        """加载数据"""
        file = TEAM_DIR / f'{self.team_id}.json'
        
        if not file.exists():
            return
        
        try:
            data = json.loads(file.read_text())
            
            # 恢复任务
            for task_id, task_data in data.get('tasks', {}).items():
                self.tasks[task_id] = TeamTask(**task_data)
            
            # 恢复记忆
            self.team_memory = data.get('team_memory', [])
            
        except Exception as e:
            log.error(f"加载数据失败: {e}")
    
    # ---- 状态 ----
    def get_status(self) -> dict:
        """获取团队状态"""
        return {
            'team_id': self.team_id,
            'agents': {
                agent_id: {
                    'role': state.role,
                    'status': state.status,
                    'current_task': state.current_task,
                    'last_active': state.last_active
                }
                for agent_id, state in self.agents.items()
            },
            'tasks': {
                'total': len(self.tasks),
                'pending': sum(1 for t in self.tasks.values() if t.status == 'pending'),
                'in_progress': sum(1 for t in self.tasks.values() if t.status == 'in_progress'),
                'completed': sum(1 for t in self.tasks.values() if t.status == 'completed'),
                'failed': sum(1 for t in self.tasks.values() if t.status == 'failed')
            },
            'memory_count': len(self.team_memory)
        }

# ==================== CLI ====================
def main():
    import argparse
    parser = argparse.ArgumentParser(description='Edict Agent Team')
    parser.add_argument('--status', action='store_true', help='查看团队状态')
    parser.add_argument('--tasks', action='store_true', help='查看任务')
    parser.add_argument('--agents', action='store_true', help='查看Agent')
    parser.add_argument('--create', nargs=4, help='创建任务: id title creator assignee')
    parser.add_argument('--complete', nargs=2, help='完成任务: id result')
    parser.add_argument('--memory', action='store_true', help='查看团队记忆')
    
    args = parser.parse_args()
    
    team = AgentTeam()
    
    if args.status:
        print(json.dumps(team.get_status(), indent=2, ensure_ascii=False))
    
    elif args.tasks:
        for task in team.tasks.values():
            print(f"{task.id} | {task.assignee} | {task.status} | {task.title}")
    
    elif args.agents:
        for agent_id, state in team.agents.items():
            print(f"{agent_id} | {state.role} | {state.status} | {state.current_task or '-'}")
    
    elif args.create:
        task_id, title, creator, assignee = args.create
        team.create_task(task_id, title, creator, assignee)
        print(f"✅ 任务已创建: {task_id}")
    
    elif args.complete:
        task_id, result = args.complete
        team.complete_task(task_id, result)
        print(f"✅ 任务已完成: {task_id}")
    
    elif args.memory:
        for mem in team.get_recent_memories():
            print(f"[{mem['time'][:19]}] {mem['agent_id']}: {mem['content'][:50]}...")

if __name__ == '__main__':
    main()
