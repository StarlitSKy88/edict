#!/usr/bin/env python3
"""
Edict 性能优化模块
功能: 缓存装饰器、并行处理、连接池
"""
import os
import sys
import time
import json
import threading
import hashlib
import logging
from pathlib import Path
from functools import lru_cache, wraps
from contextlib import contextmanager
from typing import Callable, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import OrderedDict
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(name)s] %(message)s', datefmt='%H:%M:%S')
log = logging.getLogger('performance')

BASE = Path(__file__).parent.parent
DATA = BASE / 'data'
CACHE_DIR = DATA / 'cache'
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# ==================== 配置 ====================
class Config:
    CACHE_TTL = int(os.getenv('CACHE_TTL', '3600'))  # 缓存1小时
    CACHE_MAX_SIZE = int(os.getenv('CACHE_MAX_SIZE', '1000'))
    PARALLEL_WORKERS = int(os.getenv('PARALLEL_WORKERS', '4'))
    ENABLE_CACHE = os.getenv('ENABLE_CACHE', 'true').lower() == 'true'

config = Config()

# ==================== 缓存实现 ====================
class TTLCache:
    """TTL缓存"""
    
    def __init__(self, ttl: int = 3600, maxsize: int = 1000):
        self.cache: OrderedDict = OrderedDict()
        self.expiry: dict[str, float] = {}
        self.ttl = ttl
        self.maxsize = maxsize
        self._lock = threading.RLock()
        self._hits = 0
        self._misses = 0
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        with self._lock:
            if key not in self.cache:
                self._misses += 1
                return None
            
            # 检查过期
            if time.time() > self.expiry.get(key, 0):
                del self.cache[key]
                del self.expiry[key]
                self._misses += 1
                return None
            
            # 移到末尾(LRU)
            self.cache.move_to_end(key)
            self._hits += 1
            return self.cache[key]
    
    def set(self, key: str, value: Any):
        """设置缓存"""
        with self._lock:
            # 检查容量
            if key not in self.cache and len(self.cache) >= self.maxsize:
                # 删除最老的
                oldest = next(iter(self.cache))
                del self.cache[oldest]
                self.expiry.pop(oldest, None)
            
            self.cache[key] = value
            self.expiry[key] = time.time() + self.ttl
    
    def delete(self, key: str):
        """删除缓存"""
        with self._lock:
            self.cache.pop(key, None)
            self.expiry.pop(key, None)
    
    def clear(self):
        """清空缓存"""
        with self._lock:
            self.cache.clear()
            self.expiry.clear()
            self._hits = 0
            self._misses = 0
    
    def get_stats(self) -> dict:
        """获取统计"""
        total = self._hits + self._misses
        hit_rate = self._hits / total if total > 0 else 0
        return {
            'size': len(self.cache),
            'hits': self._hits,
            'misses': self._misses,
            'hit_rate': f"{hit_rate:.2%}"
        }

# ==================== 缓存装饰器 ====================
def cached(ttl: int = None, key_func: Callable = None):
    """缓存装饰器"""
    _ttl = ttl or config.CACHE_TTL
    
    def decorator(func: Callable) -> Callable:
        cache = TTLCache(ttl=_ttl, maxsize=config.CACHE_MAX_SIZE)
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not config.ENABLE_CACHE:
                return func(*args, **kwargs)
            
            # 生成key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                key_parts = [func.__name__, str(args), str(sorted(kwargs.items()))]
                cache_key = hashlib.md5('|'.join(key_parts).encode()).hexdigest()
            
            # 检查缓存
            result = cache.get(cache_key)
            if result is not None:
                log.debug(f"缓存命中: {func.__name__}")
                return result
            
            # 执行函数
            result = func(*args, **kwargs)
            cache.set(cache_key, result)
            log.debug(f"缓存存储: {func.__name__}")
            
            return result
        
        # 暴露缓存方法
        wrapper.cache = cache
        wrapper.clear_cache = cache.clear
        return wrapper
    
    return decorator

# ==================== 并行处理 ====================
class ParallelExecutor:
    """并行执行器"""
    
    def __init__(self, max_workers: int = None):
        self.max_workers = max_workers or config.PARALLEL_WORKERS
        self.executor = ThreadPoolExecutor(max_workers=self.max_workers)
    
    def map(self, func: Callable, items: list, timeout: int = None) -> list:
        """并行映射"""
        futures = {self.executor.submit(func, item): item for item in items}
        results = []
        
        for future in as_completed(futures, timeout=timeout):
            try:
                results.append(future.result())
            except Exception as e:
                log.error(f"并行执行失败: {e}")
                results.append(None)
        
        return results
    
    def submit(self, func: Callable, *args, **kwargs):
        """提交任务"""
        return self.executor.submit(func, *args, **kwargs)
    
    def shutdown(self, wait: bool = True):
        """关闭执行器"""
        self.executor.shutdown(wait=wait)

# ==================== 批量处理 ====================
class BatchProcessor:
    """批量处理器"""
    
    def __init__(self, batch_size: int = 10, delay: float = 0.1):
        self.batch_size = batch_size
        self.delay = delay
        self.queue: list = []
        self.lock = threading.Lock()
    
    def add(self, item: Any) -> Optional[list]:
        """添加项目，返回批次"""
        with self.lock:
            self.queue.append(item)
            
            if len(self.queue) >= self.batch_size:
                batch = self.queue[:self.batch_size]
                self.queue = self.queue[self.batch_size:]
                return batch
        
        return None
    
    def flush(self) -> list:
        """刷新队列"""
        with self.lock:
            batch = self.queue
            self.queue = []
            return batch

# ==================== 连接池 ====================
class ConnectionPool:
    """连接池"""
    
    def __init__(self, factory: Callable, min_size: int = 2, max_size: int = 10):
        self.factory = factory
        self.min_size = min_size
        self.max_size = max_size
        self.pool: list = []
        self.active: int = 0
        self.lock = threading.Lock()
        
        # 初始化最小连接
        for _ in range(min_size):
            self.pool.append(factory())
    
    def get(self) -> Any:
        """获取连接"""
        with self.lock:
            if self.pool:
                conn = self.pool.pop()
            elif self.active < self.max_size:
                conn = self.factory()
            else:
                # 等待
                time.sleep(0.1)
                return self.get()
            
            self.active += 1
            return conn
    
    def put(self, conn: Any):
        """归还连接"""
        with self.lock:
            if len(self.pool) < self.max_size:
                self.pool.append(conn)
            self.active -= 1
    
    def close(self):
        """关闭所有连接"""
        with self.lock:
            for conn in self.pool:
                try:
                    if hasattr(conn, 'close'):
                        conn.close()
                except:
                    pass
            self.pool.clear()

# ==================== 性能监控 ====================
class PerformanceMonitor:
    """性能监控"""
    
    def __init__(self):
        self.timings: dict[str, list[float]] = {}
        self._lock = threading.Lock()
    
    def record(self, name: str, duration_ms: float):
        """记录执行时间"""
        with self._lock:
            if name not in self.timings:
                self.timings[name] = []
            self.timings[name].append(duration_ms)
            
            # 只保留最近1000条
            if len(self.timings[name]) > 1000:
                self.timings[name] = self.timings[name][-1000:]
    
    def get_stats(self, name: str = None) -> dict:
        """获取统计"""
        with self._lock:
            if name:
                timings = self.timings.get(name, [])
                if not timings:
                    return {}
                return {
                    'count': len(timings),
                    'min_ms': min(timings),
                    'max_ms': max(timings),
                    'avg_ms': sum(timings) / len(timings)
                }
            
            return {
                k: self.get_stats(k)
                for k in self.timings.keys()
            }

# ==================== 上下文管理器 ====================
@contextmanager
def timer(name: str = "operation", monitor: PerformanceMonitor = None):
    """计时上下文管理器"""
    start = time.time()
    try:
        yield
    finally:
        duration_ms = (time.time() - start) * 1000
        if monitor:
            monitor.record(name, duration_ms)
        log.debug(f"{name}: {duration_ms:.2f}ms")

# ==================== CLI ====================
def main():
    import argparse
    parser = argparse.ArgumentParser(description='Edict性能优化')
    parser.add_argument('--stats', action='store_true', help='查看缓存统计')
    parser.add_argument('--test', action='store_true', help='测试缓存')
    
    args = parser.parse_args()
    
    if args.test:
        @cached(ttl=60)
        def test_func(x):
            time.sleep(0.1)  # 模拟耗时
            return x * 2
        
        # 第一次
        start = time.time()
        result = test_func(5)
        print(f"首次: {time.time() - start:.3f}s, 结果: {result}")
        
        # 第二次(缓存)
        start = time.time()
        result = test_func(5)
        print(f"缓存: {time.time() - start:.3f}s, 结果: {result}")
        
        print(f"缓存统计: {test_func.cache.get_stats()}")
    
    elif args.stats:
        print("查看缓存统计")

if __name__ == '__main__':
    main()
