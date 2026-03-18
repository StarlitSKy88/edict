#!/usr/bin/env python3
"""
Edict 可观测性系统
功能: Metrics统计、Tracing追踪、Health检查、日志聚合
"""
import os
import sys
import time
import json
import logging
import threading
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional, Any
from datetime import datetime, timedelta
from collections import defaultdict
from contextlib import contextmanager

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(name)s] %(message)s', datefmt='%H:%M:%S')
log = logging.getLogger('observability')

BASE = Path(__file__).parent.parent
DATA = BASE / 'data'
METRICS_DIR = DATA / 'metrics'
METRICS_DIR.mkdir(parents=True, exist_ok=True)

# ==================== 配置 ====================
class Config:
    ENABLE_METRICS = os.getenv('ENABLE_METRICS', 'true').lower() == 'true'
    ENABLE_TRACING = os.getenv('ENABLE_TRACING', 'true').lower() == 'true'
    METRICS_INTERVAL = int(os.getenv('METRICS_INTERVAL', '60'))  # 秒
    TRACE_SAMPLE_RATE = float(os.getenv('TRACE_SAMPLE_RATE', '0.1'))
    RETENTION_DAYS = int(os.getenv('METRICS_RETENTION_DAYS', '7'))

config = Config()

# ==================== Metrics ====================
@dataclass
class MetricPoint:
    """指标点"""
    name: str
    value: float
    labels: dict = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

class MetricsCollector:
    """指标收集器"""
    
    def __init__(self):
        self.metrics: dict[str, list[MetricPoint]] = defaultdict(list)
        self.counters: dict[str, float] = defaultdict(float)
        self.gauges: dict[str, float] = {}
        self.histograms: dict[str, list[float]] = defaultdict(list)
        self._lock = threading.Lock()
    
    def counter(self, name: str, value: float = 1, labels: dict = None):
        """计数器"""
        with self._lock:
            self.counters[f"{name}:{json.dumps(labels or {}, sort_keys=True)}"] += value
            
            point = MetricPoint(name=name, value=self.counters[f"{name}:{json.dumps(labels or {}, sort_keys=True)}"], labels=labels or {})
            self.metrics[name].append(point)
    
    def gauge(self, name: str, value: float, labels: dict = None):
        """仪表"""
        with self._lock:
            key = f"{name}:{json.dumps(labels or {}, sort_keys=True)}"
            self.gauges[key] = value
            
            point = MetricPoint(name=name, value=value, labels=labels or {})
            self.metrics[name].append(point)
    
    def histogram(self, name: str, value: float, labels: dict = None):
        """直方图"""
        with self._lock:
            key = f"{name}:{json.dumps(labels or {}, sort_keys=True)}"
            self.histograms[key].append(value)
            
            point = MetricPoint(name=name, value=value, labels=labels or {})
            self.metrics[name].append(point)
    
    def get_summary(self) -> dict:
        """获取指标摘要"""
        with self._lock:
            return {
                'counters': dict(self.counters),
                'gauges': dict(self.gauges),
                'histograms': {
                    k: {
                        'count': len(v),
                        'min': min(v) if v else 0,
                        'max': max(v) if v else 0,
                        'avg': sum(v) / len(v) if v else 0
                    }
                    for k, v in self.histograms.items()
                }
            }
    
    def save(self):
        """保存指标到文件"""
        summary = self.get_summary()
        file = METRICS_DIR / f"metrics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        file.write_text(json.dumps(summary, indent=2, ensure_ascii=False))
        log.info(f"指标已保存: {file}")

# ==================== Tracing ====================
@dataclass
class Span:
    """追踪跨度"""
    name: str
    trace_id: str
    span_id: str
    parent_id: Optional[str]
    start_time: float
    end_time: Optional[float] = None
    labels: dict = field(default_factory=dict)
    error: Optional[str] = None

class Tracing:
    """分布式追踪"""
    
    def __init__(self, service_name: str = "edict"):
        self.service_name = service_name
        self.spans: list[Span] = []
        self._current_span: Optional[Span] = None
        self._lock = threading.Lock()
    
    @contextmanager
    def span(self, name: str, labels: dict = None):
        """创建追踪跨度"""
        import uuid
        
        span = Span(
            name=name,
            trace_id=uuid.uuid4().hex[:16],
            span_id=uuid.uuid4().hex[:8],
            parent_id=self._current_span.span_id if self._current_span else None,
            start_time=time.time(),
            labels=labels or {}
        )
        
        old_span = self._current_span
        self._current_span = span
        
        try:
            yield span
        except Exception as e:
            span.error = str(e)
            raise
        finally:
            span.end_time = time.time()
            with self._lock:
                self.spans.append(span)
            self._current_span = old_span
    
    def get_traces(self, limit: int = 100) -> list[dict]:
        """获取追踪记录"""
        with self._lock:
            spans = self.spans[-limit:]
            return [asdict(s) for s in spans]

# ==================== Health Check ====================
class HealthCheck:
    """健康检查"""
    
    def __init__(self):
        self.checks: dict[str, Callable] = {}
    
    def register(self, name: str, check_fn: Callable):
        """注册健康检查"""
        self.checks[name] = check_fn
    
    def check_all(self) -> dict:
        """执行所有检查"""
        results = {'status': 'healthy', 'checks': {}}
        
        for name, check_fn in self.checks.items():
            try:
                result = check_fn()
                results['checks'][name] = {'status': 'ok', 'result': result}
            except Exception as e:
                results['checks'][name] = {'status': 'error', 'error': str(e)}
                results['status'] = 'unhealthy'
        
        return results

# ==================== 主类 ====================
class Observability:
    """可观测性主类"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self.metrics = MetricsCollector()
        self.tracing = Tracing()
        self.health = HealthCheck()
        
        # 注册默认健康检查
        self._register_default_checks()
        
        # 启动指标保存线程
        self._start_metrics_saver()
        
        self._initialized = True
        log.info("可观测性系统初始化完成")
    
    def _register_default_checks(self):
        """注册默认健康检查"""
        # Agent状态检查
        def check_agents():
            # TODO: 检查Agent进程状态
            return {'agents_active': 0}
        
        # 磁盘检查
        def check_disk():
            import shutil
            total, used, free = shutil.disk_usage("/")
            return {'total_gb': total // (2**30), 'used_percent': used / total * 100}
        
        # 内存检查
        def check_memory():
            import psutil
            mem = psutil.virtual_memory()
            return {'percent': mem.percent, 'available_mb': mem.available // (2**20)}
        
        self.health.register("agents", check_agents)
        self.health.register("disk", check_disk)
        self.health.register("memory", check_memory)
    
    def _start_metrics_saver(self):
        """启动指标保存线程"""
        def saver():
            while True:
                time.sleep(config.METRICS_INTERVAL)
                try:
                    self.metrics.save()
                except Exception as e:
                    log.error(f"保存指标失败: {e}")
        
        thread = threading.Thread(target=saver, daemon=True)
        thread.start()
    
    # ---- 便捷方法 ----
    def record_request(self, endpoint: str, duration_ms: float, status: int):
        """记录请求"""
        self.metrics.histogram(
            "request_duration_ms",
            duration_ms,
            labels={"endpoint": endpoint, "status": str(status)}
        )
        self.metrics.counter(
            "request_total",
            1,
            labels={"endpoint": endpoint, "status": str(status)}
        )
    
    def record_agent_call(self, agent_id: str, success: bool, duration_ms: float):
        """记录Agent调用"""
        status = "success" if success else "error"
        
        self.metrics.histogram(
            "agent_call_duration_ms",
            duration_ms,
            labels={"agent_id": agent_id, "status": status}
        )
        self.metrics.counter(
            "agent_call_total",
            1,
            labels={"agent_id": agent_id, "status": status}
        )
    
    def record_task(self, task_id: str, status: str, duration_ms: float):
        """记录任务"""
        self.metrics.histogram(
            "task_duration_ms",
            duration_ms,
            labels={"task_id": task_id, "status": status}
        )
        self.metrics.counter(
            "task_total",
            1,
            labels={"status": status}
        )

# ==================== 装饰器 ====================
def traced(name: str = None):
    """追踪装饰器"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            obs = Observability()
            span_name = name or func.__name__
            
            with obs.tracing.span(span_name, {'function': func.__name__}):
                start = time.time()
                try:
                    result = func(*args, **kwargs)
                    duration_ms = (time.time() - start) * 1000
                    
                    obs.metrics.histogram("function_duration_ms", duration_ms, labels={'function': func.__name__})
                    obs.metrics.counter("function_success", 1, labels={'function': func.__name__})
                    
                    return result
                except Exception as e:
                    duration_ms = (time.time() - start) * 1000
                    
                    obs.metrics.histogram("function_duration_ms", duration_ms, labels={'function': func.__name__})
                    obs.metrics.counter("function_error", 1, labels={'function': func.__name__, 'error': type(e).__name__})
                    
                    raise
        return wrapper
    return decorator

# ==================== CLI ====================
def main():
    import argparse
    parser = argparse.ArgumentParser(description='Edict可观测性系统')
    parser.add_argument('--metrics', action='store_true', help='查看指标')
    parser.add_argument('--traces', action='store_true', help='查看追踪')
    parser.add_argument('--health', action='store_true', help='健康检查')
    
    args = parser.parse_args()
    
    obs = Observability()
    
    if args.metrics:
        print(json.dumps(obs.metrics.get_summary(), indent=2))
    elif args.traces:
        print(json.dumps(obs.tracing.get_traces(), indent=2, ensure_ascii=False))
    elif args.health:
        result = obs.health.check_all()
        print(json.dumps(result, indent=2, ensure_ascii=False))

if __name__ == '__main__':
    main()
