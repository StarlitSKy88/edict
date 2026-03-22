#!/usr/bin/env python3
"""
OPC 自然语言任务解析器
将用户自然语言转换为结构化任务指令
"""
import re
from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class OPCTask:
    """OPC任务结构"""
    task_type: str  # tax/contract/finance/legal
    action: str     # 申报/审核/查询/提醒
    entity: str     # 增值税/所得税/合同
    params: Dict    # 额外参数
    urgency: str    # high/medium/low


class OPCParser:
    """OPC任务解析器"""
    
    # 意图关键词映射
    INTENTS = {
        "税务": ["税", "申报", "报税", "交税", "增值税", "所得税", "个税"],
        "财务": ["账", "记账", "流水", "收入", "支出", "成本", "利润"],
        "合同": ["合同", "协议", "条款", "审核"],
        "合规": ["合规", "风险", "检查", "年报", "工商"],
        "政策": ["优惠", "政策", "补贴", "减免"],
    }
    
    # 动作映射
    ACTIONS = {
        "申报": ["申报", "报税", "缴纳"],
        "查询": ["查", "看看", "有多少", "多少"],
        "审核": ["审核", "检查", "核查", "看看有没有风险"],
        "记录": ["记录", "记账", "入账"],
        "提醒": ["提醒", "截止", "到期"],
    }
    
    def parse(self, text: str) -> OPCTask:
        """解析自然语言为OPC任务"""
        text = text.lower()
        
        # 识别意图类型
        task_type = self._identify_type(text)
        
        # 识别动作
        action = self._identify_action(text)
        
        # 识别实体
        entity = self._identify_entity(text)
        
        # 识别紧急程度
        urgency = self._identify_urgency(text)
        
        return OPCTask(
            task_type=task_type,
            action=action,
            entity=entity,
            params={},
            urgency=urgency
        )
    
    def _identify_type(self, text: str) -> str:
        """识别任务类型"""
        for intent, keywords in self.INTENTS.items():
            if any(kw in text for kw in keywords):
                return intent
        return "general"
    
    def _identify_action(self, text: str) -> str:
        """识别动作"""
        for action, keywords in self.ACTIONS.items():
            if any(kw in text for kw in keywords):
                return action
        return "query"
    
    def _identify_entity(self, text: str) -> str:
        """识别实体"""
        entities = {
            "增值税": ["增值税", "VAT"],
            "所得税": ["所得税", "企业所得税"],
            "个税": ["个税", "个人所得税"],
            "社保": ["社保", "社会保险"],
            "年报": ["年报", "工商年报"],
            "合同": ["合同"],
        }
        
        for entity, keywords in entities.items():
            if any(kw in text for kw in keywords):
                return entity
        return "general"
    
    def _identify_urgency(self, text: str) -> str:
        """识别紧急程度"""
        urgent_words = ["紧急", "马上", "立即", "今天", "截止"]
        if any(w in text for w in urgent_words):
            return "high"
        
        deadline_words = ["明天", "本月", "本季度"]
        if any(w in text for w in deadline_words):
            return "medium"
        
        return "low"
    
    def to_agent_command(self, task: OPCTask) -> str:
        """转换为Agent指令"""
        # 构建指令
        agent_map = {
            "税务": "treasury",
            "财务": "treasury", 
            "合同": "inquisition",
            "合规": "inquisition",
            "政策": "astrologer",
            "general": "zhongshu",
        }
        
        agent = agent_map.get(task.task_type, "zhongshu")
        
        return f"@{agent} {task.action}{task.entity}"


if __name__ == "__main__":
    parser = OPCParser()
    
    # 测试用例
    tests = [
        "帮我申报本月增值税",
        "看看本季度要交多少税",
        "审核一下这份合同",
        "有没有税务风险",
        "有什么优惠政策",
        "提醒我年报截止日",
    ]
    
    for test in tests:
        task = parser.parse(test)
        cmd = parser.to_agent_command(task)
        print(f"输入: {test}")
        print(f"任务: {task.task_type} - {task.action} - {task.entity}")
        print(f"指令: {cmd}")
        print("---")
