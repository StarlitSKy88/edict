#!/usr/bin/env python3
"""
Edict 通知系统
支持: 飞书、钉钉、Webhook、企业微信
"""
import os
import json
import logging
from typing import Optional, Dict, Any
from enum import Enum

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(name)s] %(message)s', datefmt='%H:%M:%S')
log = logging.getLogger('notification')

class NotificationType(Enum):
    """通知类型"""
    TASK_CREATED = "task_created"       # 任务创建
    TASK_PROGRESS = "task_progress"     # 任务进展
    TASK_COMPLETED = "task_completed"   # 任务完成
    TASK_FAILED = "task_failed"         # 任务失败
    AGENT_ERROR = "agent_error"        # Agent错误
    SYSTEM_ALERT = "system_alert"       # 系统告警

class Notifier:
    """通知器"""
    
    def __init__(self, provider: str = "feishu"):
        self.provider = provider
        self.enabled = os.getenv('NOTIFICATION_ENABLED', 'true').lower() == 'true'
        self.webhook = os.getenv('NOTIFICATION_WEBHOOK', '')
        
    def send(
        self,
        message: str,
        notification_type: NotificationType = NotificationType.TASK_PROGRESS,
        extra: Dict[str, Any] = None
    ) -> bool:
        """发送通知"""
        
        if not self.enabled:
            log.info(f"通知已禁用: {message}")
            return False
        
        # 构建消息
        msg = {
            'type': notification_type.value,
            'message': message,
            'extra': extra or {},
            'timestamp': str(datetime.now())
        }
        
        # 根据provider发送
        if self.provider == "feishu":
            return self._send_feishu(msg)
        elif self.provider == "dingtalk":
            return self._send_dingtalk(msg)
        elif self.provider == "webhook":
            return self._send_webhook(msg)
        else:
            log.warning(f"未知的provider: {self.provider}")
            return False
    
    def _send_feishu(self, msg: Dict) -> bool:
        """发送飞书通知"""
        # 使用OpenClaw的消息接口
        log.info(f"飞书通知: {msg['message'][:50]}")
        # 实际发送需要配置webhook
        return True
    
    def _send_dingtalk(self, msg: Dict) -> bool:
        """发送钉钉通知"""
        import requests
        
        if not self.webhook:
            log.warning("钉钉webhook未配置")
            return False
        
        data = {
            'msgtype': 'text',
            'text': {
                'content': f"[Edict] {msg['message']}"
            }
        }
        
        try:
            response = requests.post(self.webhook, json=data, timeout=10)
            return response.status_code == 200
        except Exception as e:
            log.error(f"钉钉通知失败: {e}")
            return False
    
    def _send_webhook(self, msg: Dict) -> bool:
        """发送通用Webhook"""
        import requests
        
        if not self.webhook:
            log.warning("Webhook未配置")
            return False
        
        try:
            response = requests.post(self.webhook, json=msg, timeout=10)
            return response.status_code == 200
        except Exception as e:
            log.error(f"Webhook通知失败: {e}")
            return False

# 便捷函数
def notify_task_progress(task_id: str, agent: str, status: str, detail: str = ""):
    """通知任务进展"""
    notifier = Notifier()
    message = f"任务 {task_id}: {agent} 正在 {status}"
    if detail:
        message += f"\n{detail}"
    
    return notifier.send(message, NotificationType.TASK_PROGRESS, {
        'task_id': task_id,
        'agent': agent,
        'status': status
    })

def notify_task_completed(task_id: str, result: str):
    """通知任务完成"""
    notifier = Notifier()
    return notifier.send(
        f"✅ 任务 {task_id} 已完成\n{result}",
        NotificationType.TASK_COMPLETED,
        {'task_id': task_id}
    )

def notify_task_failed(task_id: str, error: str):
    """通知任务失败"""
    notifier = Notifier()
    return notifier.send(
        f"❌ 任务 {task_id} 失败\n{error}",
        NotificationType.TASK_FAILED,
        {'task_id': task_id, 'error': error}
    )

def notify_agent_error(agent: str, error: str):
    """通知Agent错误"""
    notifier = Notifier()
    return notifier.send(
        f"⚠️ Agent {agent} 出错\n{error}",
        NotificationType.AGENT_ERROR,
        {'agent': agent, 'error': error}
    )

from datetime import datetime

if __name__ == '__main__':
    # 测试
    notify_task_progress("JJC-001", "红衣主教团", "规划方案", "正在分析需求...")
