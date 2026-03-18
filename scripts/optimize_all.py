#!/usr/bin/env python3
"""
Edict 一键优化脚本
自动运行所有优化步骤
"""
import subprocess
import sys
import pathlib

BASE = pathlib.Path(__file__).parent.parent

def run_cmd(cmd, name):
    """运行命令并报告结果"""
    print(f"\n🔧 {name}...")
    result = subprocess.run(cmd, shell=True, capture_output=True, cwd=BASE)
    if result.returncode == 0:
        print(f"✅ {name} 完成")
        return True
    else:
        print(f"❌ {name} 失败: {result.stderr.decode()[:200]}")
        return False

def main():
    print("=" * 50)
    print("🏛️  Edict 一键优化")
    print("=" * 50)
    
    steps = [
        ("python3 scripts/health_check.py", "健康检查"),
        ("python3 scripts/analyze.py", "日志分析"),
        ("python3 scripts/monitor.py", "任务监控"),
    ]
    
    results = []
    for cmd, name in steps:
        results.append(run_cmd(cmd, name))
    
    print("\n" + "=" * 50)
    print(f"完成: {sum(results)}/{len(results)} 步骤成功")
    print("=" * 50)
    
    return 0 if all(results) else 1

if __name__ == '__main__':
    sys.exit(main())
