#!/usr/bin/env python3
"""
Edict 数据备份脚本
自动备份关键数据文件
"""
import json
import shutil
import pathlib
import datetime
import sys
from pathlib import Path

BASE = Path(__file__).parent.parent
DATA = BASE / 'data'
BACKUP_DIR = BASE / 'data' / 'backups'

# 需要备份的文件
BACKUP_FILES = [
    'tasks_source.json',
    'live_status.json', 
    'agent_config.json',
    'officials_stats.json',
    'model_change_log.json',
]

def main():
    print(f"🏛️ Edict 数据备份")
    print("=" * 40)
    
    # 创建备份目录
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    
    # 创建时间戳目录
    timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_path = BACKUP_DIR / timestamp
    backup_path.mkdir(exist_ok=True)
    
    print(f"备份目标: {backup_path}")
    
    count = 0
    for filename in BACKUP_FILES:
        src = DATA / filename
        if src.exists():
            dst = backup_path / filename
            shutil.copy2(src, dst)
            print(f"✅ {filename}")
            count += 1
        else:
            print(f"⏭️  {filename} (跳过)")
    
    print(f"\n完成: {count}/{len(BACKUP_FILES)} 文件已备份")
    
    # 清理旧备份（保留最近 10 个）
    backups = sorted(BACKUP_DIR.glob("????????"), reverse=True)
    for old in backups[10:]:
        shutil.rmtree(old)
        print(f"🗑️  清理旧备份: {old.name}")
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
