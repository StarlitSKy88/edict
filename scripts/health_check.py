#!/usr/bin/env python3
"""
Edict 健康检查脚本
检查所有关键组件状态
"""
import json
import pathlib
import sys
import subprocess

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / 'scripts'))

BASE = pathlib.Path(__file__).parent.parent
DATA = BASE / 'data'

def check_file_exists(path, name):
    """检查文件是否存在"""
    exists = path.exists()
    status = "✅" if exists else "❌"
    print(f"{status} {name}: {path}")
    return exists

def check_json_valid(path, name):
    """检查 JSON 是否有效"""
    try:
        content = json.loads(path.read_text())
        print(f"✅ {name}: JSON 有效 ({len(str(content))} bytes)")
        return True
    except Exception as e:
        print(f"❌ {name}: JSON 无效 - {e}")
        return False

def check_scripts():
    """检查脚本语法"""
    print("\n📜 检查脚本...")
    scripts = [
        'scripts/utils.py',
        'scripts/file_lock.py', 
        'scripts/kanban_update.py',
        'scripts/refresh_live_data.py',
    ]
    
    all_ok = True
    for script in scripts:
        path = BASE / script
        if not path.exists():
            print(f"❌ {script}: 不存在")
            all_ok = False
            continue
            
        result = subprocess.run(
            ['python3', '-m', 'py_compile', str(path)],
            capture_output=True
        )
        if result.returncode == 0:
            print(f"✅ {script}: 语法正确")
        else:
            print(f"❌ {script}: 语法错误 - {result.stderr.decode()[:100]}")
            all_ok = False
    
    return all_ok

def main():
    print("=" * 50)
    print("🏛️  Edict 健康检查")
    print("=" * 50)
    
    all_ok = True
    
    # 检查数据文件
    print("\n📁 检查数据文件...")
    all_ok &= check_file_exists(DATA / 'tasks_source.json', "任务数据")
    all_ok &= check_file_exists(DATA / 'live_status.json', "实时状态")
    all_ok &= check_file_exists(DATA / 'agent_config.json', "Agent 配置")
    all_ok &= check_file_exists(DATA / 'officials_stats.json', "官员统计")
    
    # 检查 JSON 有效性
    print("\n🔍 检查 JSON 有效性...")
    for json_file in ['tasks_source.json', 'live_status.json', 'agent_config.json']:
        path = DATA / json_file
        if path.exists():
            all_ok &= check_json_valid(path, json_file)
    
    # 检查脚本
    all_ok &= check_scripts()
    
    print("\n" + "=" * 50)
    if all_ok:
        print("✅ 健康检查通过")
    else:
        print("⚠️  健康检查发现问题")
    print("=" * 50)
    
    return 0 if all_ok else 1

if __name__ == '__main__':
    sys.exit(main())
