#!/usr/bin/env python3
"""
Edict RAG记忆系统 - 向量检索+语义相似
支持: 嵌入生成、向量检索、Context压缩、RAG增强
"""
import os
import sys
import json
import time
import hashlib
import logging
from pathlib import Path
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, Any, list
from abc import ABC, abstractmethod
import numpy as np

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(name)s] %(message)s', datefmt='%H:%M:%S')
log = logging.getLogger('rag-memory')

BASE = Path(__file__).parent.parent
DATA = BASE / 'data'
MEMORY_DIR = DATA / 'memory'
MEMORY_DIR.mkdir(parents=True, exist_ok=True)

# ==================== 配置 ====================
class Config:
    EMBEDDING_MODEL = os.getenv('EMBEDDING_MODEL', 'sentence-transformers/all-MiniLM-L6-v2')
    VECTOR_DIM = 384  # MiniLM-L6-v2 输出维度
    SIMILARITY_THRESHOLD = float(os.getenv('MEMORY_SIMILARITY_THRESHOLD', '0.7'))
    MAX_CONTEXT_TOKENS = int(os.getenv('MAX_CONTEXT_TOKENS', '4000'))
    ENABLE_RAG = os.getenv('ENABLE_RAG', 'true').lower() == 'true'

config = Config()

# ==================== 嵌入接口 ====================
class EmbeddingProvider(ABC):
    """嵌入Provider抽象类"""
    
    @abstractmethod
    def encode(self, texts: list[str]) -> list[list[float]]:
        """将文本编码为向量"""
        pass

class LocalEmbeddingProvider(EmbeddingProvider):
    """本地嵌入Provider (sentence-transformers)"""
    
    def __init__(self, model_name: str = None):
        model_name = model_name or config.EMBEDDING_MODEL
        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(model_name)
            log.info(f"加载嵌入模型: {model_name}")
        except ImportError:
            log.warning("sentence-transformers未安装，使用随机向量")
            self.model = None
    
    def encode(self, texts: list[str]) -> list[list[float]]:
        if self.model:
            embeddings = self.model.encode(texts, convert_to_numpy=True)
            return embeddings.tolist()
        # 降级方案: 随机向量
        return [[hashlib.md5(t.encode()).hexdigest()[i:i+8] 
                for i in range(0, 32, 8)] 
                for t in texts]

class MockEmbeddingProvider(EmbeddingProvider):
    """Mock嵌入Provider (开发测试用)"""
    
    def encode(self, texts: list[str]) -> list[list[float]]:
        # 简单hash作为伪向量
        vectors = []
        for text in texts:
            h = hashlib.sha256(text.encode()).digest()
            # 扩展到384维
            vector = list(h) * 2 + [0] * (384 - len(h) * 2)
            vectors.append(vector[:384])
        return vectors

# ==================== 数据类 ====================
class MemoryType(Enum):
    WORKING = "working"
    SHORT_TERM = "short_term" 
    LONG_TERM = "long_term"
    PATTERN = "pattern"

@dataclass
class Memory:
    id: str
    content: str
    memory_type: str
    agent_id: str
    task_id: Optional[str] = None
    importance: float = 0.5
    tags: list[str] = field(default_factory=list)
    vector: Optional[list[float]] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    accessed_at: str = field(default_factory=lambda: datetime.now().isoformat())
    access_count: int = 0

# ==================== 核心类 ====================
class RAGMemorySystem:
    """RAG增强的记忆系统"""
    
    def __init__(self):
        # 存储文件
        self.memories_file = MEMORY_DIR / 'rag_memories.json'
        self.vectors_file = MEMORY_DIR / 'vectors.npy'
        
        # 初始化嵌入Provider
        try:
            self.embedding = LocalEmbeddingProvider()
        except:
            self.embedding = MockEmbeddingProvider()
        
        # 加载已有记忆
        self.memories: list[Memory] = self._load_memories()
        self.vectors: np.ndarray = self._load_vectors()
        
        log.info(f"记忆系统初始化完成: {len(self.memories)}条记忆")
    
    def _load_memories(self) -> list[Memory]:
        if not self.memories_file.exists():
            return []
        try:
            data = json.loads(self.memories_file.read_text())
            return [Memory(**m) for m in data]
        except:
            return []
    
    def _load_vectors(self) -> np.ndarray:
        if self.vectors_file.exists():
            try:
                return np.load(self.vectors_file)
            except:
                pass
        return np.array([])
    
    def _save(self):
        """保存记忆和向量"""
        # 保存记忆
        self.memories_file.write_text(
            json.dumps([asdict(m) for m in self.memories], ensure_ascii=False, indent=2)
        )
        # 保存向量
        if len(self.vectors) > 0:
            np.save(self.vectors_file, self.vectors)
    
    def _generate_id(self, content: str) -> str:
        return hashlib.md5(content.encode()).hexdigest()[:12]
    
    # ---- 存储方法 ----
    def store(
        self,
        content: str,
        memory_type: str,
        agent_id: str,
        task_id: Optional[str] = None,
        importance: float = 0.5,
        tags: list[str] = None,
        generate_embedding: bool = True
    ) -> str:
        """存储记忆 (支持RAG)"""
        
        # 生成嵌入
        vector = None
        if generate_embedding and config.ENABLE_RAG:
            vectors = self.embedding.encode([content])
            vector = vectors[0]
        
        memory = Memory(
            id=self._generate_id(content),
            content=content,
            memory_type=memory_type,
            agent_id=agent_id,
            task_id=task_id,
            importance=importance,
            tags=tags or [],
            vector=vector
        )
        
        # 添加到列表
        self.memories.append(memory)
        
        # 更新向量矩阵
        if vector:
            if len(self.vectors) == 0:
                self.vectors = np.array([vector])
            else:
                self.vectors = np.vstack([self.vectors, vector])
        
        self._save()
        log.info(f"存储记忆: {memory.id} ({memory_type})")
        
        return memory.id
    
    # ---- 检索方法 ----
    def retrieve(
        self,
        query: str,
        agent_id: Optional[str] = None,
        memory_type: Optional[str] = None,
        limit: int = 5
    ) -> list[Memory]:
        """语义检索 - 向量相似度"""
        
        if not config.ENABLE_RAG or len(self.vectors) == 0:
            # 降级到关键词匹配
            return self._keyword_search(query, agent_id, memory_type, limit)
        
        # 生成查询向量
        query_vectors = self.embedding.encode([query])
        query_vector = np.array(query_vectors[0])
        
        # 计算相似度
        similarities = []
        for i, memory in enumerate(self.memories):
            if memory.vector:
                # 余弦相似度
                mem_vector = np.array(memory.vector)
                sim = np.dot(query_vector, mem_vector) / (
                    np.linalg.norm(query_vector) * np.linalg.norm(mem_vector) + 1e-8
                )
                similarities.append((i, sim, memory))
        
        # 过滤和排序
        results = []
        for idx, sim, mem in similarities:
            # 过滤
            if agent_id and mem.agent_id != agent_id:
                continue
            if memory_type and mem.memory_type != memory_type:
                continue
            if sim < config.SIMILARITY_THRESHOLD:
                continue
            
            results.append((sim, mem))
        
        # 按相似度排序
        results.sort(key=lambda x: x[0], reverse=True)
        
        # 更新访问记录
        for _, mem in results[:limit]:
            mem.accessed_at = datetime.now().isoformat()
            mem.access_count += 1
        
        self._save()
        
        return [mem for _, mem in results[:limit]]
    
    def _keyword_search(
        self,
        query: str,
        agent_id: Optional[str],
        memory_type: Optional[str],
        limit: int
    ) -> list[Memory]:
        """关键词搜索 (降级方案)"""
        
        results = []
        query_words = set(query.lower().split())
        
        for mem in self.memories:
            # 过滤
            if agent_id and mem.agent_id != agent_id:
                continue
            if memory_type and mem.memory_type != memory_type:
                continue
            
            # 计算关键词匹配数
            content_words = set(mem.content.lower().split())
            match_count = len(query_words & content_words)
            
            if match_count > 0:
                results.append((match_count * mem.importance, mem))
        
        results.sort(key=lambda x: x[0], reverse=True)
        return [mem for _, mem in results[:limit]]
    
    # ---- Context生成 ----
    def compress_context(
        self,
        agent_id: str,
        query: str = "",
        max_tokens: int = None
    ) -> str:
        """生成RAG增强的Context"""
        
        max_tokens = max_tokens or config.MAX_CONTEXT_TOKENS
        
        # 检索相关记忆
        if query:
            memories = self.retrieve(agent_id=agent_id, limit=10)
        else:
            # 无查询时获取最近的
            memories = [m for m in self.memories if m.agent_id == agent_id][-10:]
        
        if not memories:
            return ""
        
        # 构建Context
        context_parts = ["## 相关经验"]
        
        for m in memories:
            context_parts.append(f"### [{m.memory_type}] 重要性: {m.importance:.2f}")
            context_parts.append(m.content[:500])
            context_parts.append("")
        
        context = "\n".join(context_parts)
        
        # 截断
        if len(context) > max_tokens * 4:  # 粗略估计
            context = context[:max_tokens * 4] + "..."
        
        return context
    
    # ---- 学习方法 ----
    def learn_from_task(
        self,
        agent_id: str,
        task_id: str,
        task_content: str,
        success: bool,
        lessons: list[str] = None
    ):
        """从任务中学习"""
        
        # 1. 存储任务记忆
        importance = 0.8 if success else 0.6
        self.store(
            content=f"任务 {task_id}: {task_content}",
            memory_type=MemoryType.WORKING.value,
            agent_id=agent_id,
            task_id=task_id,
            importance=importance
        )
        
        # 2. 如果失败，存储教训
        if not success and lessons:
            for lesson in lessons:
                self.store(
                    content=lesson,
                    memory_type=MemoryType.PATTERN.value,
                    agent_id=agent_id,
                    task_id=task_id,
                    importance=0.7,
                    tags=['failure', 'lesson']
                )
        
        # 3. 成功则提升重要性
        if success:
            for mem in self.memories:
                if mem.task_id == task_id:
                    mem.importance = min(1.0, mem.importance + 0.1)
            
            self._save()
    
    # ---- 清理方法 ----
    def cleanup(self, days: int = 7):
        """清理过期记忆"""
        cutoff = datetime.now() - timedelta(days=days)
        
        original_count = len(self.memories)
        
        self.memories = [
            m for m in self.memories 
            if datetime.fromisoformat(m.created_at) > cutoff 
            or m.memory_type == MemoryType.LONG_TERM.value
        ]
        
        # 重建向量矩阵
        self.vectors = np.array([
            m.vector for m in self.memories if m.vector
        ]) if self.memories else np.array([])
        
        self._save()
        
        removed = original_count - len(self.memories)
        log.info(f"清理完成: 移除{removed}条记忆")

# ==================== CLI ====================
def main():
    import argparse
    parser = argparse.ArgumentParser(description='Edict RAG记忆系统')
    parser.add_argument('--store', '-s', nargs='+', help='存储: type agent content')
    parser.add_argument('--retrieve', '-r', help='检索关键词')
    parser.add_argument('--agent', '-a', help='Agent ID')
    parser.add_argument('--type', '-t', choices=['working', 'short_term', 'long_term', 'pattern'])
    parser.add_argument('--limit', '-l', type=int, default=5)
    parser.add_argument('--compress', '-c', action='store_true', help='生成Context')
    parser.add_argument('--learn', nargs='+', help='学习: task_id success lessons...')
    parser.add_argument('--cleanup', action='store_true', help='清理过期记忆')
    
    args = parser.parse_args()
    
    rag = RAGMemorySystem()
    
    if args.store and len(args.store) >= 3:
        memory_type = args.store[0]
        agent_id = args.store[1]
        content = ' '.join(args.store[2:])
        
        rag.store(content, memory_type, agent_id)
        print(f"✅ 已存储记忆")
    
    elif args.retrieve:
        memories = rag.retrieve(
            args.retrieve,
            agent_id=args.agent,
            memory_type=args.type,
            limit=args.limit
        )
        print(f"找到{len(memories)}条相关记忆:")
        for m in memories:
            print(f"- [{m.memory_type}] {m.content[:80]}...")
    
    elif args.compress and args.agent:
        context = rag.compress_context(args.agent, args.retrieve or "")
        print(context)
    
    elif args.learn and len(args.learn) >= 3:
        task_id = args.learn[0]
        success = args.learn[1].lower() == 'true'
        lessons = args.learn[2:] if len(args.learn) > 2 else []
        
        rag.learn_from_task(args.agent, task_id, "", success, lessons)
        print(f"✅ 已记录学习")
    
    elif args.cleanup:
        rag.cleanup()
        print(f"✅ 清理完成")

if __name__ == '__main__':
    main()
