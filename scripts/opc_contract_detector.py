#!/usr/bin/env python3
"""
OPC 合同风险检测器
基于关键词和规则识别合同风险
"""
import re
from typing import List, Dict, Tuple
from dataclasses import dataclass


@dataclass
class RiskItem:
    """风险项"""
    level: str  # high/medium/low
    title: str
    description: str
    suggestion: str


class ContractRiskDetector:
    """合同风险检测器"""
    
    # 高风险关键词
    HIGH_RISK_KEYWORDS = [
        (r"无限责任", "股东无限连带责任", "需删除或修改为有限责任"),
        (r"个人连带责任", "个人承担无限责任", "建议修改为有限"),
        (r"无条件", "无条件条款", "需添加前提条件"),
        (r"不可撤销", "不可撤销条款", "建议添加例外情况"),
        (r"单方面", "单方面条款", "需双方协商"),
    ]
    
    # 中风险关键词
    MEDIUM_RISK_KEYWORDS = [
        (r"违约金[过\d]+%", "违约金过高", "建议控制在20%以内"),
        (r"保证金|押金", "保证金条款", "注意退还条件"),
        (r"独家|排他", "独家条款", "注意期限和例外"),
        (r"变更|修改", "变更条款", "注意变更条件和程序"),
        (r"终止|解除", "终止条款", "注意提前通知期"),
    ]
    
    # 低风险关键词
    LOW_RISK_KEYWORDS = [
        (r"争议解决", "争议解决条款", "建议明确仲裁或诉讼"),
        (r"适用法律", "法律适用条款", "确认适用法律"),
        (r"保密", "保密条款", "注意保密期限"),
        (r"知识产权", "知识产权条款", "明确归属"),
    ]
    
    def detect(self, text: str) -> List[RiskItem]:
        """检测合同风险"""
        risks = []
        
        # 检测高风险
        for pattern, title, suggestion in self.HIGH_RISK_KEYWORDS:
            if re.search(pattern, text, re.IGNORECASE):
                risks.append(RiskItem(
                    level="high",
                    title=title,
                    description=self._extract_context(text, pattern),
                    suggestion=suggestion
                ))
        
        # 检测中风险
        for pattern, title, suggestion in self.MEDIUM_RISK_KEYWORDS:
            if re.search(pattern, text, re.IGNORECASE):
                risks.append(RiskItem(
                    level="medium",
                    title=title,
                    description=self._extract_context(text, pattern),
                    suggestion=suggestion
                ))
        
        # 检测低风险
        for pattern, title, suggestion in self.LOW_RISK_KEYWORDS:
            if re.search(pattern, text, re.IGNORECASE):
                risks.append(RiskItem(
                    level="low",
                    title=title,
                    description=self._extract_context(text, pattern),
                    suggestion=suggestion
                ))
        
        return risks
    
    def _extract_context(self, text: str, pattern: str, context_chars: int = 50) -> str:
        """提取匹配上下文"""
        match = re.search(pattern, text, re.IGNORECASE)
        if not match:
            return ""
        
        start = max(0, match.start() - context_chars)
        end = min(len(text), match.end() + context_chars)
        return text[start:end].replace("\n", " ").strip()
    
    def generate_report(self, risks: List[RiskItem]) -> str:
        """生成风险报告"""
        if not risks:
            return "✅ 未发现明显风险条款，建议提交人工审核"
        
        high = [r for r in risks if r.level == "high"]
        medium = [r for r in risks if r.level == "medium"]
        low = [r for r in risks if r.level == "low"]
        
        report = []
        report.append("📋 合同风险检测报告")
        report.append("")
        
        if high:
            report.append(f"🔴 高风险 ({len(high)}项)")
            for r in high:
                report.append(f"  • {r.title}: {r.suggestion}")
            report.append("")
        
        if medium:
            report.append(f"🟡 中风险 ({len(medium)}项)")
            for r in medium:
                report.append(f"  • {r.title}: {r.suggestion}")
            report.append("")
        
        if low:
            report.append(f"🟢 建议关注 ({len(low)}项)")
            for r in low:
                report.append(f"  • {r.title}: {r.suggestion}")
        
        report.append("")
        report.append("⚠️ 免责声明：本检测仅供参考，不构成法律建议")
        
        return "\n".join(report)


if __name__ == "__main__":
    detector = ContractRiskDetector()
    
    # 测试
    test_contract = """
    服务合同
    
    第三条：乙方对甲方服务过程中产生的任何责任承担无限连带责任。
    第五条：甲方需支付保证金5万元，不可退还。
    第八条：合同签订后不可撤销。
    第十条：违约金为合同金额的50%。
    第十二条：争议解决由乙方所在地法院管辖。
    """
    
    risks = detector.detect(test_contract)
    report = detector.generate_report(risks)
    print(report)
