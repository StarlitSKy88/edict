#!/usr/bin/env python3
"""
层级路由 - 保障三省六部架构不变
定义Agent之间的层级关系和通信规则
"""
import os
import json
import logging
from functools import lru_cache
from typing import Optional, Dict, List, Set
from dataclasses import dataclass, field
from enum import Enum

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [Router] %(levelname)s: %(message)s',
    datefmt='%H:%M:%S'
)
log = logging.getLogger('router')

# ==================== 常量 ====================
class AgentLevel(Enum):
    """Agent层级"""
    CEO = 0        # 教皇 - 最高决策者
    DIRECTOR = 1   # 红衣主教团、主教团 - 部门总监
    MANAGER = 2    # 枢机处、六部 - 部门经理
    SPECIALIST = 3 # 地方/临时 - 专业人员

class RelationType(Enum):
    """关系类型"""
    PARENT = "parent"      # 上级
    CHILD = "child"       # 下级
    PEER = "peer"         # 同级
    CROSS = "cross"       # 跨级 (不允许)

# ==================== 数据类 ====================
@dataclass
class AgentNode:
    """Agent节点"""
    id: str
    name: str
    role: str
    level: AgentLevel
    parent: Optional[str] = None
    children: List[str] = field(default_factory=list)
    peers: List[str] = field(default_factory=list)
    skills: List[str] = field(default_factory=list)
    feishu_open_id: Optional[str] = None
    is_temp: bool = False
    expires_at: Optional[float] = None

@dataclass
class RouteRule:
    """路由规则"""
    from_agent: str
    to_agent: str
    allowed: bool
    reason: str = ""

# ==================== 层级定义 ====================
DEFAULT_HIERARCHY = {
    # 教皇 - CEO
    "教皇": {
        "name": "教皇",
        "role": "CEO - 最高决策者",
        "level": AgentLevel.CEO,
        "children": ["红衣主教团", "主教团"],
        "skills": ["strategy", "decision", "coordination"]
    },
    
    # 决策层
    "红衣主教团": {
        "name": "红衣主教团",
        "role": "规划决策",
        "level": AgentLevel.DIRECTOR,
        "parent": "教皇",
        "children": ["枢机处"],
        "skills": ["planning", "strategy", "analysis"]
    },
    "主教团": {
        "name": "主教团",
        "role": "执行调度",
        "level": AgentLevel.DIRECTOR,
        "parent": "教皇",
        "children": ["工匠行会", "财政部", "骑士团", "宗教裁判所", "典礼部", "人事部"],
        "skills": ["dispatch", "coordination", "management"]
    },
    
    # 执行层
    "枢机处": {
        "name": "枢机处",
        "role": "审核审批",
        "level": AgentLevel.MANAGER,
        "parent": "红衣主教团",
        "skills": ["review", "approval", "compliance"]
    },
    
    # 六部
    "工匠行会": {
        "name": "工匠行会",
        "role": "技术工程",
        "level": AgentLevel.MANAGER,
        "parent": "主教团",
        "skills": ["tech", "infrastructure", "development"]
    },
    "财政部": {
        "name": "财政部",
        "role": "财务",
        "level": AgentLevel.MANAGER,
        "parent": "主教团",
        "skills": ["finance", "accounting", "budget"]
    },
    "骑士团": {
        "name": "骑士团",
        "role": "安全",
        "level": AgentLevel.MANAGER,
        "parent": "主教团",
        "skills": ["security", "defense", "risk"]
    },
    "宗教裁判所": {
        "name": "宗教裁判所",
        "role": "合规法务",
        "level": AgentLevel.MANAGER,
        "parent": "主教团",
        "skills": ["legal", "compliance", "justice"]
    },
    "典礼部": {
        "name": "典礼部",
        "role": "文档外交",
        "level": AgentLevel.MANAGER,
        "parent": "主教团",
        "skills": ["documentation", "external", "protocol"]
    },
    "人事部": {
        "name": "人事部",
        "role": "人事",
        "level": AgentLevel.MANAGER,
        "parent": "主教团",
        "skills": ["hr", "personnel", "recruitment"]
    },
    
    # 观察层
    "占星术士": {
        "name": "占星术士",
        "role": "观测监控",
        "level": AgentLevel.SPECIALIST,
        "parent": "教皇",
        "skills": ["monitoring", "observation", "reporting"]
    },
    
    # 教皇秘书
    "教皇詹事": {
        "name": "教皇詹事",
        "role": "教皇秘书",
        "level": AgentLevel.SPECIALIST,
        "parent": "教皇",
        "skills": ["secretary", "coordination", "schedule"]
    },
}

# ==================== 核心类 ====================
class HierarchicalRouter:
    """层级路由 - 保障三省六部架构"""
    
    def __init__(self, config_path: str = None):
        self.agents: Dict[str, AgentNode] = {}
        self.config_path = config_path
        
        # 加载配置或使用默认
        if config_path and os.path.exists(config_path):
            self.load_config(config_path)
        else:
            self._init_default_hierarchy()
    
    def _init_default_hierarchy(self):
        """初始化默认层级"""
        for agent_id, info in DEFAULT_HIERARCHY.items():
            node = AgentNode(
                id=agent_id,
                name=info["name"],
                role=info["role"],
                level=info["level"],
                parent=info.get("parent"),
                children=info.get("children", []),
                skills=info.get("skills", [])
            )
            self.agents[agent_id] = node
            
            # 建立peer关系 (同层级)
            for other_id, other in self.agents.items():
                if other_id != agent_id and other.level == node.level:
                    if other_id not in node.peers:
                        node.peers.append(other_id)
                    if agent_id not in other.peers:
                        other.peers.append(agent_id)
        
        log.info(f"初始化层级: {len(self.agents)} 个Agent")
    
    def load_config(self, path: str):
        """加载自定义配置"""
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        self.agents = {}
        for agent_id, info in data.get("agents", {}).items():
            level_str = info.get("level", "SPECIALIST")
            level = AgentLevel[level_str.upper()] if isinstance(level_str, str) else level_str
            
            node = AgentNode(
                id=agent_id,
                name=info.get("name", agent_id),
                role=info.get("role", ""),
                level=level,
                parent=info.get("parent"),
                children=info.get("children", []),
                skills=info.get("skills", []),
                feishu_open_id=info.get("feishu_open_id"),
                is_temp=info.get("is_temp", False),
                expires_at=info.get("expires_at")
            )
            self.agents[agent_id] = node
        
        log.info(f"加载配置: {len(self.agents)} 个Agent")
    
    def save_config(self, path: str = None):
        """保存配置"""
        path = path or self.config_path
        if not path:
            return
        
        data = {
            "agents": {}
        }
        
        for agent_id, node in self.agents.items():
            data["agents"][agent_id] = {
                "name": node.name,
                "role": node.role,
                "level": node.level.name,
                "parent": node.parent,
                "children": node.children,
                "skills": node.skills,
                "feishu_open_id": node.feishu_open_id,
                "is_temp": node.is_temp,
                "expires_at": node.expires_at
            }
        
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        log.info(f"配置已保存: {path}")
    
    # ---- 路由检查 ----
    def check_route(self, from_agent: str, to_agent: str) -> RouteRule:
        """检查路由是否允许"""
        
        # Agent不存在
        if from_agent not in self.agents:
            return RouteRule(from_agent, to_agent, False, f"发送方不存在: {from_agent}")
        if to_agent not in self.agents:
            return RouteRule(from_agent, to_agent, False, f"接收方不存在: {to_agent}")
        
        from_node = self.agents[from_agent]
        to_node = self.agents[to_agent]
        
        # 自己给自己发
        if from_agent == to_agent:
            return RouteRule(from_agent, to_agent, True, "同Agent内部消息")
        
        # 上下级关系
        if from_node.parent == to_agent:
            return RouteRule(from_agent, to_agent, True, "下级向上级汇报")
        if to_node.parent == from_agent:
            return RouteRule(from_agent, to_agent, True, "上级向下级部署任务")
        
        # 同级协作
        if to_agent in from_node.peers:
            return RouteRule(from_agent, to_agent, True, "同级协作")
        
        # 教皇可以给任何人发
        if from_agent == "教皇":
            return RouteRule(from_agent, to_agent, True, "CEO特殊权限")
        
        # 教皇可以接收任何人消息
        if to_agent == "教皇":
            return RouteRule(from_agent, to_agent, True, "CEO接收权限")
        
        # 临时Agent可以与父级通信
        if from_node.is_temp and from_node.parent == to_agent:
            return RouteRule(from_agent, to_agent, True, "临时Agent向父级汇报")
        if to_node.is_temp and to_node.parent == from_agent:
            return RouteRule(from_agent, to_agent, True, "父级向临时Agent部署")
        
        # 其他情况 - 跨级调用
        from_level = from_node.level.value
        to_level = to_node.level.value
        
        if abs(from_level - to_level) > 1:
            return RouteRule(
                from_agent, to_agent, False, 
                f"跨级调用禁止: {from_node.level.name} -> {to_node.level.name}"
            )
        
        return RouteRule(from_agent, to_agent, True, "间接层级允许")
    
    def route_message(self, from_agent: str, to_agent: str, content: str) -> dict:
        """路由消息 - 返回路由结果"""
        
        rule = self.check_route(from_agent, to_agent)
        
        result = {
            "allowed": rule.allowed,
            "from": from_agent,
            "to": to_agent,
            "reason": rule.reason
        }
        
        if not rule.allowed:
            log.warning(f"路由拒绝: {from_agent} -> {to_agent}, 原因: {rule.reason}")
            result["error"] = rule.reason
            return result
        
        log.info(f"路由允许: {from_agent} -> {to_agent} ({rule.reason})")
        return result
    
    # ---- Agent管理 ----
    def add_agent(
        self,
        agent_id: str,
        name: str,
        role: str,
        parent: str,
        level: AgentLevel = AgentLevel.SPECIALIST,
        skills: List[str] = None
    ) -> AgentNode:
        """添加新Agent"""
        
        # 检查父级是否存在
        if parent not in self.agents:
            raise ValueError(f"父级不存在: {parent}")
        
        parent_node = self.agents[parent]
        
        node = AgentNode(
            id=agent_id,
            name=name,
            role=role,
            level=level,
            parent=parent,
            children=[],
            skills=skills or [],
            is_temp=False
        )
        
        # 更新父级children
        parent_node.children.append(agent_id)
        
        # 建立同级的peer关系
        for other_id, other in self.agents.items():
            if other.level == level and other_id != agent_id:
                node.peers.append(other_id)
                other.peers.append(agent_id)
        
        self.agents[agent_id] = node
        
        log.info(f"添加Agent: {agent_id}, 父级: {parent}, 层级: {level.name}")
        return node
    
    def remove_agent(self, agent_id: str) -> bool:
        """移除Agent (不删除教皇)"""
        
        if agent_id not in self.agents:
            return False
        
        if agent_id == "教皇":
            log.error("不能删除教皇")
            return False
        
        node = self.agents[agent_id]
        
        # 从父级children中移除
        if node.parent and node.parent in self.agents:
            parent = self.agents[node.parent]
            if agent_id in parent.children:
                parent.children.remove(agent_id)
        
        # 从同级peers中移除
        for peer_id in node.peers:
            if peer_id in self.agents:
                peer = self.agents[peer_id]
                if agent_id in peer.peers:
                    peer.peers.remove(agent_id)
        
        del self.agents[agent_id]
        
        log.info(f"移除Agent: {agent_id}")
        return True
    
    def get_children(self, agent_id: str) -> List[str]:
        """获取直接下属"""
        if agent_id not in self.agents:
            return []
        return self.agents[agent_id].children.copy()
    
    def get_all_descendants(self, agent_id: str) -> Set[str]:
        """获取所有后代 (递归)"""
        if agent_id not in self.agents:
            return set()
        
        result = set()
        node = self.agents[agent_id]
        
        for child in node.children:
            result.add(child)
            result.update(self.get_all_descendants(child))
        
        return result
    
    def get_parent_chain(self, agent_id: str) -> List[str]:
        """获取父级链"""
        if agent_id not in self.agents:
            return []
        
        chain = []
        node = self.agents[agent_id]
        
        while node.parent:
            chain.append(node.parent)
            node = self.agents[node.parent]
        
        return chain
    
    def get_team(self, agent_id: str) -> List[str]:
        """获取团队成员 (自己+所有后代)"""
        team = [agent_id]
        team.extend(self.get_all_descendants(agent_id))
        return team
    
    # ---- 状态查询 ----
    def get_hierarchy_tree(self, root: str = "教皇") -> dict:
        """获取层级树"""
        if root not in self.agents:
            return {}
        
        node = self.agents[root]
        
        return {
            "id": node.id,
            "name": node.name,
            "role": node.role,
            "level": node.level.name,
            "children": [self.get_hierarchy_tree(child) for child in node.children]
        }
    
    def list_all_agents(self) -> List[dict]:
        """列出所有Agent"""
        return [
            {
                "id": node.id,
                "name": node.name,
                "role": node.role,
                "level": node.level.name,
                "parent": node.parent,
                "children_count": len(node.children),
                "skills_count": len(node.skills),
                "is_temp": node.is_temp
            }
            for node in self.agents.values()
        ]
    
    def get_statistics(self) -> dict:
        """获取统计信息"""
        stats = {
            "total": len(self.agents),
            "by_level": {},
            "temp_agents": []
        }
        
        for node in self.agents.values():
            level_name = node.level.name
            stats["by_level"][level_name] = stats["by_level"].get(level_name, 0) + 1
            
            if node.is_temp:
                stats["temp_agents"].append({
                    "id": node.id,
                    "expires_at": node.expires_at
                })
        
        return stats


# ==================== CLI ====================
def main():
    import argparse
    parser = argparse.ArgumentParser(description='层级路由管理')
    parser.add_argument('--list', action='store_true', help='列出所有Agent')
    parser.add_argument('--tree', action='store_true', help='显示层级树')
    parser.add_argument('--check', nargs=2, metavar=("FROM", "TO"), help='检查路由')
    parser.add_argument('--add', nargs=4, metavar=("ID", "NAME", "ROLE", "PARENT"), help='添加Agent')
    parser.add_argument('--remove', help='移除Agent')
    parser.add_argument('--team', help='获取团队成员')
    parser.add_argument('--stats', action='store_true', help='统计信息')
    parser.add_argument('--config', default='config/agents.json', help='配置文件路径')
    
    args = parser.parse_args()
    
    router = HierarchicalRouter(args.config)
    
    if args.list:
        for agent in router.list_all_agents():
            print(f"{agent['id']:10} | {agent['level']:10} | {agent['role']}")
    
    elif args.tree:
        import json
        tree = router.get_hierarchy_tree()
        print(json.dumps(tree, ensure_ascii=False, indent=2))
    
    elif args.check:
        result = router.route_message(args.check[0], args.check[1], "test")
        print(json.dumps(result, ensure_ascii=False, indent=2))
    
    elif args.add:
        router.add_agent(
            args.add[0], args.add[1], args.add[2], args.add[3]
        )
        router.save_config(args.config)
        print(f"已添加: {args.add[0]}")
    
    elif args.remove:
        router.remove_agent(args.remove)
        router.save_config(args.config)
        print(f"已移除: {args.remove}")
    
    elif args.team:
        team = router.get_team(args.team)
        print(f"团队成员: {team}")
    
    elif args.stats:
        stats = router.get_statistics()
        print(json.dumps(stats, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
