#!/usr/bin/env python3
"""
Edict 监控系统
实时监控任务状态、发送告警
"""
import json
import pathlib
import time
import sys
import subprocess

BASE = pathlib.Path(__file__).parent.parent
DATA = BASE / 'data'
sys.path.insert(0, str(BASE / 'scripts'))

from utils import read_json, now_iso

def check_stuck_tasks():
    """检查卡住的任务"""
    tasks = read_json(DATA / 'tasks_source.json', [])
    
    stuck = []
    for t in tasks:
        if t.get('state') == 'Doing':
            # 简化检查：检查 updatedAt
            updated = t.get('updatedAt', '')
            if updated:
                stuck.append({
                    'id': t.get('id'),
                    'title': t.get('title', '')[:30],
                    'org': t.get('org', ''),
                })
    
    if stuck:
        print(f"⚠️  发现 {len(stuck)} 个可能卡住的任务:")
        for t in stuck[:5]:
            print(f"   - {t['id']}: {t['title']}")
    
    return stuck

def main():
    print(f"🏛️  Edict 监控 {now_iso()}")
    
    # 检查任务
    stuck = check_stuck_tasks()
    
    # 检查数据文件
    for f in ['tasks_source.json', 'live_status.json']:
        path = DATA / f
        if path.exists():
            size = path.stat().st_size
            print(f"✅ {f}: {size} bytes")
        else:
            print(f"❌ {f}: 不存在")
    
    return 0 if len(stuck) < 5 else 1

if __name__ == '__main__':
    sys.exit(main())
