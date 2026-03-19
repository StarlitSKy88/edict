#!/usr/bin/env python3
"""
审计日志 - 记录所有操作，满足合规要求
支持多种存储后端: 文件/Elasticsearch/数据库
"""
import os
import sys
import json
import time
import logging
import threading
import traceback
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from datetime import datetime

BASE = Path(__file__).parent.parent
sys.path.insert(0, str(BASE / 'scripts'))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [Audit] %(levelname)s: %(message)s',
    datefmt='%H:%M:%S'
)
log = logging.getLogger('audit')

# ==================== 常量 ====================
class AuditLevel(Enum):
    """审计级别"""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AuditAction(Enum):
    """操作类型"""
    # Agent操作
    AGENT_CREATE = "agent.create"
    AGENT_DELETE = "agent.delete"
    AGENT_UPDATE = "agent.update"
    AGENT_START = "agent.start"
    AGENT_STOP = "agent.stop"
    
    # 消息操作
    MESSAGE_SEND = "message.send"
    MESSAGE_RECEIVE = "message.receive"
    MESSAGE_FAIL = "message.fail"
    
    # 任务操作
    TASK_CREATE = "task.create"
    TASK_START = "task.start"
    TASK_COMPLETE = "task.complete"
    TASK_FAIL = "task.fail"
    
    # 配置操作
    CONFIG_GET = "config.get"
    CONFIG_SET = "config.set"
    CONFIG_DELETE = "config.delete"
    
    # 权限操作
    PERMISSION_GRANT = "permission.grant"
    PERMISSION_REVOKE = "permission.revoke"
    
    # 系统操作
    SYSTEM_START = "system.start"
    SYSTEM_STOP = "system.stop"


# ==================== 数据类 ====================
@dataclass
class AuditLog:
    """审计日志"""
    id: str = ""  # 将在初始化时生成
    timestamp: float = field(default_factory=time.time)
    level: str = "info"
    action: str = ""
    actor: str = ""  # 操作者
    target: str = ""  # 操作目标
    resource: str = ""  # 资源类型
    result: str = "success"  # success/failure
    error: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    ip_address: str = ""
    user_agent: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


# ==================== 审计日志器 ====================
class AuditLogger:
    """审计日志器"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init()
        return cls._instance
    
    def _init(self):
        """初始化"""
        self._logs: List[AuditLog] = []
        self._lock = threading.RLock()
        
        # 配置
        self._storage = os.getenv('AUDIT_STORAGE', 'file')  # file/elasticsearch/db
        self._level = AuditLevel.INFO
        self._retention_days = int(os.getenv('AUDIT_RETENTION_DAYS', 90))
        
        # 文件存储
        self._log_dir = os.getenv('AUDIT_LOG_DIR', 'logs/audit')
        
        # 最大内存日志数
        self._max_memory_logs = 10000
        
        log.info(f"审计日志初始化完成 (存储: {self._storage})")
    
    def _generate_id(self) -> str:
        """生成日志ID"""
        import uuid
        return f"audit_{int(time.time())}_{uuid.uuid4().hex[:8]}"
    
    # ---- 记录日志 ----
    def log(
        self,
        action: str,
        actor: str,
        target: str = "",
        level: AuditLevel = AuditLevel.INFO,
        result: str = "success",
        error: str = "",
        details: Dict = None,
        resource: str = "",
        **kwargs
    ):
        """记录审计日志"""
        
        audit_log = AuditLog(
            id=self._generate_id(),
            timestamp=time.time(),
            level=level.value,
            action=action,
            actor=actor,
            target=target,
            resource=resource,
            result=result,
            error=error,
            details=details or {},
            **kwargs
        )
        
        # 存储
        with self._lock:
            self._logs.append(audit_log)
            
            # 内存限制
            if len(self._logs) > self._max_memory_logs:
                self._logs = self._logs[-self._max_memory_logs:]
        
        # 输出
        self._output(audit_log)
        
        return audit_log.id
    
    def _output(self, audit_log: AuditLog):
        """输出日志"""
        
        # 文件输出
        if self._storage == 'file':
            self._write_to_file(audit_log)
        
        # 标准输出 (开发用)
        log.info(
            f"[AUDIT] {audit_log.action} | {audit_log.actor} -> {audit_log.target} | {audit_log.result}"
        )
    
    def _write_to_file(self, audit_log: AuditLog):
        """写入文件"""
        
        os.makedirs(self._log_dir, exist_ok=True)
        
        # 按日期分文件
        date_str = datetime.fromtimestamp(audit_log.timestamp).strftime("%Y-%m-%d")
        file_path = f"{self._log_dir}/{date_str}.jsonl"
        
        try:
            with open(file_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps(asdict(audit_log), ensure_ascii=False) + '\n')
        except Exception as e:
            log.error(f"写入审计日志失败: {e}")
    
    # ---- 便捷方法 ----
    def info(self, action: str, actor: str, **kwargs):
        """信息日志"""
        return self.log(action, actor, level=AuditLevel.INFO, **kwargs)
    
    def warning(self, action: str, actor: str, **kwargs):
        """警告日志"""
        return self.log(action, actor, level=AuditLevel.WARNING, **kwargs)
    
    def error(self, action: str, actor: str, error: str = "", **kwargs):
        """错误日志"""
        return self.log(action, actor, level=AuditLevel.ERROR, result="failure", error=error, **kwargs)
    
    def critical(self, action: str, actor: str, **kwargs):
        """严重日志"""
        return self.log(action, actor, level=AuditLevel.CRITICAL, **kwargs)
    
    # ---- Agent操作 ----
    def log_agent_create(self, actor: str, agent_id: str, details: Dict = None):
        """记录创建Agent"""
        return self.log(
            AuditAction.AGENT_CREATE.value,
            actor=actor,
            target=agent_id,
            resource="agent",
            details=details or {}
        )
    
    def log_agent_delete(self, actor: str, agent_id: str):
        """记录删除Agent"""
        return self.log(
            AuditAction.AGENT_DELETE.value,
            actor=actor,
            target=agent_id,
            resource="agent"
        )
    
    def log_message(self, actor: str, target: str, result: str, details: Dict = None):
        """记录消息"""
        action = AuditAction.MESSAGE_SEND.value if result == "success" else AuditAction.MESSAGE_FAIL.value
        return self.log(
            action,
            actor=actor,
            target=target,
            result=result,
            resource="message",
            details=details or {}
        )
    
    def log_task(self, action: str, actor: str, task_id: str, result: str = "success", error: str = ""):
        """记录任务"""
        action_map = {
            "create": AuditAction.TASK_CREATE.value,
            "start": AuditAction.TASK_START.value,
            "complete": AuditAction.TASK_COMPLETE.value,
            "fail": AuditAction.TASK_FAIL.value
        }
        
        return self.log(
            action_map.get(action, action),
            actor=actor,
            target=task_id,
            result=result,
            error=error,
            resource="task"
        )
    
    def log_config(self, action: str, actor: str, key: str, old_value: Any = None, new_value: Any = None):
        """记录配置变更"""
        details = {}
        if old_value is not None:
            details["old_value"] = str(old_value)
        if new_value is not None:
            details["new_value"] = str(new_value)
        
        return self.log(
            f"config.{action}",
            actor=actor,
            target=key,
            resource="config",
            details=details
        )
    
    # ---- 查询 ----
    def query(
        self,
        action: str = None,
        actor: str = None,
        target: str = None,
        start_time: float = None,
        end_time: float = None,
        level: AuditLevel = None,
        limit: int = 100
    ) -> List[AuditLog]:
        """查询日志"""
        
        with self._lock:
            logs = self._logs.copy()
        
        # 过滤
        if action:
            logs = [l for l in logs if l.action == action]
        if actor:
            logs = [l for l in logs if l.actor == actor]
        if target:
            logs = [l for l in logs if l.target == target]
        if start_time:
            logs = [l for l in logs if l.timestamp >= start_time]
        if end_time:
            logs = [l for l in logs if l.timestamp <= end_time]
        if level:
            logs = [l for l in logs if l.level == level.value]
        
        # 排序
        logs.sort(key=lambda x: x.timestamp, reverse=True)
        
        return logs[:limit]
    
    def get_stats(self) -> Dict:
        """获取统计"""
        with self._lock:
            total = len(self._logs)
            
            by_action = {}
            by_actor = {}
            by_level = {}
            by_result = {"success": 0, "failure": 0}
            
            for log in self._logs:
                by_action[log.action] = by_action.get(log.action, 0) + 1
                by_actor[log.actor] = by_actor.get(log.actor, 0) + 1
                by_level[log.level] = by_level.get(log.level, 0) + 1
                by_result[log.result] = by_result.get(log.result, 0) + 1
            
            return {
                "total": total,
                "by_action": by_action,
                "by_actor": by_actor,
                "by_level": by_level,
                "by_result": by_result
            }
    
    # ---- 导出 ----
    def export_json(self, path: str = None, **filters) -> str:
        """导出JSON"""
        logs = self.query(**filters)
        return json.dumps([asdict(l) for l in logs], ensure_ascii=False, indent=2)
    
    def export_csv(self, path: str = None, **filters) -> str:
        """导出CSV"""
        import csv
        from io import StringIO
        
        logs = self.query(**filters)
        
        output = StringIO()
        if logs:
            fieldnames = ['id', 'timestamp', 'level', 'action', 'actor', 'target', 'result', 'error']
            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader()
            
            for log in logs:
                writer.writerow({
                    'id': log.id,
                    'timestamp': log.timestamp,
                    'level': log.level,
                    'action': log.action,
                    'actor': log.actor,
                    'target': log.target,
                    'result': log.result,
                    'error': log.error
                })
        
        return output.getvalue()


# ==================== 装饰器 ====================
def audit(action: str, resource: str = ""):
    """审计装饰器"""
    
    def decorator(func):
        
        def wrapper(*args, **kwargs):
            audit_logger = AuditLogger()
            
            # 获取actor (从kwargs或第一个参数)
            actor = kwargs.get('actor', 'system')
            
            try:
                result = func(*args, **kwargs)
                
                audit_logger.log(
                    action=action,
                    actor=actor,
                    target=str(result)[:100] if result else "",
                    result="success",
                    resource=resource
                )
                
                return result
                
            except Exception as e:
                audit_logger.error(
                    action=action,
                    actor=actor,
                    error=f"{type(e).__name__}: {str(e)}",
                    details={"traceback": traceback.format_exc()},
                    resource=resource
                )
                raise
        
        return wrapper
    
    return decorator


# ==================== CLI ====================
def main():
    import argparse
    parser = argparse.ArgumentParser(description='审计日志')
    parser.add_argument('--query', action='store_true', help='查询日志')
    parser.add_argument('--action', help='按操作过滤')
    parser.add_argument('--actor', help='按操作者过滤')
    parser.add_argument('--limit', type=int, default=10, help='返回数量')
    parser.add_argument('--stats', action='store_true', help='查看统计')
    parser.add_argument('--export', help='导出文件路径')
    
    args = parser.parse_args()
    
    logger = AuditLogger()
    
    if args.query:
        logs = logger.query(
            action=args.action,
            actor=args.actor,
            limit=args.limit
        )
        
        for log in logs:
            print(f"[{log.level}] {log.action} | {log.actor} -> {log.target} | {log.result}")
    
    elif args.stats:
        import json
        print(json.dumps(logger.get_stats(), indent=2))
    
    elif args.export:
        content = logger.export_json()
        with open(args.export, 'w') as f:
            f.write(content)
        print(f"已导出到: {args.export}")


if __name__ == '__main__':
    main()
