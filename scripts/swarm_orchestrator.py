#!/usr/bin/env python3
"""
Swarm头脑风暴 - 多Agent协作思考
类似Claude Code的Swarm模式，支持轮询和并行模式
"""
import os
import sys
import json
import time
import asyncio
import logging
import uuid
from pathlib import Path
from typing import List, Dict, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict

BASE = Path(__file__).parent.parent
sys.path.insert(0, str(BASE / 'scripts'))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [Swarm] %(levelname)s: %(message)s',
    datefmt='%H:%M:%S'
)
log = logging.getLogger('swarm')

# ==================== 常量 ====================
class SwarmMode(Enum):
    """Swarm模式"""
    ROUND_ROBIN = "round"    # 轮询: Agent依次发言
    CONCURRENT = "concurrent" # 并行: 所有Agent同时思考
    HYBRID = "hybrid"       # 混合: 先并行后轮询

class SwarmStatus(Enum):
    """Swarm状态"""
    PENDING = "pending"      # 等待开始
    RUNNING = "running"      # 运行中
    CONVERGED = "converged"  # 达成共识
    MAX_ROUNDS = "max_rounds" # 达到最大轮次
    FAILED = "failed"       # 失败

# ==================== 数据类 ====================
@dataclass
class AgentContribution:
    """Agent贡献"""
    agent_id: str
    agent_name: str
    content: str
    round: int
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class SwarmSession:
    """Swarm会话"""
    id: str
    topic: str
    mode: SwarmMode
    agents: List[str]  # Agent ID列表
    contributions: List[AgentContribution] = field(default_factory=list)
    status: SwarmStatus = SwarmStatus.PENDING
    current_round: int = 0
    max_rounds: int = 5
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    ended_at: Optional[float] = None
    consensus: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

# ==================== 核心类 ====================
class SwarmOrchestrator:
    """Swarm头脑风暴编排器"""
    
    def __init__(
        self,
        router=None,
        comm=None,  # 飞书通信
        llm_provider=None  # LLM调用
    ):
        self.router = router
        self.comm = comm
        self.llm_provider = llm_provider
        self.sessions: Dict[str, SwarmSession] = {}
        self.agent_think_funcs: Dict[str, Callable] = {}  # Agent思考函数
    
    def register_agent(self, agent_id: str, think_func: Callable):
        """注册Agent的思考函数"""
        self.agent_think_funcs[agent_id] = think_func
        log.info(f"注册Agent: {agent_id}")
    
    def create_swarm(
        self,
        topic: str,
        agent_ids: List[str],
        mode: SwarmMode = SwarmMode.ROUND_ROBIN,
        max_rounds: int = 5,
        metadata: Dict[str, Any] = None
    ) -> SwarmSession:
        """创建Swarm会话"""
        
        session_id = f"swarm_{uuid.uuid4().hex[:8]}"
        
        session = SwarmSession(
            id=session_id,
            topic=topic,
            mode=mode,
            agents=agent_ids,
            max_rounds=max_rounds,
            metadata=metadata or {}
        )
        
        self.sessions[session_id] = session
        
        log.info(f"创建Swarm: {session_id}, 话题: {topic}, 模式: {mode.value}")
        return session
    
    def start_swarm(self, session_id: str) -> SwarmSession:
        """启动Swarm"""
        
        if session_id not in self.sessions:
            raise ValueError(f"Session不存在: {session_id}")
        
        session = self.sessions[session_id]
        session.status = SwarmStatus.RUNNING
        session.started_at = time.time()
        
        if session.mode == SwarmMode.ROUND_ROBIN:
            return self._run_round_robin(session)
        elif session.mode == SwarmMode.CONCURRENT:
            return self._run_concurrent(session)
        elif session.mode == SwarmMode.HYBRID:
            return self._run_hybrid(session)
        
        return session
    
    def _run_round_robin(self, session: SwarmSession) -> SwarmSession:
        """轮询模式 - Agent依次发言"""
        
        log.info(f"启动轮询Swarm: {session.id}")
        
        # 构建初始上下文
        context = self._build_context(session, round_num=0)
        
        for round_num in range(1, session.max_rounds + 1):
            session.current_round = round_num
            
            for agent_id in session.agents:
                # 获取Agent的思考函数
                think_func = self.agent_think_funcs.get(agent_id)
                
                if think_func:
                    # 调用思考函数
                    try:
                        thought = think_func(context)
                    except Exception as e:
                        log.error(f"Agent思考失败: {agent_id}, {e}")
                        thought = f"[思考失败: {e}]"
                else:
                    # 使用默认LLM调用
                    thought = self._llm_think(agent_id, context)
                
                # 记录贡献
                contribution = AgentContribution(
                    agent_id=agent_id,
                    agent_name=agent_id,
                    content=thought,
                    round=round_num
                )
                session.contributions.append(contribution)
                
                # 更新上下文
                context += f"\n\n[{agent_id}]: {thought}"
                
                # 检查是否达成共识
                if self._check_convergence(session):
                    session.status = SwarmStatus.CONVERGED
                    session.consensus = self._compile_consensus(session)
                    break
            
            # 检查收敛
            if session.status == SwarmStatus.CONVERGED:
                break
        
        if session.status != SwarmStatus.CONVERGED:
            session.status = SwarmStatus.MAX_ROUNDS
        
        session.ended_at = time.time()
        
        log.info(f"Swarm结束: {session.id}, 状态: {session.status.value}, 轮次: {session.current_round}")
        return session
    
    def _run_concurrent(self, session: SwarmSession) -> SwarmSession:
        """并行模式 - 所有Agent同时思考"""
        
        log.info(f"启动并行Swarm: {session.id}")
        
        context = self._build_context(session, round_num=0)
        
        for round_num in range(1, session.max_rounds + 1):
            session.current_round = round_num
            
            # 并行调用所有Agent
            futures = []
            for agent_id in session.agents:
                think_func = self.agent_think_funcs.get(agent_id)
                
                if think_func:
                    # 异步执行
                    future = asyncio.coroutine(lambda a=agent_id, c=context: think_func(c))
                    futures.append((agent_id, future()))
                else:
                    # 使用LLM
                    futures.append((agent_id, self._llm_think_async(agent_id, context)))
            
            # 收集结果
            round_thoughts = []
            for agent_id, future in futures:
                try:
                    thought = future if isinstance(future, str) else asyncio.run(future) if hasattr(asyncio, 'run') else "concurrent"
                except Exception as e:
                    thought = f"[错误: {e}]"
                
                contribution = AgentContribution(
                    agent_id=agent_id,
                    agent_name=agent_id,
                    content=thought,
                    round=round_num
                )
                session.contributions.append(contribution)
                round_thoughts.append(thought)
                
                context += f"\n\n[{agent_id}]: {thought}"
            
            # 检查收敛
            if self._check_convergence(session):
                session.status = SwarmStatus.CONVERGED
                session.consensus = self._compile_consensus(session)
                break
        
        if session.status != SwarmStatus.CONVERGED:
            session.status = SwarmStatus.MAX_ROUNDS
        
        session.ended_at = time.time()
        
        return session
    
    def _run_hybrid(self, session: SwarmSession) -> SwarmSession:
        """混合模式 - 先并行后轮询"""
        
        log.info(f"启动混合Swarm: {session.id}")
        
        # 第一阶段: 并行快速头脑风暴
        context = self._build_context(session, round_num=0, phase="brainstorm")
        
        for round_num in range(1, 3):  # 2轮并行
            session.current_round = round_num
            
            for agent_id in session.agents:
                think_func = self.agent_think_funcs.get(agent_id)
                
                if think_func:
                    try:
                        thought = think_func(context)
                    except:
                        thought = "[错误]"
                else:
                    thought = self._llm_think(agent_id, context)
                
                contribution = AgentContribution(
                    agent_id=agent_id,
                    agent_name=agent_id,
                    content=thought,
                    round=round_num,
                    metadata={"phase": "brainstorm"}
                )
                session.contributions.append(contribution)
                context += f"\n\n[{agent_id}]: {thought}"
        
        # 第二阶段: 轮询深入讨论
        discussion_context = self._build_context(session, round_num=3, phase="discuss")
        
        for round_num in range(3, session.max_rounds + 1):
            session.current_round = round_num
            
            for agent_id in session.agents:
                think_func = self.agent_think_funcs.get(agent_id)
                
                if think_func:
                    try:
                        thought = think_func(discussion_context)
                    except:
                        thought = "[错误]"
                else:
                    thought = self._llm_think(agent_id, discussion_context)
                
                contribution = AgentContribution(
                    agent_id=agent_id,
                    agent_name=agent_id,
                    content=thought,
                    round=round_num,
                    metadata={"phase": "discuss"}
                )
                session.contributions.append(contribution)
                discussion_context += f"\n\n[{agent_id}]: {thought}"
                
                if self._check_convergence(session):
                    session.status = SwarmStatus.CONVERGED
                    break
            
            if session.status == SwarmStatus.CONVERGED:
                break
        
        if session.status != SwarmStatus.CONVERGED:
            session.status = SwarmStatus.MAX_ROUNDS
        
        session.consensus = self._compile_consensus(session)
        session.ended_at = time.time()
        
        return session
    
    def _build_context(self, session: SwarmSession, round_num: int, phase: str = None) -> str:
        """构建上下文"""
        
        context = f"""# 头脑风暴主题: {session.topic}

## 参与Agent
{', '.join(session.agents)}

## 轮次
当前第 {round_num} 轮 (共 {session.max_rounds} 轮)

## 模式
{session.mode.value}
{f'(阶段: {phase})' if phase else ''}

## 历史观点
"""
        
        # 添加历史贡献
        for c in session.contributions:
            context += f"\n[{c.agent_name}] (第{c.round}轮): {c.content[:200]}..."
        
        return context
    
    def _llm_think(self, agent_id: str, context: str) -> str:
        """使用LLM思考 (默认实现)"""
        
        if not self.llm_provider:
            return f"[{agent_id}] 需要配置LLM提供者才能思考"
        
        # 调用LLM
        try:
            response = self.llm_provider.chat(
                messages=[
                    {"role": "system", "content": f"你是一个Agent ({agent_id})，参与头脑风暴。请针对以下话题贡献观点。"},
                    {"role": "user", "content": context}
                ]
            )
            return response.content
        except Exception as e:
            log.error(f"LLM调用失败: {e}")
            return f"[思考失败: {e}]"
    
    async def _llm_think_async(self, agent_id: str, context: str) -> str:
        """异步LLM思考"""
        return self._llm_think(agent_id, context)
    
    def _check_convergence(self, session: SwarmSession) -> bool:
        """检查是否达成共识"""
        
        if len(session.contributions) < 2:
            return False
        
        # 获取最近一轮的所有观点
        latest_round = session.contributions[-1].round
        latest_thoughts = [
            c.content for c in session.contributions 
            if c.round == latest_round
        ]
        
        if len(latest_thoughts) < 2:
            return False
        
        # 简单检查: 如果观点包含共识关键词
        consensus_keywords = ["同意", "赞成", "共识", "决定", "最终方案", "一致"]
        
        for thought in latest_thoughts:
            for keyword in consensus_keywords:
                if keyword in thought:
                    return True
        
        # 或者检查是否达到最大轮次
        if session.current_round >= session.max_rounds:
            return True
        
        return False
    
    def _compile_consensus(self, session: SwarmSession) -> str:
        """编译共识"""
        
        if session.status == SwarmStatus.CONVERGED:
            return "已达成共识 (见最后发言)"
        
        # 汇总所有观点
        summary = f"# 头脑风暴结果\n\n"
        summary += f"**主题**: {session.topic}\n\n"
        summary += f"**轮次**: {session.current_round}/{session.max_rounds}\n\n"
        summary += f"**状态**: {session.status.value}\n\n"
        
        # 按Agent汇总
        agent_opinions = defaultdict(list)
        for c in session.contributions:
            agent_opinions[c.agent_id].append(c.content)
        
        summary += "## 各Agent观点\n\n"
        for agent_id, opinions in agent_opinions.items():
            summary += f"### {agent_id}\n"
            summary += opinions[-1][:300] + "...\n\n"
        
        return summary
    
    # ---- 会话管理 ----
    def get_session(self, session_id: str) -> Optional[SwarmSession]:
        """获取会话"""
        return self.sessions.get(session_id)
    
    def list_sessions(self, status: SwarmStatus = None) -> List[SwarmSession]:
        """列出会话"""
        sessions = list(self.sessions.values())
        if status:
            sessions = [s for s in sessions if s.status == status]
        return sessions
    
    def get_contributions(self, session_id: str, agent_id: str = None) -> List[AgentContribution]:
        """获取贡献记录"""
        
        if session_id not in self.sessions:
            return []
        
        session = self.sessions[session_id]
        
        if agent_id:
            return [c for c in session.contributions if c.agent_id == agent_id]
        
        return session.contributions
    
    def export_session(self, session_id: str, format: str = "json") -> str:
        """导出会话"""
        
        if session_id not in self.sessions:
            return "{}"
        
        session = self.sessions[session_id]
        
        data = {
            "id": session.id,
            "topic": session.topic,
            "mode": session.mode.value,
            "agents": session.agents,
            "status": session.status.value,
            "current_round": session.current_round,
            "max_rounds": session.max_rounds,
            "duration": session.ended_at - session.started_at if session.ended_at else None,
            "consensus": session.consensus,
            "contributions": [
                {
                    "agent_id": c.agent_id,
                    "agent_name": c.agent_name,
                    "content": c.content,
                    "round": c.round,
                    "timestamp": c.timestamp
                }
                for c in session.contributions
            ]
        }
        
        if format == "json":
            return json.dumps(data, ensure_ascii=False, indent=2)
        elif format == "markdown":
            return self._session_to_markdown(session)
        
        return str(data)
    
    def _session_to_markdown(self, session: SwarmSession) -> str:
        """转换为Markdown"""
        
        md = f"""# 🧠 头脑风暴报告

## 基本信息
- **主题**: {session.topic}
- **模式**: {session.mode.value}
- **状态**: {session.status.value}
- **轮次**: {session.current_round}/{session.max_rounds}
- **参与**: {', '.join(session.agents)}

## 讨论记录

"""
        
        # 按轮次展示
        current_round = 0
        for c in session.contributions:
            if c.round != current_round:
                md += f"\n### 第 {c.round} 轮\n\n"
                current_round = c.round
            
            md += f"**{c.agent_name}**:\n{c.content}\n\n"
        
        if session.consensus:
            md += f"\n## 📝 结论\n\n{session.consensus}\n"
        
        return md


# ==================== CLI ====================
def main():
    import argparse
    parser = argparse.ArgumentParser(description='Swarm头脑风暴')
    parser.add_argument('--create', nargs='+', metavar=("TOPIC", "AGENTS"), help='创建Swarm')
    parser.add_argument('--mode', choices=['round', 'concurrent', 'hybrid'], default='round', help='模式')
    parser.add_argument('--rounds', type=int, default=5, help='最大轮次')
    parser.add_argument('--start', help='启动Swarm')
    parser.add_argument('--list', action='store_true', help='列出Swarm')
    parser.add_argument('--view', help='查看Swarm详情')
    parser.add_argument('--export', nargs=2, metavar=("ID", "FORMAT"), help='导出 (json/markdown)')
    
    args = parser.parse_args()
    
    swarm = SwarmOrchestrator()
    
    if args.create:
        topic = args.create[0]
        agents = args.create[1:]
        
        mode = SwarmMode[args.mode.upper()]
        
        session = swarm.create_swarm(
            topic=topic,
            agent_ids=agents,
            mode=mode,
            max_rounds=args.rounds
        )
        print(f"创建Swarm: {session.id}")
        print(f"话题: {session.topic}")
        print(f"Agent: {session.agents}")
        print(f"模式: {session.mode.value}")
        print(f"使用 --start {session.id} 启动")
    
    elif args.start:
        session = swarm.start_swarm(args.start)
        print(f"状态: {session.status.value}")
        print(f"轮次: {session.current_round}")
        print(f"\n{session.consensus}")
    
    elif args.list:
        for s in swarm.list_sessions():
            print(f"{s.id:20} | {s.topic:30} | {s.status.value:10} | 轮: {s.current_round}/{s.max_rounds}")
    
    elif args.view:
        session = swarm.get_session(args.view)
        if session:
            print(json.dumps({
                "id": session.id,
                "topic": session.topic,
                "mode": session.mode.value,
                "status": session.status.value,
                "agents": session.agents,
                "contributions": len(session.contributions)
            }, indent=2))
    
    elif args.export:
        result = swarm.export_session(args.export[0], args.export[1])
        print(result)

if __name__ == '__main__':
    main()
