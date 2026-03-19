#!/usr/bin/env python3
"""
消息队列 - Redis支持 + 内存降级
实现异步通信，Agent间消息不阻塞
"""
import os
import sys
import json
import time
import logging
import threading
import queue
from typing import Optional, Dict, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import uuid

BASE = Path(__file__).parent.parent
sys.path.insert(0, str(BASE / 'scripts'))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [Queue] %(levelname)s: %(message)s',
    datefmt='%H:%M:%S'
)
log = logging.getLogger('queue')

# ==================== 常量 ====================
class MessagePriority(Enum):
    LOW = 0
    NORMAL = 1
    HIGH = 2
    URGENT = 3

class MessageStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    DEAD_LETTER = "dead_letter"

# ==================== 数据类 ====================
@dataclass
class Message:
    """消息"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    from_agent: str = ""
    to_agent: str = ""
    content: str = ""
    msg_type: str = "text"
    priority: MessagePriority = MessagePriority.NORMAL
    status: MessageStatus = MessageStatus.PENDING
    created_at: float = field(default_factory=time.time)
    processed_at: Optional[float] = None
    retries: int = 0
    max_retries: int = 3
    metadata: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None

@dataclass
class QueueStats:
    """队列统计"""
    total_messages: int = 0
    pending: int = 0
    processing: int = 0
    completed: int = 0
    failed: int = 0
    dead_letter: int = 0

# ==================== 消息队列 ====================
class MessageQueue:
    """消息队列 - 支持Redis + 内存降级"""
    
    def __init__(
        self,
        agent_id: str,
        redis_host: str = None,
        redis_port: int = 6379,
        redis_db: int = 0,
        use_redis: bool = True
    ):
        self.agent_id = agent_id
        
        # 队列键
        self.pending_key = f"edict:queue:{agent_id}:pending"
        self.processing_key = f"edict:queue:{agent_id}:processing"
        self.completed_key = f"edict:queue:{agent_id}:completed"
        self.dead_letter_key = f"edict:queue:{agent_id}:dlq"
        self.stats_key = f"edict:queue:{agent_id}:stats"
        
        self.use_redis = use_redis
        self.redis_client = None
        
        # 尝试连接Redis
        if use_redis:
            try:
                import redis
                self.redis_client = redis.Redis(
                    host=redis_host or os.getenv('REDIS_HOST', 'localhost'),
                    port=redis_port,
                    db=redis_db,
                    decode_responses=True
                )
                # 测试连接
                self.redis_client.ping()
                log.info(f"Redis连接成功: {agent_id}")
            except Exception as e:
                log.warning(f"Redis连接失败，使用内存队列: {e}")
                self.use_redis = False
                self.redis_client = None
        
        # 内存降级
        if not self.use_redis:
            self._memory_pending: Dict[str, Message] = {}
            self._memory_processing: Dict[str, Message] = {}
            self._memory_completed: Dict[str, Message] = {}
            self._memory_dlq: Dict[str, Message] = {}
            log.info(f"使用内存队列: {agent_id}")
    
    # ---- 推送消息 ----
    def push(self, message: Message) -> bool:
        """推送消息到队列"""
        try:
            msg_data = json.dumps({
                "id": message.id,
                "from": message.from_agent,
                "to": message.to_agent,
                "content": message.content,
                "msg_type": message.msg_type,
                "priority": message.priority.value,
                "status": message.status.value,
                "created_at": message.created_at,
                "retries": message.retries,
                "max_retries": message.max_retries,
                "metadata": message.metadata
            })
            
            if self.use_redis and self.redis_client:
                # Redis实现 - 使用有序集合，score为优先级+时间
                # 高优先级在前，同优先级时间早在前
                score = (MessagePriority.URGENT.value - message.priority.value) * 10000000 + message.created_at
                self.redis_client.zadd(self.pending_key, {msg_data: score})
                
                # 更新统计
                self._incr_stat("total_messages")
                self._incr_stat("pending")
            else:
                # 内存实现
                self._memory_pending[message.id] = message
            
            log.info(f"消息已推送: {message.id} -> {message.to_agent}")
            return True
            
        except Exception as e:
            log.error(f"推送消息失败: {e}")
            return False
    
    # ---- 取出消息 ----
    def pop(self, timeout: int = 0) -> Optional[Message]:
        """从队列取出消息 (阻塞模式)"""
        
        start_time = time.time()
        
        while True:
            if self.use_redis and self.redis_client:
                # Redis实现
                result = self.redis_client.zpopmin(self.pending_key, 1)
                
                if result:
                    _, msg_data = result[0]
                    data = json.loads(msg_data)
                    
                    message = self._deserialize_message(data)
                    message.status = MessageStatus.PROCESSING
                    
                    # 移到处理中
                    self.redis_client.zadd(
                        self.processing_key,
                        {json.dumps(data): time.time()}
                    )
                    
                    # 更新统计
                    self._decr_stat("pending")
                    self._incr_stat("processing")
                    
                    return message
            else:
                # 内存实现 - 简单FIFO
                if self._memory_pending:
                    msg_id = next(iter(self._memory_pending))
                    message = self._memory_pending.pop(msg_id)
                    message.status = MessageStatus.PROCESSING
                    self._memory_processing[message.id] = message
                    return message
            
            # 检查超时
            if timeout > 0 and (time.time() - start_time) >= timeout:
                return None
            
            # 短暂等待
            time.sleep(0.1)
    
    # ---- 完成消息 ----
    def complete(self, message: Message):
        """标记消息完成"""
        message.status = MessageStatus.COMPLETED
        message.processed_at = time.time()
        
        if self.use_redis and self.redis_client:
            # 从处理中移除
            self.redis_client.zremrangebyscore(
                self.processing_key,
                message.created_at,
                message.created_at
            )
            
            # 添加到完成
            msg_data = json.dumps({
                "id": message.id,
                "completed_at": message.processed_at
            })
            self.redis_client.zadd(self.completed_key, {msg_data: time.time()})
            
            # 清理过期的完成消息 (保留1小时)
            cutoff = time.time() - 3600
            self.redis_client.zremrangebyscore(self.completed_key, 0, cutoff)
            
            # 更新统计
            self._decr_stat("processing")
            self._incr_stat("completed")
        else:
            del self._memory_processing[message.id]
            message.completed = True
            self._memory_completed[message.id] = message
    
    # ---- 失败处理 ----
    def fail(self, message: Message, error: str = None):
        """消息处理失败"""
        message.error = error
        message.retries += 1
        
        if message.retries >= message.max_retries:
            # 超过重试次数，移到死信队列
            message.status = MessageStatus.DEAD_LETTER
            
            if self.use_redis and self.redis_client:
                self.redis_client.zremrangebyscore(
                    self.processing_key,
                    message.created_at,
                    message.created_at
                )
                
                msg_data = json.dumps({
                    "id": message.id,
                    "error": error,
                    "retries": message.retries
                })
                self.redis_client.zadd(self.dead_letter_key, {msg_data: time.time()})
                
                self._decr_stat("processing")
                self._incr_stat("dead_letter")
            else:
                del self._memory_processing[message.id]
                self._memory_dlq[message.id] = message
            
            log.warning(f"消息死信: {message.id}, 错误: {error}")
        else:
            # 重试 - 重新放回队列
            message.status = MessageStatus.PENDING
            
            if self.use_redis and self.redis_client:
                self.redis_client.zremrangebyscore(
                    self.processing_key,
                    message.created_at,
                    message.created_at
                )
                
                self.push(message)
                
                self._decr_stat("processing")
            else:
                del self._memory_processing[message.id]
                self._memory_pending[message.id] = message
            
            log.info(f"消息重试: {message.id}, 第{message.retries}次")
    
    # ---- 统计 ----
    def get_stats(self) -> QueueStats:
        """获取队列统计"""
        stats = QueueStats()
        
        if self.use_redis and self.redis_client:
            stats.total_messages = int(self.redis_client.get(f"{self.stats_key}:total") or 0)
            stats.pending = self.redis_client.zcard(self.pending_key)
            stats.processing = self.redis_client.zcard(self.processing_key)
            stats.completed = self.redis_client.zcard(self.completed_key)
            stats.dead_letter = self.redis_client.zcard(self.dead_letter_key)
        else:
            stats.total_messages = len(self._memory_completed) + len(self._memory_pending)
            stats.pending = len(self._memory_pending)
            stats.processing = len(self._memory_processing)
            stats.completed = len(self._memory_completed)
            stats.dead_letter = len(self._memory_dlq)
        
        return stats
    
    def _incr_stat(self, key: str):
        """递增统计"""
        if self.use_redis and self.redis_client:
            self.redis_client.incr(f"{self.stats_key}:{key}")
    
    def _decr_stat(self, key: str):
        """递减统计"""
        if self.use_redis and self.redis_client:
            self.redis_client.decr(f"{self.stats_key}:{key}")
    
    def _deserialize_message(self, data: dict) -> Message:
        """反序列化消息"""
        return Message(
            id=data.get("id", str(uuid.uuid4())),
            from_agent=data.get("from", ""),
            to_agent=data.get("to", ""),
            content=data.get("content", ""),
            msg_type=data.get("msg_type", "text"),
            priority=MessagePriority(data.get("priority", 1)),
            status=MessageStatus(data.get("status", "pending")),
            created_at=data.get("created_at", time.time()),
            retries=data.get("retries", 0),
            max_retries=data.get("max_retries", 3),
            metadata=data.get("metadata", {})
        )


# ==================== 消息路由器 ====================
class MessageRouter:
    """消息路由器 - 跨Agent消息分发"""
    
    def __init__(self):
        self.queues: Dict[str, MessageQueue] = {}
        self.handlers: Dict[str, Callable] = {}
        self._running = False
        self._worker_thread: Optional[threading.Thread] = None
    
    def get_queue(self, agent_id: str) -> MessageQueue:
        """获取Agent队列"""
        if agent_id not in self.queues:
            self.queues[agent_id] = MessageQueue(agent_id)
        return self.queues[agent_id]
    
    def register_handler(self, agent_id: str, handler: Callable):
        """注册消息处理器"""
        self.handlers[agent_id] = handler
        log.info(f"注册处理器: {agent_id}")
    
    def send(self, from_agent: str, to_agent: str, content: str, **kwargs) -> bool:
        """发送消息"""
        message = Message(
            from_agent=from_agent,
            to_agent=to_agent,
            content=content,
            priority=kwargs.get("priority", MessagePriority.NORMAL),
            metadata=kwargs.get("metadata", {})
        )
        
        queue = self.get_queue(to_agent)
        return queue.push(message)
    
    def broadcast(self, from_agent: str, agent_ids: list, content: str) -> int:
        """广播消息"""
        count = 0
        for agent_id in agent_ids:
            if self.send(from_agent, agent_id, content):
                count += 1
        return count
    
    def start_worker(self):
        """启动消息处理worker"""
        if self._running:
            return
        
        self._running = True
        
        def worker():
            log.info("消息处理worker已启动")
            
            while self._running:
                # 遍历所有队列
                for agent_id, queue in self.queues.items():
                    # 获取消息 (非阻塞)
                    message = queue.pop(timeout=1)
                    
                    if not message:
                        continue
                    
                    # 调用处理器
                    handler = self.handlers.get(agent_id)
                    
                    if handler:
                        try:
                            handler(message)
                            queue.complete(message)
                        except Exception as e:
                            log.error(f"处理消息失败: {e}")
                            queue.fail(message, str(e))
                    else:
                        # 无处理器，移到DLQ
                        queue.fail(message, "无处理器")
                
                time.sleep(0.1)
        
        self._worker_thread = threading.Thread(target=worker, daemon=True)
        self._worker_thread.start()
        
        log.info("消息处理worker已启动")
    
    def stop_worker(self):
        """停止worker"""
        self._running = False
        if self._worker_thread:
            self._worker_thread.join(timeout=5)
        log.info("消息处理worker已停止")


# ==================== CLI ====================
def main():
    import argparse
    parser = argparse.ArgumentParser(description='消息队列')
    parser.add_argument('--agent', required=True, help='Agent ID')
    parser.add_argument('--stats', action='store_true', help='查看统计')
    parser.add_argument('--send', nargs=3, metavar=("FROM", "TO", "CONTENT"), help='发送消息')
    
    args = parser.parse_args()
    
    queue = MessageQueue(args.agent)
    
    if args.stats:
        stats = queue.get_stats()
        print(f"队列统计:")
        print(f"  总消息: {stats.total_messages}")
        print(f"  待处理: {stats.pending}")
        print(f"  处理中: {stats.processing}")
        print(f"  已完成: {stats.completed}")
        print(f"  死信: {stats.dead_letter}")
    
    elif args.send:
        msg = Message(
            from_agent=args.send[0],
            to_agent=args.send[1],
            content=args.send[2]
        )
        queue.push(msg)
        print(f"消息已发送: {msg.id}")

if __name__ == '__main__':
    main()
