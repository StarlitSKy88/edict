#!/usr/bin/env python3
"""
Edict 工具箱 - 反思学习
"""
import json
from pathlib import Path
from dataclasses import dataclass, field
from typing import List
from datetime import datetime

@dataclass
class Reflection:
    """反思结果"""
    task_id: str
    goal: str
    actual: str
    lessons: List[str] = field(default_factory=list)
    improvements: List[str] = field(default_factory=list)
    patterns: List[str] = field(default_factory=list)
    score: float = 0.0

class Reflector:
    """反思学习器"""
    
    def reflect(
        self,
        task_id: str,
        task_goal: str,
        actual_result: str,
        errors: List[str] = None,
        successes: List[str] = None
    ) -> Reflection:
        """反思任务"""
        
        errors = errors or []
        successes = successes or []
        
        # 计算得分
        if errors and successes:
            score = len(successes) / (len(errors) + len(successes)) * 100
        elif successes:
            score = 100.0
        else:
            score = 0.0
        
        # 提取经验教训
        lessons = []
        
        # 从错误中学习
        for error in errors:
            lessons.append(f"需要改进: {error}")
        
        # 从成功中学习
        for success in successes:
            lessons.append(f"保持: {success}")
        
        # 生成改进建议
        improvements = []
        
        if len(errors) > 2:
            improvements.append("建议将大型任务拆分为更小的子任务")
        
        if errors and "时间" in str(errors):
            improvements.append("未来任务建议增加20%的时间buffer")
        
        if errors and "沟通" in str(errors):
            improvements.append("建议增加中间节点确认环节")
        
        # 模式识别
        patterns = []
        if len(errors) >= 3:
            patterns.append("该Agent可能存在系统性问题，需要全面复盘")
        
        return Reflection(
            task_id=task_id,
            goal=task_goal,
            actual=actual_result,
            lessons=lessons,
            improvements=improvements,
            patterns=patterns,
            score=score
        )
    
    def save(self, reflection: Reflection):
        """保存反思结果"""
        from pathlib import Path
        file = Path(__file__).parent.parent / 'data' / 'reflections.json'
        file.parent.mkdir(parents=True, exist_ok=True)
        
        # 读取现有
        existing = []
        if file.exists():
            existing = json.loads(file.read_text())
        
        existing.append({
            'task_id': reflection.task_id,
            'goal': reflection.goal,
            'actual': reflection.actual,
            'lessons': reflection.lessons,
            'improvements': reflection.improvements,
            'score': reflection.score,
            'time': datetime.now().isoformat()
        })
        
        file.write_text(json.dumps(existing, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    reflector = Reflector()
    r = reflector.reflect(
        task_id="JJC-001",
        task_goal="完成API开发",
        actual_result="延迟3天，代码有bug",
        errors=["低估工作量", "测试不充分"],
        successes=["代码结构清晰", "文档完整"]
    )
    
    print(f"得分: {r.score}")
    print(f"经验: {r.lessons}")
    print(f"改进: {r.improvements}")
