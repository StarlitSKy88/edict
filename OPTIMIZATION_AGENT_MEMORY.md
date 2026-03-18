# Edict Agent 通信与记忆系统优化方案

## 一、当前问题分析

### 1.1 Agent 通信问题

| 问题 | 原因 | 影响 |
|------|------|------|
| Agent 无法唤起 | 网络超时/模型错误 | 任务卡死 |
| 任务卡死 | subagent 调用失败无重试 | 流程中断 |
| 无心跳检测 | 缺少健康检查 | 不知道卡在哪里 |
| 错误传递 | 异常未捕获 | 整个流程崩溃 |

### 1.2 记忆系统问题

| 问题 | 影响 |
|------|------|
| 无长期记忆 | 每次任务从零开始 |
| 无结构化存储 | 上下文混乱 |
| 无记忆检索 | 历史经验无法复用 |

---

## 二、Agent 通信优化方案

### 2.1 通信架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                    Agent 通信增强层                          │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    │
│  │ 超时检测   │    │ 重试机制   │    │ 心跳监控   │    │
│  │ (30s)     │    │ (3次指数)  │    │ (每10s)   │    │
│  └─────────────┘    └─────────────┘    └─────────────┘    │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    │
│  │ 错误降级   │    │ 状态恢复   │    │ 告警通知   │    │
│  │ (备用模型) │    │ (自动恢复) │    │ (飞书推送) │    │
│  └─────────────┘    └─────────────┘    └─────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 通信代理模块 (agent_communicator.py)

```python
#!/usr/bin/env python3
"""
Agent 通信代理 - 解决 Agent 唤起失败、任务卡死问题
"""
import asyncio
import time
import logging
from typing import Optional, Callable
from dataclasses import dataclass
from enum import Enum

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
    response: Optional[str]
    error: Optional[str]
    duration_ms: int
    retries: int

class AgentCommunicator:
    """Agent 通信代理 - 带重试、超时、心跳检测"""
    
    def __init__(
        self,
        timeout: int = 30,           # 超时时间
        max_retries: int = 3,         # 最大重试次数
        base_delay: float = 2.0,       # 基础延迟
        heartbeat_interval: int = 10   # 心跳间隔(秒)
    ):
        self.timeout = timeout
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.heartbeat_interval = heartbeat_interval
        
        # Agent 状态
        self.agent_status: dict[str, AgentStatus] = {}
        self.agent_heartbeat: dict[str, float] = {}
        
    async def call_agent(
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
                # 更新状态
                self.agent_status[agent_id] = AgentStatus.CALLING
                self.agent_heartbeat[agent_id] = time.time()
                
                # 执行调用
                result = await self._do_call(agent_id, message, subagent)
                
                # 成功
                duration_ms = int((time.time() - start_time) * 1000)
                self.agent_status[agent_id] = AgentStatus.SUCCESS
                
                return AgentCallResult(
                    success=True,
                    status=AgentStatus.SUCCESS,
                    response=result,
                    error=None,
                    duration_ms=duration_ms,
                    retries=attempt
                )
                
            except asyncio.TimeoutError:
                last_error = f"调用超时 ({self.timeout}s)"
                self.agent_status[agent_id] = AgentStatus.TIMEOUT
                
            except Exception as e:
                last_error = str(e)
                self.agent_status[agent_id] = AgentStatus.FAILED
                
            # 重试前等待
            if attempt < self.max_retries:
                delay = self.base_delay * (2 ** attempt)  # 指数退避
                await asyncio.sleep(delay)
                
        # 所有重试都失败
        duration_ms = int((time.time() - start_time) * 1000)
        
        # 尝试备用 Agent
        if fallback_agent and fallback_agent != agent_id:
            return await self.call_agent(fallback_agent, message, subagent, None)
        
        return AgentCallResult(
            success=False,
            status=self.agent_status.get(agent_id, AgentStatus.FAILED),
            response=None,
            error=last_error,
            duration_ms=duration_ms,
            retries=self.max_retries
        )
    
    async def _do_call(self, agent_id: str, message: str, subagent: bool) -> str:
        """实际执行 Agent 调用"""
        # TODO: 实现实际的 Agent 调用逻辑
        # 可以使用 subprocess 调用 openclaw CLI
        # 或使用 sessions_send API
        pass
    
    async def check_heartbeat(self) -> dict[str, bool]:
        """检查所有 Agent 心跳"""
        now = time.time()
        heartbeat_status = {}
        
        for agent_id, last_beat in self.agent_heartbeat.items():
            elapsed = now - last_beat
            heartbeat_status[agent_id] = elapsed < self.heartbeat_interval * 3
            
            if elapsed > self.heartbeat_interval * 3:
                # Agent 可能卡死
                self.agent_status[agent_id] = AgentStatus.UNREACHABLE
                
        return heartbeat_status
    
    async def recover_stuck_agent(self, agent_id: str) -> bool:
        """恢复卡住的 Agent"""
        # 1. 记录当前状态
        # 2. 尝试优雅终止
        # 3. 重新初始化
        # 4. 发送恢复消息
        pass
    
    def get_status(self) -> dict:
        """获取所有 Agent 状态"""
        return {
            "agents": self.agent_status,
            "heartbeats": {
                agent: (time.time() - beat) 
                for agent, beat in self.agent_heartbeat.items()
            }
        }
```

### 2.3 任务状态机增强

```python
#!/usr/bin/env python3
"""
任务状态机 - 带超时检测和自动恢复
"""
from enum import Enum
from typing import Optional
from dataclasses import dataclass
import time

class TaskState(Enum):
    PENDING = "pending"
    TAIZI = "taizi"
    ZHONGSHU = "zhongshu"
    MENXIA = "menxia"
    ASSIGNED = "assigned"
    DOING = "doing"
    REVIEW = "review"
    DONE = "done"
    BLOCKED = "blocked"
    FAILED = "failed"
    TIMEOUT = "timeout"

@dataclass
class TaskTimeout:
    state: TaskState
    timeout_seconds: int
    auto_action: Optional[str] = None

# 超时配置
TASK_TIMEOUTS = [
    TaskTimeout(TaskState.TAIZI, 60, "auto_forward"),       # 太子60秒未处理
    TaskTimeout(TaskState.ZHONGSHU, 300, "auto_remind"),     # 中书省5分钟未规划
    TaskTimeout(TaskState.MENXIA, 180, "auto_escalate"),     # 门下省3分钟未审核
    TaskTimeout(TaskState.ASSIGNED, 120, "auto_remind"),     # 尚书省2分钟未派发
    TaskTimeout(TaskState.DOING, 600, "auto_block"),         # 六部10分钟未完成
    TaskTimeout(TaskState.REVIEW, 180, "auto_escalate"),     # 尚书省3分钟未汇总
]

class TaskStateMachine:
    """任务状态机 - 带超时检测"""
    
    def __init__(self):
        self.timeouts = {t.state: t for t in TASK_TIMEOUTS}
        
    def check_timeout(self, task: dict) -> Optional[str]:
        """检查任务是否超时，返回处理建议"""
        state = TaskState(task.get("state", "pending"))
        updated_at = task.get("updatedAt", task.get("createdAt", ""))
        
        if not updated_at or state not in self.timeouts:
            return None
            
        # 计算时间差
        # TODO: 实现时间计算
        
        timeout_config = self.timeouts.get(state)
        if timeout_config and elapsed > timeout_config.timeout_seconds:
            return timeout_config.auto_action
            
        return None
    
    def auto_recover(self, task: dict, action: str) -> bool:
        """自动恢复"""
        if action == "auto_block":
            # 标记为阻塞
            task["state"] = "Blocked"
            task["auto_recovered"] = True
            return True
        elif action == "auto_remind":
            # 发送提醒
            # TODO: 实现提醒逻辑
            return True
        elif action == "auto_escalate":
            # 升级处理
            # TODO: 实现升级逻辑
            return True
            
        return False
```

---

## 三、记忆系统优化方案

### 3.1 记忆架构

```
┌─────────────────────────────────────────────────────────────────┐
│                    记忆系统架构                               │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    │
│  │ 工作记忆   │    │ 短期记忆   │    │ 长期记忆   │    │
│  │ (Context) │    │ (Redis)    │    │ (向量库)   │    │
│  │ 当前任务   │    │ 24小时内   │    │ >24小时   │    │
│  └─────────────┘    └─────────────┘    └─────────────┘    │
│                                                              │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    │
│  │ 语义检索   │    │ 经验提取   │    │ 模式学习   │    │
│  │ (向量相似)│    │ (规则)    │    │ (LLM)    │    │
│  └─────────────┘    └─────────────┘    └─────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 记忆存储设计

```python
#!/usr/bin/env python3
"""
Edict 记忆系统 - 多级记忆 + 向量检索
"""
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional
import json

class MemoryType(Enum):
    WORKING = "working"      # 工作记忆 (当前任务)
    SHORT_TERM = "short_term" # 短期记忆 (24小时)
    LONG_TERM = "long_term"   # 长期记忆 (历史经验)

@dataclass
class Memory:
    id: str
    content: str
    memory_type: MemoryType
    agent_id: str
    task_id: Optional[str]
    embedding: Optional[list[float]] = None
    importance: float = 0.5  # 重要性 0-1
    created_at: datetime = None
    accessed_at: datetime = None
    access_count: int = 0
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.accessed_at is None:
            self.accessed_at = datetime.now()

class MemorySystem:
    """Edict 记忆系统"""
    
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_url = redis_url
        # TODO: 初始化 Redis 连接
        # TODO: 初始化向量数据库 (Chroma / Qdrant / Milvus)
        
    async def store(self, memory: Memory) -> str:
        """存储记忆"""
        # 1. 根据类型选择存储
        if memory.memory_type == MemoryType.WORKING:
            # 存入 Redis，TTL = 1小时
            key = f"memory:working:{memory.agent_id}:{memory.id}"
            # await self.redis.set(key, json.dumps(memory.__dict__), ex=3600)
            
        elif memory.memory_type == MemoryType.SHORT_TERM:
            # 存入 Redis，TTL = 24小时
            key = f"memory:short_term:{memory.id}"
            # await self.redis.set(key, json.dumps(memory.__dict__), ex=86400)
            
        elif memory.memory_type == MemoryType.LONG_TERM:
            # 存入向量数据库
            # await self.vector_db.add(...)
            pass
            
        return memory.id
    
    async def retrieve(
        self,
        agent_id: str,
        query: str,
        limit: int = 5
    ) -> list[Memory]:
        """检索记忆 - 语义检索 + 重要性排序"""
        results = []
        
        # 1. 检索长期记忆 (向量相似度)
        # embeddings = await self.get_embeddings(query)
        # long_term_results = await self.vector_db.search(embeddings, top_k=limit)
        
        # 2. 检索短期记忆 (关键词)
        # short_term_results = await self.redis.keys(f"memory:short_term:*")
        
        # 3. 检索工作记忆
        # working_results = await self.redis.keys(f"memory:working:{agent_id}:*")
        
        # 4. 合并排序
        # results = self.rank_results([...], query)
        
        return results
    
    async def compress_context(self, agent_id: str, max_tokens: int = 4000) -> str:
        """压缩上下文 - 将记忆摘要注入 Context"""
        # 1. 获取相关记忆
        memories = await self.retrieve(agent_id, "", limit=10)
        
        # 2. 按重要性排序
        memories.sort(key=lambda m: m.importance, reverse=True)
        
        # 3. 摘要并拼接
        summary = self.summarize(memories, max_tokens)
        
        return summary
    
    def summarize(self, memories: list[Memory], max_tokens: int) -> str:
        """将记忆摘要为 Context 注入"""
        # TODO: 使用 LLM 摘要
        pass
    
    async def cleanup(self):
        """清理过期记忆"""
        # 1. 将短期记忆转移到长期记忆
        # 2. 删除低重要性记忆
        # 3. 压缩向量索引
        pass
```

### 3.3 与 mem0/Graphiti 对比

| 特性 | Edict 记忆 | mem0 | Graphiti |
|------|-----------|------|----------|
| 存储方式 | PostgreSQL + Redis + 向量 | 向量 + 图 | 时序图谱 |
| 多级记忆 | ✅ 工作/短期/长期 | 基础 | 基础 |
| 任务关联 | ✅ 任务级记忆 | ❌ | ❌ |
| 经验复用 | ✅ 模式学习 | 需企业版 | 需企业版 |
| 部署复杂度 | 中 | 高 | 高 |

---

## 四、Agent SOUL 配置优化

### 4.1 通信增强 SOUL 模板

```markdown
# {Agent} · {角色}

你是 {Agent}，负责 {职责}。

## 核心职责
1. {职责1}
2. {职责2}
3. {职责3}

---

## 🚨 通信规则（新增）

### 调用其他 Agent
```bash
# 使用通信代理，确保重试
python3 scripts/agent_call.py --agent {target_agent} --message "{message}"
```

### 错误处理
- 超时 {timeout}s 后自动重试（最多 3 次）
- 重试失败后切换备用 Agent
- 失败自动告警到飞书

### 状态检查
- 每 30 秒检查一次任务状态
- 超时自动标记并告警

### 记忆使用
- 启动时检索相关经验
- 完成后存储经验到记忆系统
```

### 4.2 建议的 Skills 列表

| Agent | 必备 Skill | 功能 |
|-------|-----------|------|
| 太子 | task-classifier | 消息分类 |
| 中书省 | task-planner | 任务规划 |
| 门下省 | task-reviewer | 方案审核 |
| 尚书省 | task-dispatcher | 任务派发 |
| 六部 | code-executor | 代码执行 |
| 全部 | error-handler | 错误处理 |
| 全部 | memory-recall | 记忆检索 |
| 全部 | health-check | 健康检查 |

---

## 五、实施计划

### 第一阶段：Agent 通信 (1-2周)
- [ ] 实现 AgentCommunicator 类
- [ ] 集成到所有 Agent 调用
- [ ] 添加心跳检测
- [ ] 实现自动恢复

### 第二阶段：记忆系统 (2-3周)
- [ ] 设计记忆存储结构
- [ ] 实现短期记忆 (Redis)
- [ ] 实现向量检索
- [ ] 实现 Context 压缩

### 第三阶段：持续优化 (进行中)
- [ ] 监控告警
- [ ] 性能调优
- [ ] 经验模式学习
