#!/usr/bin/env python3
"""
分布式锁 - 防止多实例竞争
支持Redis + 内存降级
"""
import os
import sys
import time
import logging
import threading
from typing import Optional
from dataclasses import dataclass
from pathlib import Path
from contextlib import contextmanager

BASE = Path(__file__).parent.parent
sys.path.insert(0, str(BASE / 'scripts'))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [Lock] %(levelname)s: %(message)s',
    datefmt='%H:%M:%S'
)
log = logging.getLogger('lock')

# ==================== 分布式锁 ====================
class DistributedLock:
    """分布式锁"""
    
    def __init__(
        self,
        name: str,
        redis_host: str = None,
        redis_port: int = 6379,
        redis_db: int = 0,
        timeout: int = 30,
        retry_times: int = 3,
        retry_delay: float = 0.2
    ):
        self.name = f"edict:lock:{name}"
        self.timeout = timeout
        self.retry_times = retry_times
        self.retry_delay = retry_delay
        
        self.redis_client = None
        self._local_lock = threading.RLock()
        self._locked = False
        self._lock_id = None
        
        # 尝试连接Redis
        try:
            import redis
            self.redis_client = redis.Redis(
                host=redis_host or os.getenv('REDIS_HOST', 'localhost'),
                port=redis_port,
                db=redis_db,
                decode_responses=True
            )
            self.redis_client.ping()
            self._use_redis = True
            log.info(f"Redis分布式锁: {name}")
        except Exception as e:
            log.warning(f"Redis不可用，使用本地锁: {e}")
            self._use_redis = False
    
    def acquire(self, blocking: bool = True, timeout: float = None) -> bool:
        """获取锁"""
        timeout = timeout or self.timeout
        
        # 生成唯一锁ID
        import uuid
        lock_id = str(uuid.uuid4())
        
        if self._use_redis and self.redis_client:
            return self._acquire_redis(lock_id, blocking, timeout)
        else:
            return self._acquire_local(lock_id, blocking, timeout)
    
    def _acquire_redis(self, lock_id: str, blocking: bool, timeout: float) -> bool:
        """Redis获取锁"""
        start_time = time.time()
        
        while True:
            # SET NX (只在不存在时设置)
            result = self.redis_client.set(
                self.name,
                lock_id,
                nx=True,
                ex=timeout
            )
            
            if result:
                self._lock_id = lock_id
                log.info(f"获取锁成功: {self.name}")
                return True
            
            if not blocking:
                return False
            
            # 检查超时
            if time.time() - start_time >= timeout:
                log.warning(f"获取锁超时: {self.name}")
                return False
            
            # 重试等待
            time.sleep(self.retry_delay)
    
    def _acquire_local(self, lock_id: str, blocking: bool, timeout: float) -> bool:
        """本地获取锁"""
        start_time = time.time()
        
        while True:
            if self._local_lock.acquire(blocking=False):
                self._lock_id = lock_id
                self._locked = True
                log.info(f"获取本地锁成功: {self.name}")
                return True
            
            if not blocking:
                return False
            
            if time.time() - start_time >= timeout:
                log.warning(f"获取本地锁超时: {self.name}")
                return False
            
            time.sleep(self.retry_delay)
    
    def release(self) -> bool:
        """释放锁"""
        
        if self._use_redis and self.redis_client:
            return self._release_redis()
        else:
            return self._release_local()
    
    def _release_redis(self) -> bool:
        """Redis释放锁"""
        if not self._lock_id:
            return False
        
        # Lua脚本 - 原子检查和删除
        script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("del", KEYS[1])
        else
            return 0
        end
        """
        
        try:
            result = self.redis_client.eval(script, 1, self.name, self._lock_id)
            if result:
                log.info(f"释放锁成功: {self.name}")
                self._lock_id = None
                return True
            else:
                log.warning(f"锁不存在或已被他人释放: {self.name}")
                return False
        except Exception as e:
            log.error(f"释放锁失败: {e}")
            return False
    
    def _release_local(self) -> bool:
        """本地释放锁"""
        if self._locked:
            self._local_lock.release()
            self._locked = False
            self._lock_id = None
            log.info(f"释放本地锁: {self.name}")
            return True
        return False
    
    def extend(self, additional_time: int = None) -> bool:
        """延长锁时间"""
        additional_time = additional_time or self.timeout
        
        if not self._lock_id:
            return False
        
        if self._use_redis and self.redis_client:
            try:
                # 只有锁持有者才能延长
                script = """
                if redis.call("get", KEYS[1]) == ARGV[1] then
                    return redis.call("expire", KEYS[1], ARGV[2])
                else
                    return 0
                end
                """
                result = self.redis_client.eval(
                    script, 1, self.name, self._lock_id, additional_time
                )
                return bool(result)
            except Exception as e:
                log.error(f"延长锁失败: {e}")
                return False
        else:
            # 本地锁无法延长
            return False
    
    def is_locked(self) -> bool:
        """检查是否锁定"""
        if self._use_redis and self.redis_client:
            return bool(self.redis_client.exists(self.name))
        return self._locked


# ==================== 锁管理器 ====================
class LockManager:
    """锁管理器"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._locks = {}
            cls._instance._lock = threading.RLock()
        return cls._instance
    
    def get_lock(
        self,
        name: str,
        timeout: int = 30,
        **kwargs
    ) -> DistributedLock:
        """获取锁"""
        with self._lock:
            if name not in self._locks:
                self._locks[name] = DistributedLock(name, timeout=timeout, **kwargs)
            return self._locks[name]
    
    @contextmanager
    def lock(self, name: str, timeout: int = 30, **kwargs):
        """上下文管理器"""
        lock = self.get_lock(name, timeout, **kwargs)
        
        acquired = lock.acquire()
        try:
            yield acquired
        finally:
            if acquired:
                lock.release()
    
    def release_all(self, agent_id: str = None):
        """释放所有锁 (用于清理)"""
        # 注意: 这里是简化实现
        # 实际应该记录每个agent持有的锁
        pass


# ==================== 装饰器 ====================
def distributed_lock(name: str, timeout: int = 30):
    """分布式锁装饰器"""
    
    def decorator(func):
        
        def wrapper(*args, **kwargs):
            lock = LockManager().get_lock(name, timeout)
            
            if lock.acquire():
                try:
                    return func(*args, **kwargs)
                finally:
                    lock.release()
            else:
                raise TimeoutError(f"获取锁失败: {name}")
        
        return wrapper
    
    return decorator


# ==================== CLI ====================
def main():
    import argparse
    parser = argparse.ArgumentParser(description='分布式锁')
    parser.add_argument('--acquire', help='获取锁')
    parser.add_argument('--release', help='释放锁')
    parser.add_argument('--status', help='查看锁状态')
    parser.add_argument('--timeout', type=int, default=30, help='超时时间')
    
    args = parser.parse_args()
    
    manager = LockManager()
    
    if args.acquire:
        lock = manager.get_lock(args.acquire, args.timeout)
        if lock.acquire():
            print(f"锁已获取: {args.acquire}")
            print(f"输入任意内容释放锁...", end=" ")
            input()
            lock.release()
            print("锁已释放")
        else:
            print(f"获取锁失败: {args.acquire}")
    
    elif args.release:
        lock = manager.get_lock(args.release)
        if lock.release():
            print(f"锁已释放: {args.release}")
        else:
            print(f"释放失败: {args.release}")
    
    elif args.status:
        lock = manager.get_lock(args.status)
        print(f"锁定状态: {lock.is_locked()}")


if __name__ == '__main__':
    main()
