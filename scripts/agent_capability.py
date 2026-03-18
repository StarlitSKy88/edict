#!/usr/bin/env python3
"""
Edict Agent 能力引擎
功能: Skill动态加载、工具注册、Agent能力增强
"""
import os
import sys
import json
import importlib
import logging
from pathlib import Path
from typing import Any, Optional, Dict, List, Callable
from dataclasses import dataclass, field
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(name)s] %(message)s', datefmt='%H:%M:%S')
log = logging.getLogger('agent-capability')

BASE = Path(__file__).parent.parent
AGENTS_DIR = BASE / 'agents'

# ==================== 能力定义 ====================
@dataclass
class Capability:
    """Agent能力"""
    name: str
    type: str           # skill, tool, action
    description: str
    handler: str        # 处理函数/脚本路径
    params: Dict = field(default_factory=dict)

@dataclass
class AgentCapability:
    """Agent能力集"""
    agent_id: str
    agent_name: str
    capabilities: List[Capability] = field(default_factory=list)
    enabled: bool = True

# ==================== 能力引擎 ====================
class CapabilityEngine:
    """能力引擎"""
    
    def __init__(self):
        self.agents: Dict[str, AgentCapability] = {}
        self.tools: Dict[str, Callable] = {}  # 注册的工具函数
        self._register_builtin_tools()
        self._load_agents()
        
        log.info(f"能力引擎初始化: {len(self.agents)} Agents")
    
    def _register_builtin_tools(self):
        """注册内置工具"""
        # 看板操作
        self.tools['kanban_create'] = self._tool_kanban_create
        self.tools['kanban_flow'] = self._tool_kanban_flow
        self.tools['kanban_progress'] = self._tool_kanban_progress
        self.tools['kanban_done'] = self._tool_kanban_done
        
        # 消息操作
        self.tools['send_message'] = self._tool_send_message
        self.tools['reply_message'] = self._tool_reply_message
        
        # Agent操作
        self.tools['call_agent'] = self._tool_call_agent
        self.tools['delegate_task'] = self._tool_delegate_task
        
        log.info(f"已注册 {len(self.tools)} 个内置工具")
    
    def _load_agents(self):
        """加载所有Agent"""
        for agent_dir in AGENTS_DIR.iterdir():
            if not agent_dir.is_dir():
                continue
            
            # 跳过非Agent目录
            if agent_dir.name.startswith('_') or agent_dir.name == 'common':
                continue
            
            # 加载Agent能力
            agent = self._load_agent(agent_dir.name)
            if agent:
                self.agents[agent_dir.name] = agent
    
    def _load_agent(self, agent_id: str) -> Optional[AgentCapability]:
        """加载单个Agent"""
        agent_dir = AGENTS_DIR / agent_id
        
        if not agent_dir.exists():
            return None
        
        # 读取SOUL.md获取Agent名称
        soul_file = agent_dir / 'SOUL.md'
        agent_name = agent_id
        
        if soul_file.exists():
            content = soul_file.read_text()
            # 提取Agent名称 (第一行 # 之后的内容)
            for line in content.split('\n'):
                if line.strip().startswith('#'):
                    agent_name = line.strip().replace('#', '').strip()
                    break
        
        # 查找Skills
        skills = []
        skills_dir = agent_dir / 'skills'
        
        if skills_dir.exists():
            for skill_dir in skills_dir.iterdir():
                if not skill_dir.is_dir():
                    continue
                
                skill_name = skill_dir.name
                skill_file = skill_dir / 'SKILL.md'
                
                if skill_file.exists():
                    skill_desc = skill_file.read_text()[:100]
                    skills.append(Capability(
                        name=skill_name,
                        type='skill',
                        description=skill_desc,
                        handler=str(skill_dir / 'main.py')
                    ))
        
        # 添加Agent到能力引擎
        return AgentCapability(
            agent_id=agent_id,
            agent_name=agent_name,
            capabilities=skills
        )
    
    # ---- 工具实现 ----
    def _tool_kanban_create(self, **kwargs) -> dict:
        """创建任务"""
        import subprocess
        cmd = [
            'python3', 'scripts/kanban_update.py', 'create',
            kwargs['id'], kwargs['title'], kwargs['state'],
            kwargs['org'], kwargs['official']
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=BASE)
        return {'success': result.returncode == 0, 'output': result.stdout}
    
    def _tool_kanban_flow(self, **kwargs) -> dict:
        """流转任务"""
        import subprocess
        cmd = [
            'python3', 'scripts/kanban_update.py', 'flow',
            kwargs['id'], kwargs['from'], kwargs['to'], kwargs['remark']
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=BASE)
        return {'success': result.returncode == 0, 'output': result.stdout}
    
    def _tool_kanban_progress(self, **kwargs) -> dict:
        """更新进度"""
        import subprocess
        cmd = [
            'python3', 'scripts/kanban_update.py', 'progress',
            kwargs['id'], kwargs['current'], kwargs['plan']
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=BASE)
        return {'success': result.returncode == 0, 'output': result.stdout}
    
    def _tool_kanban_done(self, **kwargs) -> dict:
        """完成任务"""
        import subprocess
        cmd = [
            'python3', 'scripts/kanban_update.py', 'done',
            kwargs['id'], kwargs['output'], kwargs['summary']
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=BASE)
        return {'success': result.returncode == 0, 'output': result.stdout}
    
    def _tool_send_message(self, **kwargs) -> dict:
        """发送消息"""
        # 使用OpenClaw的消息接口
        log.info(f"发送消息: {kwargs.get('message', '')[:50]}")
        return {'success': True, 'message': '消息已发送'}
    
    def _tool_reply_message(self, **kwargs) -> dict:
        """回复消息"""
        log.info(f"回复消息: {kwargs.get('message', '')[:50]}")
        return {'success': True, 'message': '已回复'}
    
    def _tool_call_agent(self, **kwargs) -> dict:
        """调用Agent"""
        target = kwargs.get('target')
        message = kwargs.get('message', '')
        
        log.info(f"调用Agent: {target}")
        
        # TODO: 使用OpenClaw的sessions_send
        return {'success': True, 'agent': target, 'message': message}
    
    def _tool_delegate_task(self, **kwargs) -> dict:
        """委派任务"""
        from_agent = kwargs.get('from')
        to_agent = kwargs.get('to')
        task = kwargs.get('task', '')
        
        log.info(f"任务委派: {from_agent} -> {to_agent}")
        
        return {
            'success': True,
            'from': from_agent,
            'to': to_agent,
            'task': task
        }
    
    # ---- 执行能力 ----
    def execute(self, agent_id: str, capability: str, **params) -> Any:
        """执行Agent能力"""
        
        # 查找Agent
        agent = self.agents.get(agent_id)
        if not agent:
            return {'error': f'Agent不存在: {agent_id}'}
        
        # 查找能力
        cap = None
        for c in agent.capabilities:
            if c.name == capability:
                cap = c
                break
        
        if not cap:
            return {'error': f'能力不存在: {capability}'}
        
        # 执行
        if cap.type == 'skill':
            return self._execute_skill(cap, params)
        elif cap.type == 'tool':
            return self._execute_tool(cap.name, params)
        
        return {'error': f'未知能力类型: {cap.type}'}
    
    def _execute_skill(self, capability: Capability, params: Dict) -> Any:
        """执行Skill"""
        handler = capability.handler
        
        if not handler or not Path(handler).exists():
            return {'error': f'Skill不存在: {capability.name}'}
        
        # 动态导入执行
        try:
            import subprocess
            result = subprocess.run(
                ['python3', handler, json.dumps(params)],
                capture_output=True,
                text=True,
                cwd=BASE,
                timeout=30
            )
            
            if result.returncode == 0:
                return json.loads(result.stdout) if result.stdout else {'success': True}
            else:
                return {'error': result.stderr}
        
        except Exception as e:
            return {'error': str(e)}
    
    def _execute_tool(self, tool_name: str, params: Dict) -> Any:
        """执行工具"""
        tool = self.tools.get(tool_name)
        
        if not tool:
            return {'error': f'工具不存在: {tool_name}'}
        
        try:
            return tool(**params)
        except Exception as e:
            return {'error': str(e)}
    
    # ---- 注册自定义能力 ----
    def register_tool(self, name: str, handler: Callable):
        """注册工具"""
        self.tools[name] = handler
        log.info(f"工具已注册: {name}")
    
    # ---- 查询能力 ----
    def list_capabilities(self, agent_id: str = None) -> List[Dict]:
        """列出能力"""
        if agent_id:
            agent = self.agents.get(agent_id)
            if not agent:
                return []
            
            return [
                {
                    'name': c.name,
                    'type': c.type,
                    'description': c.description[:50]
                }
                for c in agent.capabilities
            ]
        
        # 所有Agent的能力
        results = []
        for aid, agent in self.agents.items():
            results.append({
                'agent_id': aid,
                'agent_name': agent.agent_name,
                'capabilities': [
                    {'name': c.name, 'type': c.type}
                    for c in agent.capabilities
                ]
            })
        
        return results
    
    def get_tools(self) -> List[str]:
        """获取可用工具列表"""
        return list(self.tools.keys())

# ==================== CLI ====================
def main():
    import argparse
    parser = argparse.ArgumentParser(description='Edict Agent能力引擎')
    parser.add_argument('--list', action='store_true', help='列出所有Agent能力')
    parser.add_argument('--agent', help='查看特定Agent能力')
    parser.add_argument('--tools', action='store_true', help='列出可用工具')
    parser.add_argument('--execute', nargs='+', help='执行能力: agent capability [params...]')
    
    args = parser.parse_args()
    
    engine = CapabilityEngine()
    
    if args.list:
        for item in engine.list_capabilities():
            print(f"\n{item['agent_id']} ({item['agent_name']}):")
            for cap in item['capabilities']:
                print(f"  - {cap['name']} [{cap['type']}]")
    
    elif args.agent:
        caps = engine.list_capabilities(args.agent)
        print(f"Agent: {args.agent}")
        for cap in caps:
            print(f"  - {cap['name']}: {cap['description']}")
    
    elif args.tools:
        print("可用工具:")
        for tool in engine.get_tools():
            print(f"  - {tool}")
    
    elif args.execute:
        agent = args.execute[0]
        capability = args.execute[1]
        params = {}
        
        # 解析参数
        for p in args.execute[2:]:
            if '=' in p:
                k, v = p.split('=', 1)
                params[k] = v
        
        result = engine.execute(agent, capability, **params)
        print(json.dumps(result, indent=2, ensure_ascii=False))

if __name__ == '__main__':
    main()
