#!/usr/bin/env python3
"""
Edict 统一错误处理框架
功能: 错误分类、自动恢复、告警、降级
"""
import sys
import traceback
import logging
from pathlib import Path
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Callable, Any
from functools import wraps
import time

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(name)s] %(message)s', datefmt='%H:%M:%S')
log = logging.getLogger('error-handler')

# ==================== 错误类型 ====================
class ErrorType(Enum):
    """错误类型分类"""
    # Agent相关
    AGENT_TIMEOUT = "agent_timeout"
    AGENT_UNREACHABLE = "agent_unreachable"
    AGENT_FAILED = "agent_failed"
    
    # 任务相关
    TASK_NOT_FOUND = "task_not_found"
    TASK_FAILED = "task_failed"
    TASK_CANCELLED = "task_cancelled"
    
    # 技能相关
    SKILL_NOT_FOUND = "skill_not_found"
    SKILL_FAILED = "skill_failed"
    SKILL_TIMEOUT = "skill_timeout"
    
    # 记忆相关
    MEMORY_FULL = "memory_full"
    MEMORY_NOT_FOUND = "memory_not_found"
    VECTOR_ERROR = "vector_error"
    
    # 系统相关
    NETWORK_ERROR = "network_error"
    PERMISSION_DENIED = "permission_denied"
    CONFIG_ERROR = "config_error"
    UNKNOWN = "unknown"

class ErrorSeverity(Enum):
    """错误严重级别"""
    LOW = "low"       # 可忽略
    MEDIUM = "medium" # 需要关注
    HIGH = "high"     # 需要告警
    CRITICAL = "critical"  # 系统故障

# ==================== 数据类 ====================
@dataclass
class EdictError:
    """Edict错误"""
    error_type: ErrorType
    severity: ErrorSeverity
    message: str
    details: dict = field(default_factory=dict)
    traceback: str = ""
    timestamp: str = field(default_factory=lambda: time.strftime('%Y-%m-%d %H:%M:%S'))
    recovered: bool = False

# ==================== 错误分类器 ====================
class ErrorClassifier:
    """错误分类器"""
    
    @staticmethod
    def classify(exception: Exception, context: str = "") -> EdictError:
        """分类错误"""
        
        error_type = ErrorType.UNKNOWN
        severity = ErrorSeverity.MEDIUM
        details = {}
        
        # 解析错误类型
        error_msg = str(exception).lower()
        
        # Agent相关
        if 'timeout' in error_msg or '超时' in error_msg:
            error_type = ErrorType.AGENT_TIMEOUT
            severity = ErrorSeverity.HIGH
        elif 'unreachable' in error_msg or '无法访问' in error_msg:
            error_type = ErrorType.AGENT_UNREACHABLE
            severity = ErrorSeverity.HIGH
        elif 'task' in error_msg:
            error_type = ErrorType.TASK_FAILED
            severity = ErrorSeverity.MEDIUM
        
        # Skill相关
        elif 'skill' in error_msg:
            if 'not found' in error_msg or '不存在' in error_msg:
                error_type = ErrorType.SKILL_NOT_FOUND
            else:
                error_type = ErrorType.SKILL_FAILED
        
        # 网络相关
        elif 'network' in error_msg or '连接' in error_msg or 'connection' in error_msg:
            error_type = ErrorType.NETWORK_ERROR
            severity = ErrorSeverity.MEDIUM
        
        # 权限相关
        elif 'permission' in error_msg or '权限' in error_msg or 'denied' in error_msg:
            error_type = ErrorType.PERMISSION_DENIED
            severity = ErrorSeverity.HIGH
        
        # 上下文增强
        if context:
            details['context'] = context
        
        return EdictError(
            error_type=error_type,
            severity=severity,
            message=str(exception),
            details=details,
            traceback=traceback.format_exc()
        )

# ==================== 恢复策略 ====================
class RecoveryStrategy:
    """恢复策略"""
    
    STRATEGIES: dict[ErrorType, Callable] = {}
    
    @classmethod
    def register(cls, error_type: ErrorType):
        """注册恢复策略装饰器"""
        def decorator(func: Callable):
            cls.STRATEGIES[error_type] = func
            return func
        return decorator
    
    @classmethod
    def get_strategy(cls, error_type: ErrorType) -> Optional[Callable]:
        """获取恢复策略"""
        return cls.STRATEGIES.get(error_type)

@RecoveryStrategy.register(ErrorType.AGENT_TIMEOUT)
def recover_agent_timeout(error: EdictError) -> Any:
    """Agent超时恢复"""
    log.info("尝试恢复: Agent超时 - 等待后重试")
    time.sleep(2)
    return None  # 返回None表示需要重新调用

@RecoveryStrategy.register(ErrorType.AGENT_UNREACHABLE)
def recover_agent_unreachable(error: EdictError) -> Any:
    """Agent不可达恢复"""
    log.info("尝试恢复: Agent不可达 - 切换备用Agent")
    # 实际实现中会切换到备用Agent
    return {"fallback": True}

@RecoveryStrategy.register(ErrorType.SKILL_NOT_FOUND)
def recover_skill_not_found(error: EdictError) -> Any:
    """Skill不存在恢复"""
    log.warning("Skill不存在，可能需要安装")
    return {"action": "install_skill", "skill_name": error.details.get("skill")}

@RecoveryStrategy.register(ErrorType.NETWORK_ERROR)
def recover_network_error(error: EdictError) -> Any:
    """网络错误恢复"""
    log.info("尝试恢复: 网络错误 - 增加重试")
    time.sleep(5)
    return {"retry": True}

# ==================== 错误处理主类 ====================
class ErrorHandler:
    """统一错误处理器"""
    
    def __init__(self):
        self.error_history: list[EdictError] = []
        self.error_counts: dict[ErrorType, int] = {}
        self.max_history = 100
    
    def handle(self, exception: Exception, context: str = "", recovery_context: dict = None) -> EdictError:
        """处理错误"""
        
        # 1. 分类错误
        error = ErrorClassifier.classify(exception, context)
        error.details.update(recovery_context or {})
        
        # 2. 记录错误
        self._record_error(error)
        
        # 3. 打印错误
        self._log_error(error)
        
        # 4. 尝试恢复
        recovered = self._try_recover(error)
        error.recovered = recovered
        
        # 5. 告警
        if error.severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL]:
            self._send_alert(error)
        
        return error
    
    def _record_error(self, error: EdictError):
        """记录错误"""
        self.error_history.append(error)
        if len(self.error_history) > self.max_history:
            self.error_history = self.error_history[-self.max_history:]
        
        # 统计
        self.error_counts[error.error_type] = self.error_counts.get(error.error_type, 0) + 1
    
    def _log_error(self, error: EdictError):
        """打印错误"""
        if error.severity == ErrorSeverity.CRITICAL:
            log.critical(f"[{error.error_type.value}] {error.message}")
        elif error.severity == ErrorSeverity.HIGH:
            log.error(f"[{error.error_type.value}] {error.message}")
        elif error.severity == ErrorSeverity.MEDIUM:
            log.warning(f"[{error.error_type.value}] {error.message}")
        else:
            log.info(f"[{error.error_type.value}] {error.message}")
    
    def _try_recover(self, error: EdictError) -> bool:
        """尝试恢复"""
        strategy = RecoveryStrategy.get_strategy(error.error_type)
        
        if strategy:
            try:
                result = strategy(error)
                if result is not None:
                    error.details['recovery_result'] = result
                    return True
            except Exception as e:
                log.error(f"恢复失败: {e}")
        
        return False
    
    def _send_alert(self, error: EdictError):
        """发送告警"""
        alert_msg = f"🚨 告警: {error.error_type.value} - {error.message}"
        log.warning(alert_msg)
        
        # 发送到飞书Webhook (如果配置了)
        webhook_url = os.environ.get('FEISHU_WEBHOOK_URL')
        if webhook_url:
            try:
                import requests
                payload = {"msg_type": "text", "content": {"text": alert_msg}}
                requests.post(webhook_url, json=payload, timeout=5)
            except Exception as e:
                log.error(f"飞书Webhook发送失败: {e}")
        
        # 发送到钉钉Webhook (如果配置了)
        dingtalk_url = os.environ.get('DINGTALK_WEBHOOK_URL')
        if dingtalk_url:
            try:
                import requests
                payload = {"msgtype": "text", "text": {"content": alert_msg}}
                requests.post(dingtalk_url, json=payload, timeout=5)
            except Exception as e:
                log.error(f"钉钉Webhook发送失败: {e}")
    
    def get_stats(self) -> dict:
        """获取错误统计"""
        return {
            'total': len(self.error_history),
            'by_type': {k.value: v for k, v in self.error_counts.items()},
            'recent': [
                {'type': e.error_type.value, 'severity': e.severity.value, 'message': e.message[:50]}
                for e in self.error_history[-5:]
            ]
        }

# ==================== 装饰器 ====================
def error_handled(handler: ErrorHandler = None):
    """错误处理装饰器"""
    _handler = handler or ErrorHandler()
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error = _handler.handle(e, context=func.__name__)
                if error.recovered:
                    # 恢复成功，重试
                    return func(*args, **kwargs)
                raise
        return wrapper
    return decorator

# ==================== CLI ====================
def main():
    import argparse
    parser = argparse.ArgumentParser(description='Edict错误处理框架')
    parser.add_argument('--stats', action='store_true', help='查看错误统计')
    parser.add_argument('--test', action='store_true', help='测试错误分类')
    
    args = parser.parse_args()
    
    handler = ErrorHandler()
    
    if args.test:
        # 测试错误分类
        test_errors = [
            Exception("Agent timeout occurred"),
            Exception("Skill not found: classifier"),
            Exception("Network connection failed"),
            Exception("Permission denied")
        ]
        
        for e in test_errors:
            error = handler.handle(e, context="test")
            print(f"  {error.error_type.value} -> {error.severity.value}")
    
    elif args.stats:
        print(handler.get_stats())

if __name__ == '__main__':
    main()
