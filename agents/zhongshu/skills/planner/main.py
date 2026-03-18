#!/usr/bin/env python3
"""
中书省 Skill - 任务规划器
功能: 需求分析、任务拆解、风险评估、资源规划
"""
import sys
import json
import re
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class SubTask:
    title: str
    dept: str
    days: int
    priority: str = "normal"
    dependencies: list = field(default_factory=list)

@dataclass
class Risk:
    description: str
    severity: str  # high, medium, low
    mitigation: str

@dataclass
class Plan:
    task_id: str
    title: str
    subtasks: list[SubTask] = field(default_factory=list)
    risks: list[Risk] = field(default_factory=list)
    resources: list[str] = field(default_factory=list)
    estimated_days: int = 0

class TaskPlanner:
    """任务规划器"""
    
    # 部门能力映射
    DEPT_CAPABILITIES = {
        '吏部': ['调研', '招聘', '培训', '规划'],
        '户部': ['财务', '预算', '核算', '资金'],
        '礼部': ['文案', '内容', '策划', '外交'],
        '兵部': ['安全', '风控', '合规', '安保'],
        '刑部': ['审计', '法务', '合规', '审查'],
        '工部': ['开发', '技术', '架构', '运维'],
        '钦天监': ['分析', '预测', '研究', '观测']
    }
    
    # 任务类型到部门的映射
    TASK_TYPE_DEPT = {
        '开发': '工部',
        '代码': '工部',
        '技术': '工部',
        '财务': '户部',
        '预算': '户部',
        '招聘': '吏部',
        '人员': '吏部',
        '文案': '礼部',
        '内容': '礼部',
        '安全': '兵部',
        '合规': '兵部',
        '法务': '刑部',
        '审计': '刑部',
        '分析': '钦天监',
        '研究': '钦天监'
    }
    
    def plan(self, task_description: str, task_id: str = "") -> Plan:
        """制定任务计划"""
        
        # 1. 解析任务
        title = self._parse_title(task_description)
        
        # 2. 拆解子任务
        subtasks = self._decompose_task(task_description)
        
        # 3. 风险评估
        risks = self._assess_risks(task_description, subtasks)
        
        # 4. 资源规划
        resources = self._plan_resources(subtasks)
        
        # 5. 计算总工期
        total_days = sum(st.days for st in subtasks)
        
        return Plan(
            task_id=task_id,
            title=title,
            subtasks=subtasks,
            risks=risks,
            resources=resources,
            estimated_days=total_days
        )
    
    def _parse_title(self, description: str) -> str:
        """解析任务标题"""
        # 移除"帮我"等前缀
        title = re.sub(r'^(帮我|请|麻烦|能不能)[把帮个]?', '', description)
        
        # 截取核心内容
        if len(title) > 30:
            title = title[:30] + "..."
        
        return title
    
    def _decompose_task(self, description: str) -> list[SubTask]:
        """拆解子任务"""
        subtasks = []
        
        # 基于关键词识别任务类型
        task_type = "通用"
        for kw, dept in self.TASK_TYPE_DEPT.items():
            if kw in description:
                task_type = kw
                break
        
        # 标准拆解
        subtasks.append(SubTask(
            title="需求确认",
            dept="中书省",
            days=0.5,
            priority="high"
        ))
        
        # 根据任务类型添加具体子任务
        if task_type == '开发':
            subtasks.extend([
                SubTask(title="技术调研", dept="工部", days=1),
                SubTask(title="方案设计", dept="工部", days=1),
                SubTask(title="开发实施", dept="工部", days=3),
                SubTask(title="测试验收", dept="工部", days=1)
            ])
        elif task_type == '财务':
            subtasks.extend([
                SubTask(title="财务分析", dept="户部", days=1),
                SubTask(title="预算编制", dept="户部", days=1),
                SubTask(title="审批流转", dept="户部", days=0.5)
            ])
        elif task_type == '内容':
            subtasks.extend([
                SubTask(title="内容策划", dept="礼部", days=1),
                SubTask(title="文案撰写", dept="礼部", days=1),
                SubTask(title="审核发布", dept="礼部", days=0.5)
            ])
        else:
            # 默认拆解
            subtasks.extend([
                SubTask(title="调研分析", dept="吏部", days=1),
                SubTask(title="方案制定", dept="中书省", days=1),
                SubTask(title="执行落地", dept="工部", days=2)
            ])
        
        # 添加汇总
        subtasks.append(SubTask(
            title="汇总归档",
            dept="尚书省",
            days=0.5,
            priority="low"
        ))
        
        return subtasks
    
    def _assess_risks(self, description: str, subtasks: list[SubTask]) -> list[Risk]:
        """风险评估"""
        risks = []
        
        # 检查工期风险
        total_days = sum(st.days for st in subtasks)
        if total_days > 5:
            risks.append(Risk(
                description="工期较长，可能延期",
                severity="medium",
                mitigation="预留buffer时间，及时预警"
            ))
        
        # 检查复杂度
        if len(subtasks) > 5:
            risks.append(Risk(
                description="子任务较多，协调复杂",
                severity="low",
                mitigation="明确各任务依赖关系"
            ))
        
        # 检查跨部门
        depts = set(st.dept for st in subtasks)
        if len(depts) > 3:
            risks.append(Risk(
                description="跨部门协作，沟通成本高",
                severity="medium",
                mitigation="提前协调，明确接口"
            ))
        
        return risks
    
    def _plan_resources(self, subtasks: list[SubTask]) -> list[str]:
        """资源规划"""
        resources = []
        
        # 收集所需部门
        depts = set(st.dept for st in subtasks)
        
        for dept in depts:
            if dept != "中书省" and dept != "尚书省":
                resources.append(f"{dept}支持")
        
        return resources

def main():
    import argparse
    parser = argparse.ArgumentParser(description='中书省任务规划器')
    parser.add_argument('--task', '-t', required=True, help='任务描述')
    parser.add_argument('--task-id', '-i', help='任务ID')
    parser.add_argument('--json', '-j', action='store_true', help='JSON输出')
    
    args = parser.parse_args()
    
    planner = TaskPlanner()
    plan = planner.plan(args.task, args.task_id or "")
    
    if args.json:
        print(json.dumps({
            'task_id': plan.task_id,
            'title': plan.title,
            'estimated_days': plan.estimated_days,
            'subtasks': [
                {
                    'title': st.title,
                    'dept': st.dept,
                    'days': st.days,
                    'priority': st.priority
                }
                for st in plan.subtasks
            ],
            'risks': [
                {
                    'description': r.description,
                    'severity': r.severity,
                    'mitigation': r.mitigation
                }
                for r in plan.risks
            ],
            'resources': plan.resources
        }, ensure_ascii=False, indent=2))
    else:
        print(f"任务: {plan.title}")
        print(f"工期: {plan.estimated_days}天")
        print(f"\n子任务:")
        for st in plan.subtasks:
            print(f"  - {st.title} ({st.dept}, {st.days}天, {st.priority})")
        
        if plan.risks:
            print(f"\n风险:")
            for r in plan.risks:
                print(f"  - [{r.severity}] {r.description}")
        
        if plan.resources:
            print(f"\n资源: {', '.join(plan.resources)}")

if __name__ == '__main__':
    main()
