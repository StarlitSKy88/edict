#!/usr/bin/env python3
"""
OPC 税务计算器
小微企业常用税种计算
"""
from typing import Dict, Optional
from dataclasses import dataclass


@dataclass
class TaxResult:
    """计算结果"""
    tax_type: str
    tax_amount: float
    breakdown: Dict[str, float]
    tips: str


class TaxCalculator:
    """税务计算器"""
    
    # 小规模纳税人税率
    SMALL_SCALE_RATES = {
        "3%": 0.03,      # 3%征收率
        "5%": 0.05,      # 5%征收率
    }
    
    # 小微企业所得税税率
    MICRO_ENTERPRISE_RATES = {
        (0, 100): 0.05,    # 100万以下，5%
        (100, 300): 0.10,  # 100-300万，10%
        (300, float('inf')): 0.20,  # 300万以上，20%
    }
    
    def calc_vat(self, revenue: float, rate: str = "3%", 
                 input_vat: float = 0) -> TaxResult:
        """计算增值税
        
        小规模纳税人：应纳税额 = 销售额 × 征收率
        一般纳税人：应纳税额 = 销项税额 - 进项税额
        """
        vat_rate = self.SMALL_SCALE_RATES.get(rate, 0.03)
        
        # 应纳税额
        tax = revenue * vat_rate - input_vat
        tax = max(0, tax)  # 不能为负
        
        # 免税额度
        tax_free = 100000  # 10万/月
        
        tips = ""
        if revenue <= tax_free:
            tax = 0
            tips = "✅ 月销售额10万元以下，免征增值税"
        elif revenue <= tax_free * 3:
            tips = f"💡 全年120万元以下，免征增值税"
        
        return TaxResult(
            tax_type="增值税",
            tax_amount=round(tax, 2),
            breakdown={
                "销售额": revenue,
                "征收率": vat_rate,
                "应纳税额": round(tax, 2)
            },
            tips=tips
        )
    
    def calc_income_tax(self, profit: float) -> TaxResult:
        """计算企业所得税
        
        小型微利企业：
        - 应纳税所得额≤100万：5%
        - 100万<应纳税所得额≤300万：10%
        - 应纳税所得额>300万：20%
        """
        # 确定税率
        rate = 0.20  # 默认20%
        for (min_val, max_val), r in self.MICRO_ENTERPRISE_RATES.items():
            if min_val < profit <= max_val:
                rate = r
                break
        
        tax = profit * rate
        
        tips = ""
        if profit <= 1000000:
            tips = "✅ 符合小型微利企业条件，实际税负5%"
        elif profit <= 3000000:
            tips = "✅ 符合小型微利企业条件，实际税负10%"
        
        return TaxResult(
            tax_type="企业所得税",
            tax_amount=round(tax, 2),
            breakdown={
                "应纳税所得额": profit,
                "适用税率": rate,
                "应纳税额": round(tax, 2),
                "实际税负率": round(tax/profit*100, 2) if profit > 0 else 0
            },
            tips=tips
        )
    
    def calc_individual_income_tax(self, income: float) -> TaxResult:
        """计算个人所得税（经营所得）"""
        # 经营所得个人所得税税率表（5%-35%）
        rates = [
            (30000, 0.05, 0),
            (90000, 0.10, 1500),
            (300000, 0.20, 10500),
            (500000, 0.30, 40500),
            (float('inf'), 0.35, 65500),
        ]
        
        rate = 0.35
        deduction = 65500
        
        for threshold, r, d in rates:
            if income <= threshold:
                rate = r
                deduction = d
                break
        
        tax = income * rate - deduction
        tax = max(0, tax)
        
        return TaxResult(
            tax_type="个人所得税",
            tax_amount=round(tax, 2),
            breakdown={
                "经营所得": income,
                "适用税率": rate,
                "速算扣除数": deduction,
                "应纳税额": round(tax, 2)
            },
            tips="💡 每年6月30日前需完成经营所得汇算清缴"
        )
    
    def calc_social_insurance(self, salary: float, employee_count: int = 1) -> TaxResult:
        """计算社保（以北京为例）"""
        # 社保缴费比例
        rates = {
            "养老": {"company": 0.16, "person": 0.08},
            "失业": {"company": 0.008, "person": 0.002},
            "工伤": {"company": 0.002, "person": 0},
            "医疗": {"company": 0.09, "person": 0.02},
            "生育": {"company": 0.008, "person": 0},
        }
        
        breakdown = {}
        total_company = 0
        total_person = 0
        
        base = min(salary, 31582)  # 社保缴费基数上限
        
        for item, r in rates.items():
            company = base * r["company"] * employee_count
            person = base * r["person"] * employee_count
            breakdown[f"{item}(单位)"] = round(company, 2)
            breakdown[f"{item}(个人)"] = round(person, 2)
            total_company += company
            total_person += person
        
        total = total_company + total_person
        
        tips = f"💡 单位部分：¥{total_company:.2f}，个人部分：¥{total_person:.2f}"
        
        return TaxResult(
            tax_type="社保",
            tax_amount=round(total, 2),
            breakdown=breakdown,
            tips=tips
        )
    
    def estimate_quarterly_tax(self, quarterly_revenue: float, 
                              quarterly_cost: float) -> TaxResult:
        """预估季度税负"""
        # 增值税（季度30万以下免税）
        vat = 0
        if quarterly_revenue > 300000:
            vat = (quarterly_revenue - 300000) * 0.03
        
        # 所得税（按利润率估算）
        profit = quarterly_revenue - quarterly_cost
        income_tax = 0
        if profit > 0:
            if profit <= 250000:  # 季度
                income_tax = profit * 0.05
            elif profit <= 750000:
                income_tax = profit * 0.10
            else:
                income_tax = profit * 0.20
        
        total = vat + income_tax
        
        tips = "📌 预估仅供参考，实际以申报为准"
        
        return TaxResult(
            tax_type="季度预估税负",
            tax_amount=round(total, 2),
            breakdown={
                "增值税预估": round(vat, 2),
                "所得税预估": round(income_tax, 2)
            },
            tips=tips
        )


if __name__ == "__main__":
    calc = TaxCalculator()
    
    print("=== 增值税计算 ===")
    result = calc.calc_vat(80000)
    print(f"销售额8万：应纳税额 ¥{result.tax_amount}")
    print(result.tips)
    print()
    
    result = calc.calc_vat(150000)
    print(f"销售额15万：应纳税额 ¥{result.tax_amount}")
    print(result.tips)
    print()
    
    print("=== 企业所得税计算 ===")
    result = calc.calc_income_tax(500000)
    print(f"利润50万：应纳税额 ¥{result.tax_amount}")
    print(result.tips)
    print()
    
    print("=== 季度预估 ===")
    result = calc.estimate_quarterly_tax(400000, 250000)
    print(f"收入40万，成本25万：预估税负 ¥{result.tax_amount}")
    print(result.tips)
