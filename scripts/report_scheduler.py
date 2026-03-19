#!/usr/bin/env python3
"""
报告调度器 - 自动触发日报/周报/月报
基于Cron定时任务，汇总各Agent状态并生成报告
"""
import os
import sys
import json
import time
import logging
import smtplib
from pathlib import Path
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import threading

BASE = Path(__file__).parent.parent
sys.path.insert(0, str(BASE / 'scripts'))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [Report] %(levelname)s: %(message)s',
    datefmt='%H:%M:%S'
)
log = logging.getLogger('report')

# ==================== 常量 ====================
class ReportType(Enum):
    """报告类型"""
    DAILY = "daily"    # 日报
    WEEKLY = "weekly"  # 周报
    MONTHLY = "monthly" # 月报

class ReportStatus(Enum):
    """报告状态"""
    PENDING = "pending"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"

# ==================== 数据类 ====================
@dataclass
class AgentStatus:
    """Agent状态"""
    agent_id: str
    agent_name: str
    status: str  # active, idle, error
    tasks_completed: int = 0
    tasks_pending: int = 0
    messages_sent: int = 0
    messages_received: int = 0
    uptime_hours: float = 0
    last_active: Optional[str] = None

@dataclass
class Report:
    """报告"""
    id: str
    type: ReportType
    title: str
    content: str
    status: ReportStatus
    created_at: float = field(default_factory=time.time)
    generated_at: Optional[float] = None
    agent_statuses: List[AgentStatus] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

# ==================== 核心类 ====================
class ReportScheduler:
    """报告调度器"""
    
    def __init__(
        self,
        config_path: str = None,
        router=None,
        comm=None,
        feishu_webhook: str = None
    ):
        self.config_path = config_path or "config/report_config.json"
        self.router = router
        self.comm = comm
        self.feishu_webhook = feishu_webhook
        
        self.reports: Dict[str, Report] = {}
        self.schedule_config = self._load_schedule()
        
        # 回调函数
        self.status_collectors: Dict[str, callable] = {}
        
        # 默认cron配置
        self.cron_expressions = {
            "daily": "0 18 * * *",      # 每天18:00
            "weekly": "0 17 * * 5",      # 每周五17:00
            "monthly": "0 10 1 * *",    # 每月1号10:00
        }
        
        # 调度线程
        self._scheduler_thread: Optional[threading.Thread] = None
        self._running = False
    
    def _load_schedule(self) -> Dict:
        """加载调度配置"""
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r') as f:
                return json.load(f)
        return {
            "daily": {"enabled": True, "time": "18:00"},
            "weekly": {"enabled": True, "time": "17:00", "day": "friday"},
            "monthly": {"enabled": False, "time": "10:00", "day": "1"}
        }
    
    def _save_schedule(self):
        """保存调度配置"""
        os.makedirs(os.path.dirname(self.config_path) or ".", exist_ok=True)
        with open(self.config_path, 'w') as f:
            json.dump(self.schedule_config, f, indent=2)
    
    # ---- 状态收集 ----
    def register_status_collector(self, agent_id: str, collector: callable):
        """注册状态收集器"""
        self.status_collectors[agent_id] = collector
        log.info(f"注册状态收集器: {agent_id}")
    
    def collect_agent_status(self, agent_id: str = None) -> List[AgentStatus]:
        """收集Agent状态"""
        
        statuses = []
        
        # 如果有路由器，从路由器获取
        if self.router:
            agents = self.router.list_all_agents()
            
            for agent in agents:
                # 调用收集器
                collector = self.status_collectors.get(agent["id"])
                
                if collector:
                    try:
                        data = collector()
                        status = AgentStatus(
                            agent_id=agent["id"],
                            agent_name=agent["name"],
                            **data
                        )
                    except Exception as e:
                        log.error(f"收集器失败: {agent['id']}, {e}")
                        status = AgentStatus(
                            agent_id=agent["id"],
                            agent_name=agent["name"],
                            status="error"
                        )
                else:
                    # 默认状态
                    status = AgentStatus(
                        agent_id=agent["id"],
                        agent_name=agent["name"],
                        status="active"
                    )
                
                statuses.append(status)
        else:
            # 没有路由器，返回模拟状态
            default_agents = ["教皇", "红衣主教团", "主教团", "枢机处", "工匠行会", "财政部"]
            for agent_id in default_agents:
                statuses.append(AgentStatus(
                    agent_id=agent_id,
                    agent_name=agent_id,
                    status="active"
                ))
        
        return statuses
    
    # ---- 报告生成 ----
    def generate_report(self, report_type: ReportType, force: bool = False) -> Report:
        """生成报告"""
        
        report_id = f"report_{report_type.value}_{int(time.time())}"
        
        report = Report(
            id=report_id,
            type=report_type,
            title=self._get_report_title(report_type),
            status=ReportStatus.GENERATING
        )
        
        self.reports[report_id] = report
        
        log.info(f"生成{report_type.value}报告: {report_id}")
        
        try:
            # 收集状态
            statuses = self.collect_agent_status()
            report.agent_statuses = statuses
            
            # 生成内容
            content = self._compile_report(report_type, statuses)
            report.content = content
            
            report.status = ReportStatus.COMPLETED
            report.generated_at = time.time()
            
            # 发送通知
            self._send_notification(report)
            
            log.info(f"报告生成完成: {report_id}")
            
        except Exception as e:
            log.error(f"报告生成失败: {e}")
            report.status = ReportStatus.FAILED
        
        return report
    
    def _get_report_title(self, report_type: ReportType) -> str:
        """获取报告标题"""
        now = datetime.now()
        
        if report_type == ReportType.DAILY:
            return f"【日报】{now.strftime('%Y-%m-%d')} Edict运营报告"
        elif report_type == ReportType.WEEKLY:
            week = now.isocalendar()[1]
            return f"【周报】第{week}周 Edict运营报告"
        elif report_type == ReportType.MONTHLY:
            return f"【月报】{now.strftime('%Y年%m月')} Edict运营报告"
        
        return "Edict运营报告"
    
    def _compile_report(self, report_type: ReportType, statuses: List[AgentStatus]) -> str:
        """编译报告内容"""
        
        now = datetime.now()
        
        # 统计
        total_agents = len(statuses)
        active_agents = sum(1 for s in statuses if s.status == "active")
        error_agents = sum(1 for s in statuses if s.status == "error")
        
        total_tasks = sum(s.tasks_completed for s in statuses)
        pending_tasks = sum(s.tasks_pending for s in statuses)
        
        content = f"""# {self._get_report_title(report_type)}

## 📊 总体概览

| 指标 | 数值 |
|-----|------|
| Agent总数 | {total_agents} |
| 在线Agent | {active_agents} |
| 异常Agent | {error_agents} |
| 完成任务 | {total_tasks} |
| 待处理任务 | {pending_tasks} |

## 🤖 Agent状态详情

"""
        
        # 按层级分组
        if self.router:
            content += "### 🏛️ 决策层\n\n"
            for s in statuses:
                if self.router.agents.get(s.agent_id):
                    level = self.router.agents[s.agent_id].level
                    if level.value == 0 or level.value == 1:
                        content += self._format_agent_status(s)
            
            content += "\n### 📋 执行层\n\n"
            for s in statuses:
                if self.router.agents.get(s.agent_id):
                    level = self.router.agents[s.agent_id].level
                    if level.value >= 2:
                        content += self._format_agent_status(s)
        else:
            for s in statuses:
                content += self._format_agent_status(s)
        
        # 本期重点
        content += f"""
## 📝 本期重点

"""
        
        if report_type == ReportType.DAILY:
            content += "- 今日任务完成情况\n"
            content += "- 遇到的问题及解决方案\n"
            content += "- 明日计划\n"
        elif report_type == ReportType.WEEKLY:
            content += "- 本周目标完成情况\n"
            content += "- 重大事项回顾\n"
            content += "- 下周计划\n"
        elif report_type == ReportType.MONTHLY:
            content += "- 本月目标达成率\n"
            content += "- 重大里程碑\n"
            content += "- 下月计划\n"
        
        # 页脚
        content += f"""
---
*报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""
        
        return content
    
    def _format_agent_status(self, status: AgentStatus) -> str:
        """格式化Agent状态"""
        
        emoji = {
            "active": "✅",
            "idle": "💤",
            "error": "❌"
        }.get(status.status, "❓")
        
        return f"""- **{status.agent_name}** ({status.agent_id}) {emoji}
  - 完成任务: {status.tasks_completed} | 待办: {status.tasks_pending}
  - 消息: 📤{status.messages_sent} | 📥{status.messages_received}

"""
    
    # ---- 通知发送 ----
    def _send_notification(self, report: Report):
        """发送报告通知"""
        
        # 飞书通知
        if self.feishu_webhook:
            try:
                import requests
                payload = {
                    "msg_type": "interactive",
                    "card": {
                        "header": {
                            "title": {
                                "tag": "plain_text",
                                "content": report.title
                            },
                            "template": "blue"
                        },
                        "elements": [
                            {
                                "tag": "markdown",
                                "content": report.content[:2000]  # 飞书卡片有长度限制
                            },
                            {
                                "tag": "action",
                                "actions": [
                                    {
                                        "tag": "button",
                                        "text": {"tag": "plain_text", "content": "查看详情"},
                                        "type": "primary",
                                        "url": f"https://example.com/reports/{report.id}"
                                    }
                                ]
                            }
                        ]
                    }
                }
                requests.post(self.feishu_webhook, json=payload, timeout=10)
                log.info(f"飞书通知发送成功")
            except Exception as e:
                log.error(f"飞书通知失败: {e}")
    
    # ---- 手动触发 ----
    def trigger_daily(self) -> Report:
        """手动触发日报"""
        return self.generate_report(ReportType.DAILY)
    
    def trigger_weekly(self) -> Report:
        """手动触发周报"""
        return self.generate_report(ReportType.WEEKLY)
    
    def trigger_monthly(self) -> Report:
        """手动触发月报"""
        return self.generate_report(ReportType.MONTHLY)
    
    # ---- 定时调度 ----
    def start_scheduler(self, check_interval: int = 60):
        """启动定时调度"""
        
        self._running = True
        
        def run():
            log.info("报告调度器已启动")
            
            while self._running:
                now = datetime.now()
                current_time = now.strftime("%H:%M")
                current_weekday = now.weekday()  # 0=周一
                current_day = now.day
                
                # 检查日报
                if self.schedule_config.get("daily", {}).get("enabled"):
                    target_time = self.schedule_config["daily"].get("time", "18:00")
                    if current_time == target_time:
                        log.info("触发日报")
                        self.generate_report(ReportType.DAILY)
                
                # 检查周报 (周五)
                if self.schedule_config.get("weekly", {}).get("enabled"):
                    target_time = self.schedule_config["weekly"].get("time", "17:00")
                    if current_weekday == 4 and current_time == target_time:  # Friday
                        log.info("触发周报")
                        self.generate_report(ReportType.WEEKLY)
                
                # 检查月报 (每月1号)
                if self.schedule_config.get("monthly", {}).get("enabled"):
                    target_time = self.schedule_config["monthly"].get("time", "10:00")
                    if current_day == 1 and current_time == target_time:
                        log.info("触发月报")
                        self.generate_report(ReportType.MONTHLY)
                
                time.sleep(check_interval)
        
        self._scheduler_thread = threading.Thread(target=run, daemon=True)
        self._scheduler_thread.start()
        
        log.info("报告调度器已启动")
    
    def stop_scheduler(self):
        """停止调度"""
        self._running = False
        if self._scheduler_thread:
            self._scheduler_thread.join(timeout=5)
        log.info("报告调度器已停止")
    
    # ---- 查询 ----
    def get_report(self, report_id: str) -> Optional[Report]:
        """获取报告"""
        return self.reports.get(report_id)
    
    def list_reports(self, report_type: ReportType = None, limit: int = 10) -> List[Report]:
        """列出报告"""
        reports = list(self.reports.values())
        
        if report_type:
            reports = [r for r in reports if r.type == report_type]
        
        reports.sort(key=lambda x: x.created_at, reverse=True)
        return reports[:limit]
    
    def get_latest(self, report_type: ReportType) -> Optional[Report]:
        """获取最新报告"""
        reports = self.list_reports(report_type, 1)
        return reports[0] if reports else None


# ==================== CLI ====================
def main():
    import argparse
    parser = argparse.ArgumentParser(description='报告调度器')
    parser.add_argument('--daily', action='store_true', help='生成日报')
    parser.add_argument('--weekly', action='store_true', help='生成周报')
    parser.add_argument('--monthly', action='store_true', help='生成月报')
    parser.add_argument('--list', action='store_true', help='列出报告')
    parser.add_argument('--view', help='查看报告')
    parser.add_argument('--start', action='store_true', help='启动调度器')
    parser.add_argument('--stop', action='store_true', help='停止调度器')
    parser.add_argument('--config', default='config/report_config.json', help='配置文件')
    
    args = parser.parse_args()
    
    scheduler = ReportScheduler(args.config)
    
    if args.daily:
        report = scheduler.trigger_daily()
        print(f"日报生成: {report.id}")
        print(report.content)
    
    elif args.weekly:
        report = scheduler.trigger_weekly()
        print(f"周报生成: {report.id}")
        print(report.content)
    
    elif args.monthly:
        report = scheduler.trigger_monthly()
        print(f"月报生成: {report.id}")
        print(report.content)
    
    elif args.list:
        for r in scheduler.list_reports():
            print(f"{r.id:30} | {r.type.value:10} | {r.status.value:10} | {datetime.fromtimestamp(r.created_at)}")
    
    elif args.view:
        report = scheduler.get_report(args.view)
        if report:
            print(report.content)
        else:
            print("报告不存在")
    
    elif args.start:
        scheduler.start_scheduler()
        print("调度器已启动，按Ctrl+C停止")
        try:
            while True: time.sleep(1)
        except KeyboardInterrupt:
            scheduler.stop_scheduler()

if __name__ == '__main__':
    main()
