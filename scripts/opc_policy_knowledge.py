#!/usr/bin/env python3
"""
OPC 政策知识库
小微企业优惠政策实时更新
"""
import json
import os
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class Policy:
    """政策"""
    id: str
    title: str
    category: str  # tax/social/finance/legal
    content: str
    conditions: List[str]  # 适用条件
    benefits: str  # 优惠内容
    deadline: Optional[str]  # 截止日期
    source: str  # 来源
    updated_at: str


class PolicyKnowledgeBase:
    """OPC政策知识库"""
    
    def __init__(self, data_dir: str = None):
        self.data_dir = data_dir or "/workspace/nick-project/data"
        self.policies_file = os.path.join(self.data_dir, "opc_policies.json")
        self.policies = self._load_policies()
    
    def _load_policies(self) -> List[Policy]:
        """加载政策库"""
        if os.path.exists(self.policies_file):
            with open(self.policies_file) as f:
                data = json.load(f)
                return [Policy(**p) for p in data]
        return self._get_default_policies()
    
    def _get_default_policies(self) -> List[Policy]:
        """默认政策库"""
        return [
            Policy(
                id="tax-001",
                title="小规模纳税人增值税优惠",
                category="tax",
                content="月销售额10万元以下（含10万元）的增值税小规模纳税人，免征增值税。",
                conditions=["小规模纳税人", "月销售额≤10万元"],
                benefits="免征增值税",
                deadline="2027-12-31",
                source="国家税务总局"
            ),
            Policy(
                id="tax-002",
                title="小型微利企业所得税优惠",
                category="tax",
                content="对小型微利企业减按20%税率征收企业所得税。小型微利企业年应纳税所得额300万元以内的部分，减按25%计入应纳税所得额。",
                conditions=["小型微利企业", "年应纳税所得额≤300万元"],
                benefits="实际税负5%",
                deadline="2027-12-31",
                source="国家税务总局"
            ),
            Policy(
                id="tax-003",
                title="六税两费减半征收",
                category="tax",
                content="对增值税小规模纳税人、小型微利企业和个体工商户减按50%税额幅度内资源税、城市维护建设税、房产税、城镇土地使用税、印花税（不含证券交易印花税）、耕地占用税和教育费附加、地方教育附加。",
                conditions=["增值税小规模纳税人", "小型微利企业", "个体工商户"],
                benefits="减按50%征收",
                deadline="2027-12-31",
                source="国家税务总局"
            ),
            Policy(
                id="social-001",
                title="阶段性降低失业保险费率",
                category="social",
                content="延续实施失业保险阶段性降费率政策，用人单位费率降至0.7%，个人费率降至0.3%。",
                conditions=["所有用人单位"],
                benefits="失业保险费率降至0.7%（单位）+0.3%（个人）",
                deadline="2025-12-31",
                source="人力资源社会保障部"
            ),
            Policy(
                id="finance-001",
                title="创业担保贷款贴息",
                category="finance",
                content="符合条件的小微企业可申请创业担保贷款，贷款额度最高300万元，财政给予贴息。",
                conditions=["小微企业", "招用重点群体达到一定比例"],
                benefits="贷款额度最高300万元，财政贴息",
                deadline="2025-12-31",
                source="财政部"
            ),
            Policy(
                id="legal-001",
                title="简易注销",
                category="legal",
                content="对未发生债权债务或已将债权债务清偿完结的市场主体，可以简易注销退出。",
                conditions=["无债权债务", "已清偿完毕"],
                benefits="简易注销，20天完成",
                deadline=None,
                source="市场监管总局"
            ),
        ]
    
    def save(self):
        """保存政策库"""
        with open(self.policies_file, "w") as f:
            json.dump([asdict(p) for p in self.policies], f, ensure_ascii=False, indent=2)
    
    def search(self, query: str, category: str = None) -> List[Policy]:
        """搜索政策"""
        results = []
        query = query.lower()
        
        for p in self.policies:
            if category and p.category != category:
                continue
            
            # 简单关键词匹配
            if (query in p.title.lower() or 
                query in p.content.lower() or
                any(query in c.lower() for c in p.conditions)):
                results.append(p)
        
        return results
    
    def get_by_category(self, category: str) -> List[Policy]:
        """按类别获取政策"""
        return [p for p in self.policies if p.category == category]
    
    def get_all_categories(self) -> List[str]:
        """获取所有类别"""
        return list(set(p.category for p in self.policies))
    
    def format_policy(self, policy: Policy) -> str:
        """格式化政策输出"""
        lines = []
        lines.append(f"📌 {policy.title}")
        lines.append("")
        lines.append(f"📝 内容：{policy.content}")
        lines.append("")
        lines.append(f"✅ 适用条件：")
        for c in policy.conditions:
            lines.append(f"  • {c}")
        lines.append("")
        lines.append(f"💰 优惠内容：{policy.benefits}")
        if policy.deadline:
            lines.append(f"⏰ 截止日期：{policy.deadline}")
        lines.append(f"📎 来源：{policy.source}")
        return "\n".join(lines)
    
    def format_search_results(self, results: List[Policy]) -> str:
        """格式化搜索结果"""
        if not results:
            return "未找到相关政策，建议咨询专业人士。"
        
        lines = [f"找到 {len(results)} 条相关政策：", ""]
        
        category_names = {
            "tax": "税务",
            "social": "社保",
            "finance": "金融",
            "legal": "工商"
        }
        
        for p in results:
            cat = category_names.get(p.category, p.category)
            lines.append(f"【{cat}】{p.title}")
            lines.append(f"  💰 {p.benefits}")
            if p.deadline:
                lines.append(f"  ⏰ 截止：{p.deadline}")
            lines.append("")
        
        lines.append("详情请回复：政策编号（如：tax-001）")
        return "\n".join(lines)


if __name__ == "__main__":
    kb = PolicyKnowledgeBase()
    
    # 测试搜索
    print("=== 搜索 '增值税' ===")
    results = kb.search("增值税")
    print(kb.format_search_results(results))
    
    print("\n=== 所有税务政策 ===")
    tax_policies = kb.get_by_category("tax")
    for p in tax_policies:
        print(kb.format_policy(p))
        print("---")
