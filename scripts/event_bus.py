#!/usr/bin/env python3
"""
事件总线 - 发布/订阅模式
解耦Agent间通信，支持异步事件处理
"""
import os
import sys
import json
import time
import logging
import threading
from typing import Dict, List, Callable, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import uuid
import asyncio

BASE = Path(__file__).parent.parent
sys.path.insert(0, str(BASE / 'scripts'))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [EventBus] %(levelname)s: %(message)s',
    datefmt='%H:%M:%S'
)
log = logging.getLogger('eventbus')

# ==================== 常量 ====================
class EventPriority(Enum):
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


# ==================== 数据类 ====================
@dataclass
class Event:
    """事件"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: str = ""  # 事件类型
    source: str = ""  # 发布者
    data: Any = None  # 事件数据
    priority: EventPriority = EventPriority.NORMAL
    created_at: float = field(default_factory=time.time)
    metadata: Dict = field(default_factory=dict)


@dataclass
class Subscription:
    """订阅"""
    id: str
    event_type: str
    handler: Callable
    agent_id: str  # 订阅者
    priority: EventPriority = EventPriority.NORMAL
    active: bool = True


# ==================== 事件总线 ====================
class EventBus:
    """事件总线 - 发布/订阅"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init()
        return cls._instance
    
    def _init(self):
        """初始化"""
        self._subscriptions: Dict[str, List[Subscription]] = {}  # event_type -> subscriptions
        self._handlers: Dict[str, Callable] = {}  # handler_id -> handler
        self._event_queue: List[Event] = []
        self._lock = threading.RLock()
        
        # 事件历史
        self._history: List[Event] = []
        self._max_history = 1000
        
        # 统计
        self._stats = {
            "published": 0,
            "delivered": 0,
            "failed": 0
        }
        
        # 异步处理
        self._async_mode = False
        self._loop = None
        
        log.info("事件总线初始化完成")
    
    # ---- 订阅 ----
    def subscribe(
        self,
        event_type: str,
        handler: Callable,
        agent_id: str,
        priority: EventPriority = EventPriority.NORMAL
    ) -> str:
        """订阅事件"""
        
        sub_id = str(uuid.uuid4())
        
        subscription = Subscription(
            id=sub_id,
            event_type=event_type,
            handler=handler,
            agent_id=agent_id,
            priority=priority
        )
        
        with self._lock:
            if event_type not in self._subscriptions:
                self._subscriptions[event_type] = []
            
            self._subscriptions[event_type].append(subscription)
            self._handlers[sub_id] = handler
        
        log.info(f"订阅: {agent_id} -> {event_type}")
        return sub_id
    
    def unsubscribe(self, subscription_id: str) -> bool:
        """取消订阅"""
        with self._lock:
            for event_type, subs in self._subscriptions.items():
                for sub in subs:
                    if sub.id == subscription_id:
                        sub.active = False
                        if subscription_id in self._handlers:
                            del self._handlers[subscription_id]
                        log.info(f"取消订阅: {subscription_id}")
                        return True
        return False
    
    def unsubscribe_agent(self, agent_id: str) -> int:
        """取消某Agent的所有订阅"""
        count = 0
        with self._lock:
            for event_type, subs in self._subscriptions.items():
                for sub in subs:
                    if sub.agent_id == agent_id and sub.active:
                        sub.active = False
                        count += 1
                        if sub.id in self._handlers:
                            del self._handlers[sub.id]
        
        log.info(f"取消{agent_id}的所有订阅: {count}个")
        return count
    
    # ---- 发布 ----
    def publish(self, event: Event) -> bool:
        """发布事件"""
        
        with self._lock:
            self._stats["published"] += 1
            
            # 添加到历史
            self._history.append(event)
            if len(self._history) > self._max_history:
                self._history = self._history[-self._max_history:]
        
        # 查找订阅者
        with self._lock:
            subs = self._subscriptions.get(event.type, [])
            active_subs = [s for s in subs if s.active]
        
        if not active_subs:
            log.debug(f"无订阅者: {event.type}")
            return False
        
        # 按优先级排序
        active_subs.sort(key=lambda s: s.priority.value, reverse=True)
        
        # 同步分发
        for sub in active_subs:
            try:
                if self._async_mode and asyncio.iscoroutinefunction(sub.handler):
                    # 异步处理
                    asyncio.run_coroutine_threadsafe(
                        sub.handler(event),
                        self._loop or asyncio.get_event_loop()
                    )
                else:
                    # 同步处理
                    sub.handler(event)
                
                self._stats["delivered"] += 1
                
            except Exception as e:
                self._stats["failed"] += 1
                log.error(f"事件处理失败: {sub.agent_id}, {e}")
        
        return True
    
    def publish_async(self, event_type: str, source: str, data: Any = None, **kwargs):
        """便捷异步发布"""
        event = Event(
            type=event_type,
            source=source,
            data=data,
            metadata=kwargs
        )
        return self.publish(event)
    
    # ---- 批量操作 ----
    def publish_batch(self, events: List[Event]) -> int:
        """批量发布"""
        count = 0
        for event in events:
            if self.publish(event):
                count += 1
        return count
    
    # ---- 查询 ----
    def get_subscriptions(self, event_type: str = None) -> List[dict]:
        """获取订阅列表"""
        with self._lock:
            if event_type:
                subs = self._subscriptions.get(event_type, [])
                return [
                    {
                        "id": s.id,
                        "event_type": s.event_type,
                        "agent_id": s.agent_id,
                        "priority": s.priority.name,
                        "active": s.active
                    }
                    for s in subs
                ]
            
            result = []
            for et, subs in self._subscriptions.items():
                for s in subs:
                    result.append({
                        "id": s.id,
                        "event_type": et,
                        "agent_id": s.agent_id,
                        "priority": s.priority.name,
                        "active": s.active
                    })
            return result
    
    def get_history(self, event_type: str = None, limit: int = 100) -> List[dict]:
        """获取事件历史"""
        with self._lock:
            history = self._history
            
            if event_type:
                history = [e for e in history if e.type == event_type]
            
            history = history[-limit:]
            
            return [
                {
                    "id": e.id,
                    "type": e.type,
                    "source": e.source,
                    "created_at": e.created_at,
                    "priority": e.priority.name
                }
                for e in history
            ]
    
    def get_stats(self) -> dict:
        """获取统计"""
        with self._lock:
            return {
                **self._stats,
                "subscriptions": sum(len(s) for s in self._subscriptions.values()),
                "history_size": len(self._history)
            }
    
    # ---- 异步模式 ----
    def enable_async(self, loop=None):
        """启用异步模式"""
        self._async_mode = True
        self._loop = loop or asyncio.new_event_loop()
        log.info("事件总线异步模式已启用")
    
    def disable_async(self):
        """禁用异步模式"""
        self._async_mode = False
        log.info("事件总线异步模式已禁用")
    
    # ---- 清空 ----
    def clear(self):
        """清空所有订阅和历史"""
        with self._lock:
            self._subscriptions.clear()
            self._handlers.clear()
            self._history.clear()
            self._stats = {"published": 0, "delivered": 0, "failed": 0}
        log.info("事件总线已清空")


# ==================== 便捷装饰器 ====================
def on_event(event_type: str, priority: EventPriority = EventPriority.NORMAL):
    """事件订阅装饰器"""
    
    def decorator(func: Callable) -> Callable:
        # 注册到全局事件总线
        bus = EventBus()
        bus.subscribe(event_type, func, func.__name__, priority)
        return func
    
    return decorator


# ==================== CLI ====================
def main():
    import argparse
    parser = argparse.ArgumentParser(description='事件总线')
    parser.add_argument('--publish', nargs=3, metavar=("TYPE", "SOURCE", "DATA"), help='发布事件')
    parser.add_argument('--subscribe', nargs=2, metavar=("TYPE", "AGENT"), help='订阅事件')
    parser.add_argument('--list', action='store_true', help='列出订阅')
    parser.add_argument('--history', action='store_true', help='查看历史')
    parser.add_argument('--stats', action='store_true', help='查看统计')
    parser.add_argument('--clear', action='store_true', help='清空')
    
    args = parser.parse_args()
    
    bus = EventBus()
    
    if args.publish:
        bus.publish(Event(
            type=args.publish[0],
            source=args.publish[1],
            data=args.publish[2]
        ))
        print(f"事件已发布: {args.publish[0]}")
    
    elif args.subscribe:
        def handler(event):
            print(f"收到事件: {event.type}")
        
        bus.subscribe(args.subscribe[0], handler, args.subscribe[1])
        print(f"已订阅: {args.subscribe[1]} -> {args.subscribe[0]}")
    
    elif args.list:
        for sub in bus.get_subscriptions():
            print(f"{sub['event_type']:20} | {sub['agent_id']:15} | {sub['priority']}")
    
    elif args.history:
        for e in bus.get_history(limit=10):
            print(f"{e['type']:20} | {e['source']:15} | {e['created_at']}")
    
    elif args.stats:
        import json
        print(json.dumps(bus.get_stats(), indent=2))
    
    elif args.clear:
        bus.clear()
        print("已清空")


if __name__ == '__main__':
    main()
