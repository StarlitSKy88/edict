#!/usr/bin/env python3
"""
Edict 日志分析工具
分析任务日志、发现性能问题
"""
import json
import pathlib
import sys
from collections import Counter
from datetime import datetime

BASE = pathlib.Path(__file__).parent.parent
DATA = BASE / 'data'

def analyze_tasks():
    """分析任务统计数据"""
    tasks = json.loads((DATA / 'tasks_source.json').read_text())
    
    if not tasks:
        print("无任务数据")
        return
    
    # 按状态统计
    states = Counter(t.get('state', 'Unknown') for t in tasks)
    print("📊 任务状态分布:")
    for state, count in states.most_common():
        print(f"   {state}: {count}")
    
    # 按部门统计
    orgs = Counter(t.get('org', 'Unknown') for t in tasks)
    print("\n📊 任务部门分布:")
    for org, count in orgs.most_common():
        print(f"   {org}: {count}")
    
    # 计算完成率
    done = states.get('Done', 0)
    total = len(tasks)
    rate = done / total * 100 if total > 0 else 0
    print(f"\n📈 完成率: {rate:.1f}% ({done}/{total})")

def main():
    print("=" * 40)
    print("🏛️  Edict 日志分析")
    print("=" * 40)
    analyze_tasks()
    return 0

if __name__ == '__main__':
    sys.exit(main())
