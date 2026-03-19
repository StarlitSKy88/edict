#!/usr/bin/env python3
"""
Edict 知识图谱
"""
import json
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set
from collections import defaultdict

BASE = Path(__file__).parent.parent.parent
KG_FILE = BASE / 'data' / 'knowledge_graph.json'

@dataclass
class Entity:
    """实体"""
    id: str
    type: str  # agent, task, skill
    properties: Dict = field(default_factory=dict)

@dataclass
class Relation:
    """关系"""
    from_id: str
    to_id: str
    type: str
    properties: Dict = field(default_factory=dict)

class KnowledgeGraph:
    """知识图谱"""
    
    def __init__(self):
        self.entities: Dict[str, Entity] = {}
        self.relations: List[Relation] = []
        self.adjacency: Dict[str, Dict[str, Set[str]]] = defaultdict(lambda: defaultdict(set))
        
        self._load()
    
    def _load(self):
        """加载图谱"""
        if KG_FILE.exists():
            data = json.loads(KG_FILE.read_text())
            
            for e in data.get('entities', []):
                self.entities[e['id']] = Entity(e['id'], e['type'], e.get('properties', {}))
            
            for r in data.get('relations', []):
                relation = Relation(r['from'], r['to'], r['type'])
                self.relations.append(relation)
                self.adjacency[r['from']][r['type']].add(r['to'])
    
    def _save(self):
        """保存图谱"""
        data = {
            'entities': [
                {'id': e.id, 'type': e.type, 'properties': e.properties}
                for e in self.entities.values()
            ],
            'relations': [
                {'from': r.from_id, 'to': r.to_id, 'type': r.type}
                for r in self.relations
            ]
        }
        KG_FILE.parent.mkdir(parents=True, exist_ok=True)
        KG_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    
    # ---- 实体操作 ----
    def add_entity(self, entity_id: str, entity_type: str, properties: Dict = None):
        """添加实体"""
        self.entities[entity_id] = Entity(entity_id, entity_type, properties or {})
        self._save()
    
    def get_entity(self, entity_id: str) -> Optional[Entity]:
        """获取实体"""
        return self.entities.get(entity_id)
    
    def query_entities(self, entity_type: str = None) -> List[Entity]:
        """查询实体"""
        if entity_type:
            return [e for e in self.entities.values() if e.type == entity_type]
        return list(self.entities.values())
    
    # ---- 关系操作 ----
    def add_relation(self, from_id: str, relation_type: str, to_id: str, properties: Dict = None):
        """添加关系"""
        relation = Relation(from_id, to_id, relation_type, properties or {})
        self.relations.append(relation)
        self.adjacency[from_id][relation_type].add(to_id)
        self._save()
    
    def get_relations(self, entity_id: str, relation_type: str = None) -> List[str]:
        """获取关系"""
        if relation_type:
            return list(self.adjacency.get(entity_id, {}).get(relation_type, set()))
        
        results = []
        for rtype, targets in self.adjacency.get(entity_id, {}).items():
            results.extend(targets)
        return results
    
    # ---- 推理 ----
    def recommend(self, entity_id: str, relation_type: str) -> List[str]:
        """推荐相关实体"""
        return self.get_relations(entity_id, relation_type)
    
    def find_path(self, start: str, end: str, max_depth: int = 3) -> List[List[str]]:
        """查找路径"""
        paths = []
        
        def dfs(current: str, target: str, path: List[str], visited: Set[str]):
            if current == target:
                paths.append(path + [current])
                return
            if len(path) >= max_depth:
                return
            if current in visited:
                return
            
            visited.add(current)
            
            for next_entity in self.get_relations(current):
                dfs(next_entity, target, path + [current], visited.copy())
        
        dfs(start, end, [], set())
        return paths
    
    # ---- 初始化默认图谱 ----
    def init_default(self):
        """初始化默认Agent关系"""
        # Agent实体
        agents = [
            ("pope", "agent", {"role": "教皇", "function": "消息分拣"}),
            ("cardinal", "agent", {"role": "红衣主教团", "function": "规划"}),
            ("cardinal_office", "agent", {"role": "枢机处", "function": "审核"}),
            ("bishop", "agent", {"role": "主教团", "function": "调度"}),
            ("guild", "agent", {"role": "工匠行会", "function": "技术"}),
            ("treasury", "agent", {"role": "财政部", "function": "财务"}),
            ("knights", "agent", {"role": "骑士团", "function": "安全"}),
            ("inquisition", "agent", {"role": "宗教裁判所", "function": "合规"}),
        ]
        
        for aid, atype, props in agents:
            self.add_entity(aid, atype, props)
        
        # Agent关系
        self.add_relation("pope", "delegates_to", "cardinal")
        self.add_relation("cardinal", "reviews", "cardinal_office")
        self.add_relation("cardinal_office", "approves", "bishop")
        self.add_relation("bishop", "dispatches", "guild")
        self.add_relation("bishop", "dispatches", "treasury")
        self.add_relation("bishop", "dispatches", "knights")
        
        print("✅ 知识图谱初始化完成")

if __name__ == '__main__':
    kg = KnowledgeGraph()
    
    # 测试
    kg.init_default()
    
    print("\n=== Agent列表 ===")
    for e in kg.query_entities("agent"):
        print(f"  {e.id}: {e.properties}")
    
    print("\n=== 教皇委派关系 ===")
    print(kg.get_relations("pope", "delegates_to"))
