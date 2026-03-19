#!/usr/bin/env python3
"""
监控指标采集 - Prometheus格式
集成到Agent系统中
"""
import os
import sys
import time
import logging
import threading
import psutil
from typing import Dict, Optional, Any
from dataclasses import dataclass, field
from pathlib import Path
from pathlib import Path
import json

BASE = Path(__file__).parent.parent
sys.path.insert(0, str(BASE / 'scripts'))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [Monitor] %(levelname)s: %(message)s',
    datefmt='%H:%M:%S'
)
log = logging.getLogger('monitor')

# ==================== 指标定义 ====================
@dataclass
class AgentMetrics:
    """Agent指标"""
    agent_id: str
    messages_sent: int = 0
    messages_received: int = 0
    tasks_completed: int = 0
    tasks_failed: int = 0
    avg_response_time: float = 0.0
    last_active: float = field(default_factory=time.time)


class MetricsCollector:
    """指标采集器"""
    
    def __init__(self):
        self.agent_metrics: Dict[str, AgentMetrics] = {}
        self.system_metrics = {}
        self._lock = threading.RLock()
        
        # 系统指标缓存
        self._last_cpu_times = None
        self._last_io_counters = None
    
    # ---- Agent指标 ----
    def record_message_sent(self, agent_id: str):
        """记录发送消息"""
        with self._lock:
            if agent_id not in self.agent_metrics:
                self.agent_metrics[agent_id] = AgentMetrics(agent_id=agent_id)
            self.agent_metrics[agent_id].messages_sent += 1
    
    def record_message_received(self, agent_id: str):
        """记录接收消息"""
        with self._lock:
            if agent_id not in self.agent_metrics:
                self.agent_metrics[agent_id] = AgentMetrics(agent_id=agent_id)
            self.agent_metrics[agent_id].messages_received += 1
    
    def record_task_completed(self, agent_id: str, duration: float):
        """记录任务完成"""
        with self._lock:
            if agent_id not in self.agent_metrics:
                self.agent_metrics[agent_id] = AgentMetrics(agent_id=agent_id)
            
            m = self.agent_metrics[agent_id]
            m.tasks_completed += 1
            m.last_active = time.time()
            
            # 更新平均响应时间
            if m.avg_response_time == 0:
                m.avg_response_time = duration
            else:
                m.avg_response_time = (m.avg_response_time * 0.9) + (duration * 0.1)
    
    def record_task_failed(self, agent_id: str):
        """记录任务失败"""
        with self._lock:
            if agent_id not in self.agent_metrics:
                self.agent_metrics[agent_id] = AgentMetrics(agent_id=agent_id)
            self.agent_metrics[agent_id].tasks_failed += 1
            self.agent_metrics[agent_id].last_active = time.time()
    
    def get_agent_metrics(self, agent_id: str = None) -> dict:
        """获取Agent指标"""
        with self._lock:
            if agent_id:
                m = self.agent_metrics.get(agent_id)
                if m:
                    return {
                        "agent_id": m.agent_id,
                        "messages_sent": m.messages_sent,
                        "messages_received": m.messages_received,
                        "tasks_completed": m.tasks_completed,
                        "tasks_failed": m.tasks_failed,
                        "avg_response_time": round(m.avg_response_time, 2),
                        "last_active": m.last_active
                    }
                return {}
            
            return {
                k: {
                    "messages_sent": v.messages_sent,
                    "messages_received": v.messages_received,
                    "tasks_completed": v.tasks_completed,
                    "tasks_failed": v.tasks_failed,
                    "avg_response_time": round(v.avg_response_time, 2),
                    "last_active": v.last_active
                }
                for k, v in self.agent_metrics.items()
            }
    
    # ---- 系统指标 ----
    def collect_system_metrics(self) -> dict:
        """采集系统指标"""
        
        # CPU
        cpu_percent = psutil.cpu_percent(interval=0.1)
        
        # 内存
        memory = psutil.virtual_memory()
        
        # 磁盘
        disk = psutil.disk_usage('/')
        
        # 网络
        net_io = psutil.net_io_counters()
        
        self.system_metrics = {
            "timestamp": time.time(),
            "cpu": {
                "percent": cpu_percent,
                "count": psutil.cpu_count()
            },
            "memory": {
                "total": memory.total,
                "available": memory.available,
                "percent": memory.percent,
                "used": memory.used
            },
            "disk": {
                "total": disk.total,
                "used": disk.used,
                "free": disk.free,
                "percent": disk.percent
            },
            "network": {
                "bytes_sent": net_io.bytes_sent,
                "bytes_recv": net_io.bytes_recv,
                "packets_sent": net_io.packets_sent,
                "packets_recv": net_io.packets_recv
            }
        }
        
        return self.system_metrics
    
    def get_system_metrics(self) -> dict:
        """获取系统指标"""
        return self.system_metrics
    
    # ---- Prometheus格式 ----
    def export_prometheus(self) -> str:
        """导出Prometheus格式"""
        lines = []
        timestamp = int(time.time() * 1000)
        
        # Agent指标
        with self._lock:
            for agent_id, m in self.agent_metrics.items():
                safe_id = agent_id.replace("-", "_")
                lines.append(f'edict_agent_messages_sent{{agent="{safe_id}"}} {m.messages_sent} {timestamp}')
                lines.append(f'edict_agent_messages_received{{agent="{safe_id}"}} {m.messages_received} {timestamp}')
                lines.append(f'edict_agent_tasks_completed{{agent="{safe_id}"}} {m.tasks_completed} {timestamp}')
                lines.append(f'edict_agent_tasks_failed{{agent="{safe_id}"}} {m.tasks_failed} {timestamp}')
                lines.append(f'edict_agent_avg_response_time{{agent="{safe_id}"}} {m.avg_response_time} {timestamp}')
        
        # 系统指标
        if self.system_metrics:
            sysm = self.system_metrics
            lines.append(f'edict_cpu_percent {sysm["cpu"]["percent"]} {timestamp}')
            lines.append(f'edict_memory_percent {sysm["memory"]["percent"]} {timestamp}')
            lines.append(f'edict_disk_percent {sysm["disk"]["percent"]} {timestamp}')
        
        return "\n".join(lines)
    
    # ---- JSON格式 ----
    def export_json(self) -> str:
        """导出JSON格式"""
        return json.dumps({
            "timestamp": time.time(),
            "agents": self.get_agent_metrics(),
            "system": self.get_system_metrics()
        }, indent=2)


# ==================== 全局采集器 ====================
_global_collector: Optional[MetricsCollector] = None


def get_collector() -> MetricsCollector:
    """获取全局采集器"""
    global _global_collector
    if _global_collector is None:
        _global_collector = MetricsCollector()
    return _global_collector


# ==================== HTTP服务器 ====================
class MetricsServer:
    """指标HTTP服务器"""
    
    def __init__(self, port: int = 9090):
        self.port = port
        self.collector = get_collector()
        self._server = None
    
    def start(self):
        """启动服务器"""
        try:
            from http.server import HTTPServer, BaseHTTPRequestHandler
            
            class Handler(BaseHTTPRequestHandler):
                def do_GET(self):
                    if self.path == "/metrics":
                        self.send_response(200)
                        self.send_header("Content-Type", "text/plain")
                        self.end_headers()
                        output = self.server.server.collector.export_prometheus()
                        self.wfile.write(output.encode())
                    
                    elif self.path == "/metrics/json":
                        self.send_response(200)
                        self.send_header("Content-Type", "application/json")
                        self.end_headers()
                        output = self.server.server.collector.export_json()
                        self.wfile.write(output.encode())
                    
                    elif self.path == "/health":
                        self.send_response(200)
                        self.send_header("Content-Type", "text/plain")
                        self.end_headers()
                        self.wfile.write(b"OK")
                    
                    else:
                        self.send_response(404)
                        self.end_headers()
                
                def log_message(self, format, *args):
                    pass  # 禁用日志
            
            self._server = HTTPServer(("0.0.0.0", self.port), Handler)
            self._server.collector = self.collector
            
            log.info(f"指标服务器启动: http://0.0.0.0:{self.port}/metrics")
            self._server.serve_forever()
            
        except ImportError:
            log.warning("http.server 不可用，使用简单轮询")
    
    def stop(self):
        """停止服务器"""
        if self._server:
            self._server.shutdown()


# ==================== CLI ====================
def main():
    import argparse
    parser = argparse.ArgumentParser(description='监控指标')
    parser.add_argument('--agent', help='查看指定Agent指标')
    parser.add_argument('--system', action='store_true', help='查看系统指标')
    parser.add_argument('--prometheus', action='store_true', help='Prometheus格式')
    parser.add_argument('--json', action='store_true', help='JSON格式')
    parser.add_argument('--server', action='store_true', help='启动指标服务器')
    parser.add_argument('--port', type=int, default=9090, help='服务器端口')
    
    args = parser.parse_args()
    
    collector = get_collector()
    
    # 采集系统指标
    collector.collect_system_metrics()
    
    if args.server:
        server = MetricsServer(args.port)
        server.start()
    
    elif args.prometheus:
        print(collector.export_prometheus())
    
    elif args.json:
        print(collector.export_json())
    
    elif args.system:
        import json
        print(json.dumps(collector.get_system_metrics(), indent=2))
    
    elif args.agent:
        import json
        print(json.dumps(collector.get_agent_metrics(args.agent), indent=2))
    
    else:
        import json
        print(json.dumps(collector.get_agent_metrics(), indent=2))


if __name__ == '__main__':
    main()
