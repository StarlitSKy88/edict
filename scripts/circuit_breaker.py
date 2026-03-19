#!/usr/bin/env python3
"""
熔断器 - 防止级联故障
参考Netflix Hystrix实现
"""
import os
import sys
import time
import logging
import threading
from typing import Callable, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from functools import wraps

BASE = Path(__file__).parent.parent
sys.path.insert(0, str(BASE / 'scripts'))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [Circuit] %(levelname)s: %(message)s',
    datefmt='%H:%M:%S'
)
log = logging.getLogger('circuit')

# ==================== 常量 ====================
class CircuitState(Enum):
    """熔断器状态"""
    CLOSED = "closed"      # 正常 - 关闭状态
    OPEN = "open"          # 断开 - 快速失败
    HALF_OPEN = "half_open"  # 半开 - 尝试恢复


@dataclass
class CircuitMetrics:
    """熔断器指标"""
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    rejected_calls: int = 0
    last_failure_time: float = 0
    last_success_time: float = 0
    consecutive_failures: int = 0
    consecutive_successes: int = 0


# ==================== 熔断器 ====================
class CircuitBreaker:
    """熔断器"""
    
    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,      # 连续失败次数阈值
        success_threshold: int = 3,      # 连续成功次数阈值
        timeout: float = 60.0,           # 熔断超时时间(秒)
        half_open_max_calls: int = 3,   # 半开状态最大尝试次数
        excluded_exceptions: tuple = ()
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.success_threshold = success_threshold
        self.timeout = timeout
        self.half_open_max_calls = half_open_max_calls
        self.excluded_exceptions = excluded_exceptions
        
        self._state = CircuitState.CLOSED
        self._metrics = CircuitMetrics()
        self._lock = threading.RLock()
        self._last_state_change = time.time()
        self._half_open_calls = 0
    
    @property
    def state(self) -> CircuitState:
        """获取当前状态"""
        with self._lock:
            if self._state == CircuitState.OPEN:
                # 检查是否超时
                if time.time() - self._last_state_change >= self.timeout:
                    log.info(f"熔断器 {self.name} 进入半开状态")
                    self._state = CircuitState.HALF_OPEN
                    self._half_open_calls = 0
            return self._state
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """执行函数 - 带熔断保护"""
        
        # 检查状态
        if self.state == CircuitState.OPEN:
            self._metrics.rejected_calls += 1
            raise CircuitBreakerOpenError(
                f"熔断器 {self.name} 已断开，拒绝调用"
            )
        
        # 执行调用
        start_time = time.time()
        self._metrics.total_calls += 1
        
        try:
            result = func(*args, **kwargs)
            
            # 成功
            duration = time.time() - start_time
            self._on_success(duration)
            
            return result
            
        except Exception as e:
            # 检查是否排除异常
            if isinstance(e, self.excluded_exceptions):
                raise
            
            duration = time.time() - start_time
            self._on_failure(duration, str(e))
            
            raise
    
    def _on_success(self, duration: float):
        """成功回调"""
        with self._lock:
            self._metrics.successful_calls += 1
            self._metrics.consecutive_successes += 1
            self._metrics.consecutive_failures = 0
            self._metrics.last_success_time = time.time()
            
            # 状态转换
            if self._state == CircuitState.HALF_OPEN:
                self._half_open_calls += 1
                
                if self._half_open_calls >= self.half_open_max_calls:
                    log.info(f"熔断器 {self.name} 恢复关闭")
                    self._state = CircuitState.CLOSED
                    self._metrics.consecutive_successes = 0
                    self._last_state_change = time.time()
    
    def _on_failure(self, duration: float, error: str):
        """失败回调"""
        with self._lock:
            self._metrics.failed_calls += 1
            self._metrics.consecutive_failures += 1
            self._metrics.consecutive_successes = 0
            self._metrics.last_failure_time = time.time()
            
            # 状态转换
            if self._state == CircuitState.CLOSED:
                if self._metrics.consecutive_failures >= self.failure_threshold:
                    log.warning(
                        f"熔断器 {self.name} 断开 (连续{self._metrics.consecutive_failures}次失败)"
                    )
                    self._state = CircuitState.OPEN
                    self._last_state_change = time.time()
                    
            elif self._state == CircuitState.HALF_OPEN:
                log.warning(f"熔断器 {self.name} 半开状态失败，重新断开")
                self._state = CircuitState.OPEN
                self._last_state_change = time.time()
    
    def get_metrics(self) -> dict:
        """获取指标"""
        with self._lock:
            return {
                "name": self.name,
                "state": self.state.value,
                "total_calls": self._metrics.total_calls,
                "successful_calls": self._metrics.successful_calls,
                "failed_calls": self._metrics.failed_calls,
                "rejected_calls": self._metrics.rejected_calls,
                "consecutive_failures": self._metrics.consecutive_failures,
                "failure_rate": (
                    self._metrics.failed_calls / self._metrics.total_calls
                    if self._metrics.total_calls > 0 else 0
                )
            }
    
    def reset(self):
        """手动重置"""
        with self._lock:
            self._state = CircuitState.CLOSED
            self._metrics = CircuitMetrics()
            self._last_state_change = time.time()
            log.info(f"熔断器 {self.name} 已重置")


class CircuitBreakerOpenError(Exception):
    """熔断器断开异常"""
    pass


# ==================== 熔断器管理器 ====================
class CircuitBreakerManager:
    """熔断器管理器"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._breakers = {}
            cls._instance._lock = threading.RLock()
        return cls._instance
    
    def get_breaker(
        self,
        name: str,
        failure_threshold: int = 5,
        success_threshold: int = 3,
        timeout: float = 60.0
    ) -> CircuitBreaker:
        """获取或创建熔断器"""
        with self._lock:
            if name not in self._breakers:
                self._breakers[name] = CircuitBreaker(
                    name=name,
                    failure_threshold=failure_threshold,
                    success_threshold=success_threshold,
                    timeout=timeout
                )
            return self._breakers[name]
    
    def get_all_metrics(self) -> list:
        """获取所有熔断器指标"""
        return [b.get_metrics() for b in self._breakers.values()]
    
    def reset_all(self):
        """重置所有熔断器"""
        for breaker in self._breakers.values():
            breaker.reset()


# ==================== 装饰器 ====================
def circuit_breaker(
    name: str = None,
    failure_threshold: int = 5,
    success_threshold: int = 3,
    timeout: float = 60.0
):
    """熔断器装饰器"""
    
    def decorator(func: Callable) -> Callable:
        func_name = name or func.__name__
        manager = CircuitBreakerManager()
        breaker = manager.get_breaker(
            func_name,
            failure_threshold,
            success_threshold,
            timeout
        )
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            return breaker.call(func, *args, **kwargs)
        
        return wrapper
    
    return decorator


# ==================== CLI ====================
def main():
    import argparse
    parser = argparse.ArgumentParser(description='熔断器')
    parser.add_argument('--list', action='store_true', help='列出所有熔断器')
    parser.add_argument('--reset', help='重置指定熔断器')
    parser.add_argument('--reset-all', action='store_true', help='重置所有')
    
    args = parser.parse_args()
    
    manager = CircuitBreakerManager()
    
    if args.list:
        for m in manager.get_all_metrics():
            print(f"\n{m['name']}:")
            print(f"  状态: {m['state']}")
            print(f"  总调用: {m['total_calls']}")
            print(f"  失败: {m['failed_calls']}")
            print(f"  拒绝: {m['rejected_calls']}")
            print(f"  失败率: {m['failure_rate']:.1%}")
    
    elif args.reset:
        breaker = manager.get_breaker(args.reset)
        breaker.reset()
        print(f"已重置: {args.reset}")
    
    elif args.reset_all:
        manager.reset_all()
        print("已重置所有")


if __name__ == '__main__':
    main()
