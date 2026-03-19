#!/usr/bin/env python3
"""
Agent工厂 - 教皇动态创建/销毁临时Agent
支持运行时创建专家Agent，项目结束后自动销毁
"""
import os
import sys
import json
import time
import logging
import uuid
from pathlib import Path
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta

BASE = Path(__file__).parent.parent
sys.path.insert(0, str(BASE / 'scripts'))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [Factory] %(levelname)s: %(message)s',
    datefmt='%H:%M:%S'
)
log = logging.getLogger('factory')

# ==================== 数据类 ====================
@dataclass
class TempAgentConfig:
    """临时Agent配置"""
    id: str
    name: str
    role: str
    parent: str  # 教皇
    skills: List[str]
    description: str
    created_at: float = field(default_factory=time.time)
    expires_at: float
    status: str = "active"  # active, expired, destroyed
    metadata: Dict[str, Any] = field(default_factory=dict)
    feishu_enabled: bool = False
    feishu_open_id: Optional[str] = None

@dataclass
class ProjectContext:
    """项目上下文"""
    id: str
    name: str
    description: str
    created_by: str  # 教皇
    created_at: float = field(default_factory=time.time)
    agents: List[str] = field(default_factory=list)  # 参与的临时Agent
    status: str = "active"  # active, completed, archived

# ==================== Agent工厂 ====================
class AgentFactory:
    """教皇动态创建Agent的工厂"""
    
    def __init__(self, config_path: str = None, router=None):
        self.config_path = config_path or "config/temp_agents.json"
        self.router = router  # 层级路由器
        self.temp_agents: Dict[str, TempAgentConfig] = {}
        self.projects: Dict[str, ProjectContext] = {}
        
        # 技能模板库
        self.skill_templates = self._init_skill_templates()
        
        # 加载已存在的临时Agent
        self._load()
    
    def _init_skill_templates(self) -> Dict[str, Dict]:
        """初始化技能模板"""
        return {
            # 金融领域
            "finance": {
                "name": "金融专家",
                "skills": ["financial-analysis", "risk-assessment", "investment-strategy"],
                "description": "擅长金融市场分析、投资策略、风险管理"
            },
            "accounting": {
                "name": "会计专家",
                "skills": ["accounting", "tax-planning", "audit"],
                "description": "擅长财务报表、税务规划、审计"
            },
            
            # 技术领域
            "devops": {
                "name": "DevOps专家",
                "skills": ["ci-cd", "infrastructure", "cloud-native"],
                "description": "擅长持续集成、云原生、基础设施"
            },
            "security": {
                "name": "安全专家",
                "skills": ["penetration-test", "code-audit", "compliance"],
                "description": "擅长安全审计、渗透测试、合规"
            },
            "data-engineer": {
                "name": "数据工程师",
                "skills": ["etl", "data-warehouse", "big-data"],
                "description": "擅长数据工程、数据仓库、大数据"
            },
            
            # 业务领域
            "marketing": {
                "name": "营销专家",
                "skills": ["market-research", "brand-strategy", "digital-marketing"],
                "description": "擅长市场研究、品牌策略、数字营销"
            },
            "sales": {
                "name": "销售专家",
                "skills": ["sales-strategy", "crm", "customer-relation"],
                "description": "擅长销售策略、客户关系管理"
            },
            "product": {
                "name": "产品专家",
                "skills": ["product-design", "ux-research", "roadmap"],
                "description": "擅长产品设计、用户体验、路线图"
            },
            
            # 法律领域
            "legal": {
                "name": "法律专家",
                "skills": ["contract-review", "ip-law", "compliance"],
                "description": "擅长合同审查、知识产权、合规"
            },
            
            # 通用
            "research": {
                "name": "研究专家",
                "skills": ["literature-review", "data-analysis", "report-writing"],
                "description": "擅长文献综述、数据分析、报告撰写"
            },
            "consultant": {
                "name": "咨询顾问",
                "skills": ["business-analysis", "process-optimization", "strategy"],
                "description": "擅长业务分析、流程优化、战略规划"
            }
        }
    
    def _load(self):
        """加载配置"""
        if not os.path.exists(self.config_path):
            return
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 加载临时Agent
            for agent_id, info in data.get("agents", {}).items():
                self.temp_agents[agent_id] = TempAgentConfig(
                    id=agent_id,
                    name=info["name"],
                    role=info["role"],
                    parent=info["parent"],
                    skills=info["skills"],
                    description=info.get("description", ""),
                    created_at=info.get("created_at", time.time()),
                    expires_at=info["expires_at"],
                    status=info.get("status", "active"),
                    metadata=info.get("metadata", {}),
                    feishu_enabled=info.get("feishu_enabled", False),
                    feishu_open_id=info.get("feishu_open_id")
                )
            
            # 加载项目
            for proj_id, info in data.get("projects", {}).items():
                self.projects[proj_id] = ProjectContext(
                    id=proj_id,
                    name=info["name"],
                    description=info.get("description", ""),
                    created_by=info["created_by"],
                    created_at=info.get("created_at", time.time()),
                    agents=info.get("agents", []),
                    status=info.get("status", "active")
                )
            
            log.info(f"加载配置: {len(self.temp_agents)} 个临时Agent, {len(self.projects)} 个项目")
        except Exception as e:
            log.error(f"加载配置失败: {e}")
    
    def _save(self):
        """保存配置"""
        os.makedirs(os.path.dirname(self.config_path) or ".", exist_ok=True)
        
        data = {
            "agents": {},
            "projects": {}
        }
        
        # 保存临时Agent
        for agent_id, agent in self.temp_agents.items():
            data["agents"][agent_id] = {
                "name": agent.name,
                "role": agent.role,
                "parent": agent.parent,
                "skills": agent.skills,
                "description": agent.description,
                "created_at": agent.created_at,
                "expires_at": agent.expires_at,
                "status": agent.status,
                "metadata": agent.metadata,
                "feishu_enabled": agent.feishu_enabled,
                "feishu_open_id": agent.feishu_open_id
            }
        
        # 保存项目
        for proj_id, proj in self.projects.items():
            data["projects"][proj_id] = {
                "name": proj.name,
                "description": proj.description,
                "created_by": proj.created_by,
                "created_at": proj.created_at,
                "agents": proj.agents,
                "status": proj.status
            }
        
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        log.info(f"配置已保存: {self.config_path}")
    
    # ---- Agent创建 ----
    def create_temp_agent(
        self,
        name: str,
        skill_type: str,
        parent: str = "教皇",
        expires_hours: int = 24,
        description: str = "",
        feishu_enabled: bool = False,
        metadata: Dict[str, Any] = None
    ) -> TempAgentConfig:
        """创建临时Agent"""
        
        # 验证技能模板
        if skill_type not in self.skill_templates:
            log.warning(f"未知技能类型: {skill_type}，使用自定义")
            skills = [skill_type]
            role = name
        else:
            template = self.skill_templates[skill_type]
            skills = template["skills"]
            role = template["name"]
            description = description or template["description"]
        
        # 生成ID
        agent_id = f"temp_{skill_type}_{uuid.uuid4().hex[:8]}"
        
        # 计算过期时间
        expires_at = time.time() + expires_hours * 3600
        
        # 创建配置
        agent = TempAgentConfig(
            id=agent_id,
            name=name or role,
            role=role,
            parent=parent,
            skills=skills,
            description=description,
            expires_at=expires_at,
            feishu_enabled=feishu_enabled,
            metadata=metadata or {}
        )
        
        self.temp_agents[agent_id] = agent
        
        # 注册到路由器 (如果可用)
        if self.router:
            try:
                from hierarchical_router import AgentLevel
                self.router.add_agent(
                    agent_id=agent_id,
                    name=agent.name,
                    role=agent.role,
                    parent=parent,
                    level=AgentLevel.SPECIALIST,
                    skills=skills
                )
                log.info(f"已注册到层级路由: {agent_id}")
            except Exception as e:
                log.warning(f"注册层级路由失败: {e}")
        
        self._save()
        
        log.info(f"创建临时Agent: {agent_id}, 过期: {expires_hours}h")
        return agent
    
    def create_project_agent(
        self,
        project_name: str,
        skill_types: List[str],
        parent: str = "教皇",
        expires_days: int = 7,
        description: str = ""
    ) -> ProjectContext:
        """创建项目组 (多个临时Agent)"""
        
        proj_id = f"proj_{uuid.uuid4().hex[:8]}"
        
        project = ProjectContext(
            id=proj_id,
            name=project_name,
            description=description,
            created_by=parent
        )
        
        # 为项目创建多个Agent
        for skill_type in skill_types:
            agent = self.create_temp_agent(
                name=f"{project_name}-{skill_type}",
                skill_type=skill_type,
                parent=parent,
                expires_hours=expires_days * 24,
                metadata={"project_id": proj_id}
            )
            project.agents.append(agent.id)
        
        self.projects[proj_id] = project
        self._save()
        
        log.info(f"创建项目: {proj_id}, 包含 {len(project.agents)} 个Agent")
        return project
    
    # ---- Agent销毁 ----
    def destroy_temp_agent(self, agent_id: str, reason: str = "") -> bool:
        """销毁临时Agent"""
        
        if agent_id not in self.temp_agents:
            log.warning(f"Agent不存在: {agent_id}")
            return False
        
        agent = self.temp_agents[agent_id]
        
        # 从路由器移除 (如果可用)
        if self.router:
            try:
                self.router.remove_agent(agent_id)
            except Exception as e:
                log.warning(f"从层级路由移除失败: {e}")
        
        # 更新状态
        agent.status = "destroyed"
        
        # 移除
        del self.temp_agents[agent_id]
        
        self._save()
        
        log.info(f"销毁Agent: {agent_id}, 原因: {reason}")
        return True
    
    def complete_project(self, project_id: str) -> bool:
        """完成项目，销毁所有相关Agent"""
        
        if project_id not in self.projects:
            return False
        
        project = self.projects[project_id]
        
        # 销毁所有Agent
        for agent_id in project.agents:
            self.destroy_temp_agent(agent_id, f"项目完成: {project.name}")
        
        project.status = "completed"
        self._save()
        
        log.info(f"项目完成: {project_id}")
        return True
    
    # ---- Agent查询 ----
    def get_temp_agent(self, agent_id: str) -> Optional[TempAgentConfig]:
        """获取临时Agent"""
        return self.temp_agents.get(agent_id)
    
    def list_temp_agents(self, parent: str = None, status: str = None) -> List[TempAgentConfig]:
        """列出临时Agent"""
        agents = list(self.temp_agents.values())
        
        if parent:
            agents = [a for a in agents if a.parent == parent]
        if status:
            agents = [a for a in agents if a.status == status]
        
        return agents
    
    def list_projects(self, status: str = None) -> List[ProjectContext]:
        """列出项目"""
        projects = list(self.projects.values())
        
        if status:
            projects = [p for p in projects if p.status == status]
        
        return projects
    
    # ---- 清理过期 ----
    def cleanup_expired(self) -> int:
        """清理过期Agent"""
        now = time.time()
        cleaned = 0
        
        for agent_id in list(self.temp_agents.keys()):
            agent = self.temp_agents[agent_id]
            
            if agent.expires_at < now and agent.status == "active":
                self.destroy_temp_agent(agent_id, "过期自动销毁")
                cleaned += 1
        
        if cleaned > 0:
            log.info(f"清理过期Agent: {cleaned} 个")
        
        return cleaned
    
    def get_expiring_agents(self, hours: int = 24) -> List[TempAgentConfig]:
        """获取即将过期的Agent"""
        threshold = time.time() + hours * 3600
        return [
            agent for agent in self.temp_agents.values()
            if agent.expires_at <= threshold and agent.status == "active"
        ]
    
    # ---- 续期 ----
    def extend_agent(self, agent_id: str, hours: int = 24) -> bool:
        """延长Agent过期时间"""
        
        if agent_id not in self.temp_agents:
            return False
        
        agent = self.temp_agents[agent_id]
        agent.expires_at += hours * 3600
        self._save()
        
        log.info(f"延长Agent: {agent_id}, +{hours}h")
        return True


# ==================== CLI ====================
def main():
    import argparse
    parser = argparse.ArgumentParser(description='Agent工厂')
    parser.add_argument('--create', nargs=2, metavar=("NAME", "SKILL"), help='创建临时Agent')
    parser.add_argument('--project', nargs=2, metavar=("NAME", "SKILLS"), help='创建项目组 (逗号分隔技能)')
    parser.add_argument('--destroy', help='销毁Agent')
    parser.add_argument('--complete', help='完成项目')
    parser.add_argument('--list', action='store_true', help='列出临时Agent')
    parser.add_argument('--projects', action='store_true', help='列出项目')
    parser.add_argument('--cleanup', action='store_true', help='清理过期Agent')
    parser.add_argument('--expiring', type=int, help='查看即将过期的Agent')
    parser.add_argument('--extend', nargs=2, metavar=("AGENT", "HOURS"), help='延长Agent')
    parser.add_argument('--config', default='config/temp_agents.json', help='配置文件')
    
    args = parser.parse_args()
    
    factory = AgentFactory(args.config)
    
    if args.create:
        agent = factory.create_temp_agent(
            name=args.create[0],
            skill_type=args.create[1],
            expires_hours=24
        )
        print(f"创建成功: {agent.id}")
    
    elif args.project:
        skills = args.project[1].split(",")
        proj = factory.create_project_agent(
            project_name=args.project[0],
            skill_types=skills,
            expires_days=7
        )
        print(f"项目创建成功: {proj.id}, 包含 {len(proj.agents)} 个Agent")
    
    elif args.destroy:
        factory.destroy_temp_agent(args.destroy)
        print(f"已销毁: {args.destroy}")
    
    elif args.complete:
        factory.complete_project(args.complete)
        print(f"项目已完成: {args.complete}")
    
    elif args.list:
        for agent in factory.list_temp_agents():
            print(f"{agent.id:30} | {agent.name:15} | {agent.role:10} | 过期: {datetime.fromtimestamp(agent.expires_at)}")
    
    elif args.projects:
        for proj in factory.list_projects():
            print(f"{proj.id:20} | {proj.name:20} | {len(proj.agents)} agents | {proj.status}")
    
    elif args.cleanup:
        count = factory.cleanup_expired()
        print(f"清理: {count} 个")
    
    elif args.expiring:
        for agent in factory.get_expiring_agents(args.expiring):
            remaining = int((agent.expires_at - time.time()) / 3600)
            print(f"{agent.id:30} | 剩余 {remaining}h")

if __name__ == '__main__':
    main()
