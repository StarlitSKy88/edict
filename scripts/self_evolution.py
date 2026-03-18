#!/usr/bin/env python3
"""
Edict 自主进化系统 - 自我决策、自我学习、自我进化
"""
import json
import subprocess
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import hashlib

BASE = Path(__file__).parent.parent
DATA = BASE / 'data'
EVOLUTION_DIR = DATA / 'evolution'
EVOLUTION_DIR.mkdir(parents=True, exist_ok=True)

@dataclass
class TaskRecord:
    task_id: str
    agent_id: str
    success: bool
    duration_ms: int
    retries: int
    errors: list[str] = field(default_factory=list)
    lessons: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

class SelfEvolution:
    """自主进化系统"""
    
    def __init__(self):
        self.record_file = EVOLUTION_DIR / 'task_records.json'
        self.pattern_file = EVOLUTION_DIR / 'patterns.json'
        self.stats_file = EVOLUTION_DIR / 'agent_stats.json'
        self._init_files()
    
    def _init_files(self):
        for f in [self.record_file, self.pattern_file, self.stats_file]:
            if not f.exists():
                f.write_text('[]')
    
    def record_task(self, task_id: str, agent_id: str, success: bool, 
                   duration_ms: int, retries: int, errors: list[str] = None):
        """记录任务执行结果"""
        records = json.loads(self.record_file.read_text())
        
        record = TaskRecord(
            task_id=task_id,
            agent_id=agent_id,
            success=success,
            duration_ms=duration_ms,
            retries=retries,
            errors=errors or []
        )
        
        records.append(record.__dict__)
        self.record_file.write_text(json.dumps(records, ensure_ascii=False, indent=2))
        
        # 更新统计
        self._update_stats(agent_id, success, duration_ms)
        
        # 如果失败，提取教训
        if not success:
            self._extract_lessons(agent_id, errors)
        
        # 检查是否需要进化
        self._check_evolution(agent_id)
    
    def _update_stats(self, agent_id: str, success: bool, duration_ms: int):
        """更新 Agent 统计"""
        stats = json.loads(self.stats_file.read_text())
        
        if agent_id not in stats:
            stats[agent_id] = {
                'total': 0,
                'success': 0,
                'failed': 0,
                'avg_duration': 0,
                'total_duration': 0
            }
        
        s = stats[agent_id]
        s['total'] += 1
        s['total_duration'] += duration_ms
        s['avg_duration'] = s['total_duration'] / s['total']
        
        if success:
            s['success'] += 1
        else:
            s['failed'] += 1
        
        self.stats_file.write_text(json.dumps(stats, ensure_ascii=False, indent=2))
    
    def _extract_lessons(self, agent_id: str, errors: list[str]):
        """从失败中提取教训"""
        if not errors:
            return
        
        patterns = json.loads(self.pattern_file.read_text())
        
        for error in errors:
            # 检查是否已有类似教训
            existing = [p for p in patterns if error in p.get('error_pattern', '')]
            
            if not existing:
                patterns.append({
                    'type': 'lesson',
                    'agent_id': agent_id,
                    'error_pattern': error,
                    'count': 1,
                    'created_at': datetime.now().isoformat()
                })
            else:
                existing[0]['count'] = existing[0].get('count', 1) + 1
        
        self.pattern_file.write_text(json.dumps(patterns, ensure_ascii=False, indent=2))
    
    def _check_evolution(self, agent_id: str):
        """检查是否需要进化"""
        stats = json.loads(self.stats_file.read_text())
        
        if agent_id not in stats:
            return
        
        s = stats[agent_id]
        
        # 如果失败率超过30%，触发进化
        if s['total'] >= 10:
            failure_rate = s['failed'] / s['total']
            
            if failure_rate > 0.3:
                self._evolve(agent_id, failure_rate)
    
    def _evolve(self, agent_id: str, failure_rate: float):
        """执行进化"""
        print(f"🔄 Agent {agent_id} 失败率 {failure_rate:.1%}，开始进化...")
        
        # 1. 分析失败模式
        patterns = json.loads(self.pattern_file.read_text())
        lessons = [p for p in patterns if p.get('agent_id') == agent_id and p.get('type') == 'lesson']
        
        # 2. 生成优化建议
        suggestions = self._generate_suggestions(agent_id, lessons)
        
        # 3. 记录进化
        evolution_log = {
            'agent_id': agent_id,
            'failure_rate': failure_rate,
            'suggestions': suggestions,
            'evolved_at': datetime.now().isoformat()
        }
        
        log_file = EVOLUTION_DIR / 'evolution_log.json'
        logs = json.loads(log_file.read_text()) if log_file.exists() else []
        logs.append(evolution_log)
        log_file.write_text(json.dumps(logs, ensure_ascii=False, indent=2))
        
        print(f"✅ 进化完成: {suggestions}")
    
    def _generate_suggestions(self, agent_id: str, lessons: list) -> list[str]:
        """生成优化建议"""
        suggestions = []
        
        # 统计错误类型
        error_counts = {}
        for lesson in lessons:
            error = lesson.get('error_pattern', '')
            error_counts[error] = error_counts.get(error, 0) + 1
        
        # 生成建议
        for error, count in sorted(error_counts.items(), key=lambda x: x[1], reverse=True)[:3]:
            if 'timeout' in error.lower():
                suggestions.append(f"增加超时时间，考虑添加重试机制")
            elif 'permission' in error.lower():
                suggestions.append(f"检查权限配置，添加权限申请流程")
            elif 'not found' in error.lower():
                suggestions.append(f"添加资源预检查，创建缺失资源")
            else:
                suggestions.append(f"优化错误处理: {error[:30]}")
        
        return suggestions
    
    def get_stats(self, agent_id: str = None) -> dict:
        """获取统计信息"""
        stats = json.loads(self.stats_file.read_text())
        
        if agent_id:
            return stats.get(agent_id, {})
        
        return stats
    
    def get_recommendations(self, agent_id: str) -> list[str]:
        """获取优化建议"""
        stats = self.get_stats(agent_id)
        
        recommendations = []
        
        # 基于统计生成建议
        if stats.get('total', 0) >= 10:
            failure_rate = stats.get('failed', 0) / stats.get('total', 1)
            
            if failure_rate > 0.3:
                recommendations.append(f"⚠️ 失败率过高: {failure_rate:.1%}，建议检查错误处理")
            
            if stats.get('avg_duration', 0) > 300000:  # 5分钟
                recommendations.append(f"⏱️ 平均执行时间过长: {stats['avg_duration']/1000:.0f}s")
        
        # 从模式中获取建议
        patterns = json.loads(self.pattern_file.read_text())
        lessons = [p for p in patterns if p.get('agent_id') == agent_id and p.get('type') == 'lesson']
        
        for lesson in lessons[:3]:
            recommendations.append(f"💡 {lesson.get('error_pattern', '')[:50]}")
        
        return recommendations

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Edict 自主进化系统')
    parser.add_argument('--record', '-r', nargs=5, help='记录任务: task_id agent success duration errors')
    parser.add_argument('--stats', '-s', help='查看统计')
    parser.add_argument('--recommend', '-R', help='获取建议')
    
    args = parser.parse_args()
    
    evo = SelfEvolution()
    
    if args.record:
        task_id, agent_id, success, duration, retries = args.record
        evo.record_task(
            task_id, 
            agent_id, 
            success.lower() == 'true',
            int(duration),
            int(retries)
        )
        print(f"✅ 已记录任务: {task_id}")
    
    elif args.stats:
        print(json.dumps(evo.get_stats(args.stats), indent=2, ensure_ascii=False))
    
    elif args.recommend:
        for r in evo.get_recommendations(args.recommend):
            print(r)
    
    else:
        print("用法:")
        print("  --record task_id agent success duration retries")
        print("  --stats agent_id")
        print("  --recommend agent_id")

if __name__ == '__main__':
    main()
