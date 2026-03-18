#!/usr/bin/env python3
"""
Edict 记忆系统 - 多级记忆 + 经验复用
"""
import json
import time
import logging
from pathlib import Path
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, Any
import hashlib

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(name)s] %(message)s', datefmt='%H:%M:%S')
log = logging.getLogger('memory')

BASE = Path(__file__).parent.parent
DATA = BASE / 'data'
MEMORY_DIR = DATA / 'memory'
MEMORY_DIR.mkdir(parents=True, exist_ok=True)

class MemoryType(Enum):
    WORKING = "working"      # 工作记忆 (当前任务)
    SHORT_TERM = "short_term" # 短期记忆 (24小时)
    LONG_TERM = "long_term"   # 长期记忆 (历史经验)
    PATTERN = "pattern"       # 模式记忆 (可复用经验)

@dataclass
class Memory:
    """单条记忆"""
    id: str
    content: str
    memory_type: str
    agent_id: str
    task_id: Optional[str] = None
    importance: float = 0.5  # 0-1 重要性
    tags: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    accessed_at: str = field(default_factory=lambda: datetime.now().isoformat())
    access_count: int = 0
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Memory':
        return cls(**data)

class MemorySystem:
    """Edict 记忆系统"""
    
    def __init__(self):
        self.short_term_file = MEMORY_DIR / 'short_term.json'
        self.long_term_file = MEMORY_DIR / 'long_term.json'
        self.pattern_file = MEMORY_DIR / 'patterns.json'
        
        # 初始化文件
        for f in [self.short_term_file, self.long_term_file, self.pattern_file]:
            if not f.exists():
                f.write_text('[]')
    
    def _generate_id(self, content: str) -> str:
        """生成记忆ID"""
        return hashlib.md5(content.encode()).hexdigest()[:12]
    
    def store(
        self,
        content: str,
        memory_type: str,
        agent_id: str,
        task_id: Optional[str] = None,
        importance: float = 0.5,
        tags: list[str] = None
    ) -> str:
        """存储记忆"""
        
        memory = Memory(
            id=self._generate_id(content),
            content=content,
            memory_type=memory_type,
            agent_id=agent_id,
            task_id=task_id,
            importance=importance,
            tags=tags or []
        )
        
        # 根据类型存储
        if memory_type == MemoryType.WORKING.value:
            self._store_working(memory)
        elif memory_type == MemoryType.SHORT_TERM.value:
            self._store_short_term(memory)
        elif memory_type == MemoryType.LONG_TERM.value:
            self._store_long_term(memory)
        elif memory_type == MemoryType.PATTERN.value:
            self._store_pattern(memory)
        
        log.info(f"存储记忆: {memory.id} ({memory_type}) - {content[:50]}...")
        return memory.id
    
    def _store_working(self, memory: Memory):
        """存储工作记忆"""
        # 工作记忆存 Redis 或文件
        working_file = MEMORY_DIR / f'working_{memory.agent_id}.json'
        memories = []
        if working_file.exists():
            memories = json.loads(working_file.read_text())
        
        memories.append(memory.to_dict())
        
        # 只保留最近10条
        memories = memories[-10:]
        working_file.write_text(json.dumps(memories, ensure_ascii=False, indent=2))
    
    def _store_short_term(self, memory: Memory):
        """存储短期记忆"""
        memories = json.loads(self.short_term_file.read_text())
        
        # 检查是否已存在
        existing = [m for m in memories if m['id'] != memory.id]
        existing.append(memory.to_dict())
        
        self.short_term_file.write_text(json.dumps(existing, ensure_ascii=False, indent=2))
    
    def _store_long_term(self, memory: Memory):
        """存储长期记忆"""
        memories = json.loads(self.long_term_file.read_text())
        
        # 提升重要性
        memory.importance = min(1.0, memory.importance + 0.1)
        
        existing = [m for m in memories if m['id'] != memory.id]
        existing.append(memory.to_dict())
        
        self.long_term_file.write_text(json.dumps(existing, ensure_ascii=False, indent=2))
    
    def _store_pattern(self, memory: Memory):
        """存储模式记忆"""
        patterns = json.loads(self.pattern_file.read_text())
        
        # 检查是否已有相似模式
        similar = [p for p in patterns if p.get('content', '').split('\n')[0] == memory.content.split('\n')[0]]
        
        if similar:
            # 更新访问次数
            similar[0]['access_count'] = similar[0].get('access_count', 0) + 1
            similar[0]['accessed_at'] = memory.accessed_at
        else:
            patterns.append(memory.to_dict())
        
        self.pattern_file.write_text(json.dumps(patterns, ensure_ascii=False, indent=2))
    
    def retrieve(
        self,
        agent_id: Optional[str] = None,
        task_id: Optional[str] = None,
        memory_type: Optional[str] = None,
        limit: int = 5
    ) -> list[Memory]:
        """检索记忆"""
        results = []
        
        # 1. 检索工作记忆
        if not memory_type or memory_type == MemoryType.WORKING.value:
            if agent_id:
                working_file = MEMORY_DIR / f'working_{agent_id}.json'
                if working_file.exists():
                    results.extend(json.loads(working_file.read_text()))
        
        # 2. 检索短期记忆
        if not memory_type or memory_type == MemoryType.SHORT_TERM.value:
            short_term = json.loads(self.short_term_file.read_text())
            if agent_id:
                short_term = [m for m in short_term if m['agent_id'] == agent_id]
            results.extend(short_term)
        
        # 3. 检索长期记忆
        if not memory_type or memory_type == MemoryType.LONG_TERM.value:
            long_term = json.loads(self.long_term_file.read_text())
            if agent_id:
                long_term = [m for m in long_term if m['agent_id'] == agent_id]
            results.extend(long_term)
        
        # 按重要性排序
        results.sort(key=lambda m: m.get('importance', 0.5), reverse=True)
        
        return [Memory.from_dict(m) for m in results[:limit]]
    
    def retrieve_patterns(self, query: str = "", limit: int = 3) -> list[Memory]:
        """检索可复用的模式"""
        patterns = json.loads(self.pattern_file.read_text())
        
        # 按访问次数和重要性排序
        patterns.sort(key=lambda p: (p.get('access_count', 0), p.get('importance', 0.5)), reverse=True)
        
        return [Memory.from_dict(p) for p in patterns[:limit]]
    
    def compress_context(self, agent_id: str, max_length: int = 2000) -> str:
        """压缩上下文 - 生成记忆摘要"""
        
        # 1. 获取相关记忆
        memories = self.retrieve(agent_id=agent_id, limit=10)
        
        if not memories:
            return ""
        
        # 2. 生成摘要
        summary_parts = [f"## 相关经验 ({len(memories)}条)"]
        
        for m in memories:
            summary_parts.append(f"- **{m.memory_type}**: {m.content[:200]}")
        
        summary = '\n'.join(summary_parts)
        
        # 3. 截断
        if len(summary) > max_length:
            summary = summary[:max_length] + "..."
        
        return summary
    
    def cleanup(self):
        """清理过期记忆"""
        now = datetime.now()
        
        # 清理短期记忆 (24小时)
        short_term = json.loads(self.short_term_file.read_text())
        kept = []
        for m in short_term:
            created = datetime.fromisoformat(m['created_at'])
            if now - created < timedelta(hours=24):
                kept.append(m)
        
        # 超过100条的保留重要的
        if len(kept) > 100:
            kept.sort(key=lambda m: m.get('importance', 0.5), reverse=True)
            kept = kept[:100]
        
        self.short_term_file.write_text(json.dumps(kept, ensure_ascii=False, indent=2))
        
        log.info(f"清理完成: 保留 {len(kept)} 条短期记忆")
        
        return len(short_term) - len(kept)

# CLI 入口
def main():
    import argparse
    parser = argparse.ArgumentParser(description='Edict 记忆系统')
    parser.add_argument('--store', '-s', nargs='+', help='存储记忆: type agent content')
    parser.add_argument('--retrieve', '-r', help='检索记忆')
    parser.add_argument('--agent', '-a', help='Agent ID')
    parser.add_argument('--type', '-t', choices=['working', 'short_term', 'long_term', 'pattern'])
    parser.add_argument('--limit', '-l', type=int, default=5)
    parser.add_argument('--compress', '-c', action='store_true', help='压缩上下文')
    parser.add_argument('--cleanup', action='store_true', help='清理过期记忆')
    
    args = parser.parse_args()
    
    memory = MemorySystem()
    
    if args.store:
        # store type agent content
        if len(args.store) >= 3:
            memory_type = args.store[0]
            agent_id = args.store[1]
            content = ' '.join(args.store[2:])
            
            memory.store(content, memory_type, agent_id)
            print(f"✅ 已存储记忆")
        else:
            print("用法: --store type agent content...")
    
    elif args.compress and args.agent:
        summary = memory.compress_context(args.agent)
        print(summary)
    
    elif args.cleanup:
        deleted = memory.cleanup()
        print(f"✅ 已清理 {deleted} 条过期记忆")
    
    else:
        # 检索
        memories = memory.retrieve(agent_id=args.agent, memory_type=args.type, limit=args.limit)
        print(f"找到 {len(memories)} 条记忆:")
        for m in memories:
            print(f"- [{m.memory_type}] {m.content[:80]} (重要度: {m.importance})")

if __name__ == '__main__':
    main()
