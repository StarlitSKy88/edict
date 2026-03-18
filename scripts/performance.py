#!/usr/bin/env python3
"""
Edict 性能分析器
分析任务执行性能、发现问题
"""
import json
import pathlib
import sys
from collections import Counter
from datetime import datetime

BASE = pathlib.Path(__file__).parent.parent
DATA = BASE / 'data'

def analyze_performance():
    """分析任务执行性能"""
    tasks = json.loads((DATA / 'tasks_source.json').read_text())
    
    if not tasks:
        print("无任务数据")
        return
    
    # 计算平均执行时间
    durations = []
    for t in tasks:
        created = t.get('createdAt', '')
        updated = t.get('updatedAt', '')
        
        if created and updated and t.get('state') == 'Done':
            try:
                c = datetime.fromisoformat(created.replace('Z', '+00:00'))
                u = datetime.fromisoformat(updated.replace('Z', '+00:00'))
                duration = (u - c).total_seconds() / 60  # 分钟
                durations.append(duration)
            except:
                pass
    
    if durations:
        avg = sum(durations) / len(durations)
        print(f"📊 平均任务执行时间: {avg:.1f} 分钟")
        print(f"   最快: {min(durations):.1f} 分钟")
        print(f"   最慢: {max(durations):.1f} 分钟")
    
    # 部门效率排名
    org_times = {}
    for t in tasks:
        org = t.get('org', 'unknown')
        if t.get('state') == 'Done':
            created = t.get('createdAt', '')
            updated = t.get('updatedAt', '')
            if created and updated:
                try:
                    c = datetime.fromisoformat(created.replace('Z', '+00:00'))
                    u = datetime.fromisoformat(updated.replace('Z', '+00:00'))
                    duration = (u - c).total_seconds() / 60
                    if org not in org_times:
                        org_times[org] = []
                    org_times[org].append(duration)
                except:
                    pass
    
    if org_times:
        print("\n📊 部门效率排名:")
        avg_by_org = [(org, sum(times)/len(times)) for org, times in org_times.items()]
        avg_by_org.sort(key=lambda x: x[1])
        for i, (org, avg) in enumerate(avg_by_org[:5], 1):
            print(f"   {i}. {org}: {avg:.1f} 分钟")

def analyze_blocked():
    """分析阻塞任务"""
    tasks = json.loads((DATA / 'tasks_source.json').read_text())
    
    blocked = [t for t in tasks if t.get('state') == 'Blocked']
    
    if blocked:
        print(f"\n⚠️  阻塞任务: {len(blocked)} 个")
        for t in blocked[:5]:
            print(f"   - {t.get('id')}: {t.get('title', '')[:30]}")
    else:
        print("\n✅ 无阻塞任务")

def main():
    print("=" * 50)
    print("📈 Edict 性能分析")
    print("=" * 50)
    
    analyze_performance()
    analyze_blocked()
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
