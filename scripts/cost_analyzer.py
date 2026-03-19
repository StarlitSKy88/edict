#!/usr/bin/env python3
"""
成本分析 - Token消耗统计与成本计算
支持多模型计费、预算告警
"""
import os
import sys
import json
import time
import logging
import threading
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime, timedelta

BASE = Path(__file__).parent.parent
sys.path.insert(0, str(BASE / 'scripts'))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [Cost] %(levelname)s: %(message)s',
    datefmt='%H:%M:%S'
)
log = logging.getLogger('cost')

# ==================== 模型定价 ====================
MODEL_PRICING = {
    # OpenAI (USD per 1M tokens)
    "gpt-4": {"input": 30.0, "output": 60.0},
    "gpt-4-turbo": {"input": 10.0, "output": 30.0},
    "gpt-3.5-turbo": {"input": 0.5, "output": 1.5},
    
    # Anthropic
    "claude-3-opus": {"input": 15.0, "output": 75.0},
    "claude-3-sonnet": {"input": 3.0, "output": 15.0},
    "claude-3-haiku": {"input": 0.25, "output": 1.25},
    
    # Google
    "gemini-pro": {"input": 0.25, "output": 0.5},
    "gemini-pro-1.5": {"input": 1.25, "output": 5.0},
    
    # Meta
    "llama-3-70b": {"input": 0.8, "output": 0.8},
    "llama-3-8b": {"input": 0.2, "output": 0.2},
    
    # DeepSeek
    "deepseek-chat": {"input": 0.14, "output": 0.28},
    
    # Qwen
    "qwen-2-72b": {"input": 0.9, "output": 0.9},
    
    # MiniMax
    "MiniMax-M2.1": {"input": 0.1, "output": 0.1},
    
    # 免费模型
    "free": {"input": 0.0, "output": 0.0},
}


# ==================== 数据类 ====================
@dataclass
class TokenUsage:
    """Token使用记录"""
    id: str
    agent_id: str
    model: str
    input_tokens: int
    output_tokens: int
    timestamp: float = field(default_factory=time.time)
    task_id: str = ""
    metadata: Dict = field(default_factory=dict)


@dataclass
class CostReport:
    """成本报告"""
    total_cost: float
    input_cost: float
    output_cost: float
    total_tokens: int
    by_agent: Dict[str, float]
    by_model: Dict[str, float]
    period: str


# ==================== 成本分析器 ====================
class CostAnalyzer:
    """成本分析器"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init()
        return cls._instance
    
    def _init(self):
        """初始化"""
        self._usages: List[TokenUsage] = []
        self._lock = threading.RLock()
        
        # 预算设置
        self._daily_budget = float(os.getenv('DAILY_BUDGET', 100.0))  # 美元
        self._monthly_budget = float(os.getenv('MONTHLY_BUDGET', 3000.0))
        
        # 告警阈值
        self._alert_threshold = 0.8  # 80%告警
        
        # 缓存
        self._cache: Dict = {}
        self._cache_time = 0
        self._cache_ttl = 60  # 60秒
        
        log.info("成本分析器初始化完成")
    
    def _get_pricing(self, model: str) -> Dict:
        """获取模型定价"""
        # 精确匹配
        if model in MODEL_PRICING:
            return MODEL_PRICING[model]
        
        # 模糊匹配
        model_lower = model.lower()
        for key, pricing in MODEL_PRICING.items():
            if key in model_lower:
                return pricing
        
        # 默认定价
        return {"input": 1.0, "output": 2.0}
    
    # ---- 记录使用 ----
    def record_usage(
        self,
        agent_id: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        task_id: str = "",
        **metadata
    ):
        """记录Token使用"""
        
        import uuid
        
        usage = TokenUsage(
            id=str(uuid.uuid4()),
            agent_id=agent_id,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            task_id=task_id,
            metadata=metadata
        )
        
        with self._lock:
            self._usages.append(usage)
            
            # 限制内存记录数
            if len(self._usages) > 100000:
                self._usages = self._usages[-50000:]
        
        # 检查预算
        self._check_budget(agent_id)
    
    def _check_budget(self, agent_id: str):
        """检查预算"""
        
        today_cost = self.get_cost(period="today").total_cost
        
        if today_cost >= self._daily_budget * self._alert_threshold:
            log.warning(
                f"预算告警: 今日成本 ${today_cost:.2f} "
                f"已达每日预算 ${self._daily_budget:.2f} 的 {self._alert_threshold*100:.0f}%"
            )
    
    # ---- 成本计算 ----
    def calculate_cost(self, input_tokens: int, output_tokens: int, model: str) -> float:
        """计算单次调用成本"""
        
        pricing = self._get_pricing(model)
        
        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]
        
        return input_cost + output_cost
    
    def get_cost(
        self,
        agent_id: str = None,
        model: str = None,
        start_time: float = None,
        end_time: float = None,
        period: str = None
    ) -> CostReport:
        """获取成本报告"""
        
        # 解析周期
        now = time.time()
        if period:
            if period == "today":
                start_time = datetime.now().replace(hour=0, minute=0, second=0).timestamp()
            elif period == "yesterday":
                yesterday = datetime.now() - timedelta(days=1)
                start_time = yesterday.replace(hour=0, minute=0, second=0).timestamp()
                end_time = yesterday.replace(hour=23, minute=59, second=59).timestamp()
            elif period == "week":
                start_time = (datetime.now() - timedelta(days=7)).timestamp()
            elif period == "month":
                start_time = (datetime.now() - timedelta(days=30)).timestamp()
        
        # 过滤
        with self._lock:
            usages = self._usages.copy()
        
        if agent_id:
            usages = [u for u in usages if u.agent_id == agent_id]
        if model:
            usages = [u for u in usages if u.model == model]
        if start_time:
            usages = [u for u in usages if u.timestamp >= start_time]
        if end_time:
            usages = [u for u in usages if u.timestamp <= end_time]
        
        # 计算成本
        total_input = 0
        total_output = 0
        by_agent: Dict[str, float] = {}
        by_model: Dict[str, float] = {}
        
        for usage in usages:
            cost = self.calculate_cost(
                usage.input_tokens,
                usage.output_tokens,
                usage.model
            )
            
            total_input += (usage.input_tokens / 1_000_000) * self._get_pricing(usage.model)["input"]
            total_output += (usage.output_tokens / 1_000_000) * self._get_pricing(usage.model)["output"]
            
            by_agent[usage.agent_id] = by_agent.get(usage.agent_id, 0) + cost
            by_model[usage.model] = by_model.get(usage.model, 0) + cost
        
        total_cost = total_input + total_output
        
        return CostReport(
            total_cost=total_cost,
            input_cost=total_input,
            output_cost=total_output,
            total_tokens=sum(u.input_tokens + u.output_tokens for u in usages),
            by_agent=by_agent,
            by_model=by_model,
            period=period or "custom"
        )
    
    # ---- 统计 ----
    def get_stats(self) -> Dict:
        """获取统计"""
        
        with self._lock:
            total = len(self._usages)
            if total == 0:
                return {"total_requests": 0, "total_cost": 0}
            
            total_tokens = sum(
                u.input_tokens + u.output_tokens 
                for u in self._usages
            )
            
            models_used = set(u.model for u in self._usages)
            agents_used = set(u.agent_id for u in self._usages)
            
            return {
                "total_requests": total,
                "total_tokens": total_tokens,
                "models_used": list(models_used),
                "agents_used": list(agents_used),
                "today_cost": self.get_cost(period="today").total_cost,
                "daily_budget": self._daily_budget,
                "budget_usage": self.get_cost(period="today").total_cost / self._daily_budget
            }
    
    def get_agent_stats(self, agent_id: str) -> Dict:
        """获取Agent统计"""
        
        report = self.get_cost(agent_id=agent_id, period="month")
        
        return {
            "agent_id": agent_id,
            "total_cost": report.total_cost,
            "total_tokens": report.total_tokens,
            "by_model": report.by_model
        }
    
    def get_model_stats(self) -> List[Dict]:
        """获取模型使用统计"""
        
        report = self.get_cost(period="month")
        
        return [
            {
                "model": model,
                "cost": cost,
                "percentage": (cost / report.total_cost * 100) if report.total_cost > 0 else 0
            }
            for model, cost in sorted(
                report.by_model.items(), 
                key=lambda x: x[1], 
                reverse=True
            )
        ]
    
    # ---- 预算管理 ----
    def set_budget(self, daily: float = None, monthly: float = None):
        """设置预算"""
        if daily:
            self._daily_budget = daily
        if monthly:
            self._monthly_budget = monthly
        
        log.info(f"预算设置: 每日 ${daily}, 每月 ${monthly}")
    
    def check_budget(self) -> Dict:
        """检查预算状态"""
        
        today = self.get_cost(period="today")
        month = self.get_cost(period="month")
        
        return {
            "daily": {
                "used": today.total_cost,
                "budget": self._daily_budget,
                "remaining": self._daily_budget - today.total_cost,
                "percentage": today.total_cost / self._daily_budget * 100
            },
            "monthly": {
                "used": month.total_cost,
                "budget": self._monthly_budget,
                "remaining": self._monthly_budget - month.total_cost,
                "percentage": month.total_cost / self._monthly_budget * 100
            }
        }
    
    # ---- 导出 ----
    def export_report(self, period: str = "month") -> str:
        """导出报告"""
        
        report = self.get_cost(period=period)
        
        output = f"""# 成本分析报告 ({period})

## 概览

| 指标 | 数值 |
|-----|------|
| 总成本 | ${report.total_cost:.4f} |
| 输入成本 | ${report.input_cost:.4f} |
| 输出成本 | ${report.output_cost:.4f} |
| 总Token数 | {report.total_tokens:,} |

## 按Agent

| Agent | 成本 | 占比 |
|-------|------|------|
"""
        
        for agent, cost in sorted(report.by_agent.items(), key=lambda x: x[1], reverse=True):
            pct = cost / report.total_cost * 100 if report.total_cost > 0 else 0
            output += f"| {agent} | ${cost:.4f} | {pct:.1f}% |\n"
        
        output += """
## 按模型

| 模型 | 成本 | 占比 |
|-----|------|------|
"""
        
        for model, cost in sorted(report.by_model.items(), key=lambda x: x[1], reverse=True):
            pct = cost / report.total_cost * 100 if report.total_cost > 0 else 0
            output += f"| {model} | ${cost:.4f} | {pct:.1f}% |\n"
        
        return output
    
    def save_to_file(self, path: str = "logs/costs.json"):
        """保存到文件"""
        
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        
        with self._lock:
            data = [
                {
                    "id": u.id,
                    "agent_id": u.agent_id,
                    "model": u.model,
                    "input_tokens": u.input_tokens,
                    "output_tokens": u.output_tokens,
                    "timestamp": u.timestamp,
                    "task_id": u.task_id
                }
                for u in self._usages
            ]
        
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)
        
        log.info(f"成本数据已保存: {path}")


# ==================== 便捷函数 ====================
def record_tokens(agent_id: str, model: str, input_tokens: int, output_tokens: int, **kwargs):
    """记录Token使用"""
    CostAnalyzer().record_usage(agent_id, model, input_tokens, output_tokens, **kwargs)


# ==================== CLI ====================
def main():
    import argparse
    parser = argparse.ArgumentParser(description='成本分析')
    parser.add_argument('--stats', action='store_true', help='查看统计')
    parser.add_argument('--report', choices=['today', 'week', 'month'], help='成本报告')
    parser.add_argument('--agent', help='指定Agent')
    parser.add_argument('--budget', action='store_true', help='预算状态')
    parser.add_argument('--models', action='store_true', help='模型统计')
    parser.add_argument('--set-budget', nargs=2, metavar=("DAILY", "MONTHLY"), help='设置预算')
    parser.add_argument('--export', help='导出报告')
    
    args = parser.parse_args()
    
    analyzer = CostAnalyzer()
    
    if args.stats:
        import json
        print(json.dumps(analyzer.get_stats(), indent=2))
    
    elif args.report:
        report = analyzer.get_cost(period=args.report)
        print(f"总成本: ${report.total_cost:.4f}")
        print(f"输入成本: ${report.input_cost:.4f}")
        print(f"输出成本: ${report.output_cost:.4f}")
        print(f"总Token: {report.total_tokens:,}")
    
    elif args.budget:
        import json
        print(json.dumps(analyzer.check_budget(), indent=2))
    
    elif args.models:
        for m in analyzer.get_model_stats():
            print(f"{m['model']:30} ${m['cost']:8.4f} {m['percentage']:5.1f}%")
    
    elif args.set_budget:
        analyzer.set_budget(
            daily=float(args.set_budget[0]),
            monthly=float(args.set_budget[1])
        )
        print("预算已设置")
    
    elif args.export:
        content = analyzer.export_report(args.export)
        with open(args.export + ".md", 'w') as f:
            f.write(content)
        print(f"报告已导出: {args.export}.md")


if __name__ == '__main__':
    main()
