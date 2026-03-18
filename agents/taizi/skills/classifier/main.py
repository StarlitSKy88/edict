#!/usr/bin/env python3
"""
太子 Skill - 消息分类器
功能: 消息分类、意图识别、任务提取、紧急度判断
"""
import sys
import re
import json
from pathlib import Path
from dataclasses import dataclass
from typing import Optional
from enum import Enum

# 消息类型
class MessageType(Enum):
    CHAT = "chat"           # 闲聊
    TASK = "task"            # 任务
    QUESTION = "question"     # 问答
    CONFIRM = "confirm"       # 确认

# 紧急度
class Priority(Enum):
    URGENT = "urgent"     # 紧急
    HIGH = "high"          # 高
    NORMAL = "normal"       # 普通
    LOW = "low"             # 低

@dataclass
class ClassificationResult:
    message_type: MessageType
    intent: str
    priority: Priority
    target: str
    deliverable: str
    confidence: float

class MessageClassifier:
    """消息分类器"""
    
    # 闲聊关键词
    CHAT_KEYWORDS = [
        '你好', '在吗', '忙吗', '休息', '吃了吗', '天气', '周末', '干嘛',
        '怎么样', '如何', '?', '？', '好', '否', '嗯', '啊', '哈哈'
    ]
    
    # 任务关键词
    TASK_KEYWORDS = [
        '帮我', '做', '写', '调研', '分析', '开发', '部署', '安装',
        '创建', '生成', '制作', '完成', '执行', '处理', '解决',
        '传旨', '下旨', '旨意'
    ]
    
    # 动作词
    ACTION_WORDS = [
        '帮', '做', '写', '调研', '分析', '开发', '部署', '安装',
        '创建', '生成', '制作', '完成', '执行', '处理', '解决'
    ]
    
    # 紧急关键词
    URGENT_KEYWORDS = [
        '紧急', '马上', '立即', '尽快', '加急', ' deadline', 'deadline'
    ]
    
    def classify(self, message: str) -> ClassificationResult:
        """分类消息"""
        message = message.strip()
        
        # 1. 判断消息类型
        msg_type = self._detect_type(message)
        
        # 2. 提取意图
        intent = self._extract_intent(message, msg_type)
        
        # 3. 判断紧急度
        priority = self._detect_priority(message)
        
        # 4. 提取任务目标
        target, deliverable = self._extract_target(message)
        
        # 5. 计算置信度
        confidence = self._calculate_confidence(message, msg_type)
        
        return ClassificationResult(
            message_type=msg_type,
            intent=intent,
            priority=priority,
            target=target,
            deliverable=deliverable,
            confidence=confidence
        )
    
    def _detect_type(self, message: str) -> MessageType:
        """检测消息类型"""
        # 太短可能是闲聊
        if len(message) < 10:
            # 包含问号
            if '?' in message or '？' in message:
                return MessageType.QUESTION
            # 闲聊关键词
            if any(kw in message for kw in self.CHAT_KEYWORDS):
                return MessageType.CHAT
        
        # 有任务关键词
        if any(kw in message for kw in self.TASK_KEYWORDS):
            return MessageType.TASK
        
        # 问号结尾
        if message.endswith('?') or message.endswith('？'):
            return MessageType.QUESTION
        
        # 默认为任务(因为是工作场景)
        return MessageType.TASK
    
    def _extract_intent(self, message: str, msg_type: MessageType) -> str:
        """提取意图"""
        if msg_type == MessageType.CHAT:
            return "闲聊"
        
        if msg_type == MessageType.QUESTION:
            return "问答"
        
        # 任务意图
        for action in self.ACTION_WORDS:
            if action in message:
                return f"{action}任务"
        
        return "处理任务"
    
    def _detect_priority(self, message: str) -> Priority:
        """检测紧急度"""
        if any(kw in message.lower() for kw in self.URGENT_KEYWORDS):
            return Priority.URGENT
        
        # 包含"紧急"等词
        urgent_count = sum(1 for kw in self.URGENT_KEYWORDS if kw in message.lower())
        
        if urgent_count >= 2:
            return Priority.HIGH
        elif urgent_count == 1:
            return Priority.NORMAL
        
        return Priority.NORMAL
    
    def _extract_target(self, message: str) -> tuple[str, str]:
        """提取任务目标和交付物"""
        # 移除前缀
        msg = re.sub(r'^(传旨|下旨)[：:\s]*', '', message)
        
        # 简单提取: 取前20字作为目标
        target = msg[:20] if len(msg) > 20 else msg
        
        # 尝试识别交付物
        deliverable = ""
        deliverable_keywords = {
            '方案': '文档',
            '报告': '文档',
            '文章': '文档',
            '代码': '代码',
            '部署': '部署完成',
            '安装': '安装完成',
            '调研': '调研报告',
            '分析': '分析报告'
        }
        
        for kw, deliverable in deliverable_keywords.items():
            if kw in message:
                break
        
        return target, deliverable
    
    def _calculate_confidence(self, message: str, msg_type: MessageType) -> float:
        """计算置信度"""
        base = 0.5
        
        # 关键词匹配增加置信度
        if msg_type == MessageType.TASK:
            matches = sum(1 for kw in self.TASK_KEYWORDS if kw in message)
            base = min(0.95, 0.5 + matches * 0.1)
        
        return base
    
    def should_create_task(self, result: ClassificationResult, message: str) -> bool:
        """判断是否应该创建任务"""
        # 闲聊不创建
        if result.message_type == MessageType.CHAT:
            return False
        
        # 消息太短不创建
        if len(message.strip()) < 10:
            return False
        
        # 低置信度不创建
        if result.confidence < 0.5:
            return False
        
        return True

def main():
    import argparse
    parser = argparse.ArgumentParser(description='太子消息分类器')
    parser.add_argument('--message', '-m', required=True, help='要分类的消息')
    parser.add_argument('--json', action='store_true', help='JSON输出')
    
    args = parser.parse_args()
    
    classifier = MessageClassifier()
    result = classifier.classify(args.message)
    
    if args.json:
        print(json.dumps({
            'message_type': result.message_type.value,
            'intent': result.intent,
            'priority': result.priority.value,
            'target': result.target,
            'deliverable': result.deliverable,
            'confidence': result.confidence,
            'should_create_task': classifier.should_create_task(result, args.message)
        }, ensure_ascii=False, indent=2))
    else:
        print(f"消息类型: {result.message_type.value}")
        print(f"意图: {result.intent}")
        print(f"优先级: {result.priority.value}")
        print(f"目标: {result.target}")
        print(f"交付物: {result.deliverable}")
        print(f"置信度: {result.confidence:.2f}")
        print(f"应创建任务: {'是' if classifier.should_create_task(result, args.message) else '否'}")

if __name__ == '__main__':
    main()
