#!/usr/bin/env python3
"""
Edict 边界保护器
自动检测并修复常见问题
"""
import json
import pathlib
import sys
import shutil
import time
from datetime import datetime, timedelta

BASE = pathlib.Path(__file__).parent.parent
DATA = BASE / 'data'
sys.path.insert(0, str(BASE / 'scripts'))

from utils import read_json, write_json, now_iso

def fix_corrupted_json():
    """修复损坏的JSON文件"""
    fixed = []
    
    json_files = [
        'tasks_source.json',
        'live_status.json',
        'agent_config.json',
        'officials_stats.json',
    ]
    
    for filename in json_files:
        path = DATA / filename
        if not path.exists():
            continue
            
        try:
            # 尝试解析
            data = json.loads(path.read_text())
            print(f"✅ {filename}: 正常")
        except json.JSONDecodeError as e:
            print(f"❌ {filename}: 损坏 - {e}")
            
            # 创建备份
            backup = DATA / 'corrupted' / f"{filename}.{int(time.time())}"
            backup.parent.mkdir(exist_ok=True)
            shutil.copy2(path, backup)
            print(f"   📦 已备份到 {backup.name}")
            
            # 修复：根据文件类型创建空数据
            if filename == 'tasks_source.json':
                path.write_text("[]")
            else:
                path.write_text("{}")
            
            print(f"   🔧 已重建")
            fixed.append(filename)
    
    return len(fixed)

def fix_stale_locks():
    """清理过期的锁文件"""
    locks_removed = 0
    
    for lock in DATA.glob("*.lock"):
        try:
            age = datetime.now() - datetime.fromtimestamp(lock.stat().st_mtime)
            if age > timedelta(hours=1):
                lock.unlink()
                print(f"🗑️  删除过期锁: {lock.name}")
                locks_removed += 1
        except Exception as e:
            print(f"⚠️  处理锁失败: {lock.name} - {e}")
    
    return locks_removed

def fix_orphaned_tasks():
    """修复孤立任务(没有flow_log的任务)"""
    tasks = read_json(DATA / 'tasks_source.json', [])
    fixed = 0
    
    for task in tasks:
        if 'flow_log' not in task:
            task['flow_log'] = [{
                'at': task.get('createdAt', now_iso()),
                'from': 'system',
                'to': task.get('org', 'unknown'),
                'remark': '自动修复：添加flow_log'
            }]
            fixed += 1
    
    if fixed > 0:
        write_json(DATA / 'tasks_source.json', tasks)
        print(f"🔧 修复了 {fixed} 个孤立任务")
    
    return len(fixed)

def fix_missing_fields():
    """修复缺失字段"""
    tasks = read_json(DATA / 'tasks_source.json', [])
    fixed = 0
    
    for task in tasks:
        # 补全必要字段
        if 'id' not in task:
            task['id'] = f"JJC-{datetime.now().strftime('%Y%m%d')}-{len(tasks):03d}"
            fixed += 1
        if 'createdAt' not in task:
            task['createdAt'] = now_iso()
        if 'updatedAt' not in task:
            task['updatedAt'] = task.get('createdAt', now_iso())
        if 'state' not in task:
            task['state'] = 'Pending'
            fixed += 1
    
    if fixed > 0:
        write_json(DATA / 'tasks_source.json', tasks)
        print(f"🔧 补全了 {fixed} 个任务字段")
    
    return len(fixed)

def fix_duplicate_ids():
    """修复重复ID"""
    tasks = read_json(DATA / 'tasks_source.json', [])
    seen = set()
    duplicates = []
    
    for task in tasks:
        task_id = task.get('id', '')
        if task_id in seen:
            duplicates.append(task)
        else:
            seen.add(task_id)
    
    # 删除重复任务（保留第一个）
    if duplicates:
        tasks = [t for t in tasks if t not in duplicates]
        write_json(DATA / 'tasks_source.json', tasks)
        print(f"🗑️  删除了 {len(duplicates)} 个重复任务")
        return len(duplicates)
    
    return 0

def main():
    print("=" * 50)
    print("🛡️  Edict 边界保护器")
    print("=" * 50)
    print(f"时间: {now_iso()}")
    print()
    
    fixes = []
    
    print("📁 检查 JSON 文件...")
    fixes.append(("损坏JSON", fix_corrupted_json()))
    
    print("\n🔒 检查锁文件...")
    fixes.append(("过期锁", fix_stale_locks()))
    
    print("\n👻 检查孤立任务...")
    fixes.append(("孤立任务", fix_orphaned_tasks()))
    
    print("\n📝 检查缺失字段...")
    fixes.append(("缺失字段", fix_missing_fields()))
    
    print("\n🔄 检查重复ID...")
    fixes.append(("重复ID", fix_duplicate_ids()))
    
    print("\n" + "=" * 50)
    print("📊 修复总结:")
    total = 0
    for name, count in fixes:
        status = "✅" if count == 0 else f"🔧 {count}项"
        print(f"   {name}: {status}")
        total += count
    
    if total == 0:
        print("   ✨ 无需修复，系统健康!")
    print("=" * 50)
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
