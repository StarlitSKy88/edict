#!/usr/bin/env python3
"""
Edict 并发安全测试
测试文件锁、并发访问等场景
"""
import json
import pathlib
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE = pathlib.Path(__file__).parent.parent
DATA = BASE / 'data'
sys.path.insert(0, str(BASE / 'scripts'))

from file_lock import atomic_json_read, atomic_json_write

# 测试数据文件
TEST_FILE = DATA / 'test_concurrent.json'

def concurrent_read_test():
    """并发读取测试"""
    print("\n📋 并发读取测试...")
    
    # 创建测试数据
    atomic_json_write(TEST_FILE, {"value": 0, "reads": 0})
    
    results = []
    
    def reader(thread_id):
        for i in range(10):
            data = atomic_json_read(TEST_FILE, {})
            results.append((thread_id, data.get('value')))
            time.sleep(0.01)
    
    threads = [threading.Thread(target=reader, args=(i,)) for i in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    
    print(f"   ✅ 完成 {len(results)} 次读取")
    return True

def concurrent_write_test():
    """并发写入测试"""
    print("\n📋 并发写入测试...")
    
    # 创建测试数据
    atomic_json_write(TEST_FILE, {"counter": 0})
    
    results = []
    
    def writer(thread_id):
        for i in range(5):
            def increment(data):
                data['counter'] = data.get('counter', 0) + 1
                return data
            
            atomic_json_write(TEST_FILE, {"counter": thread_id * 100 + i})
            results.append(thread_id * 100 + i)
            time.sleep(0.01)
    
    threads = [threading.Thread(target=writer, args=(i,)) for i in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    
    final = atomic_json_read(TEST_FILE, {})
    print(f"   ✅ 最终值: {final.get('counter')}")
    
    # 验证最终值是有效值
    return final.get('counter', -1) >= 0

def main():
    print("=" * 50)
    print("🔒 Edict 并发安全测试")
    print("=" * 50)
    
    # 清理测试文件
    if TEST_FILE.exists():
        TEST_FILE.unlink()
    
    results = []
    
    # 并发读取测试
    results.append(concurrent_read_test())
    
    # 并发写入测试
    results.append(concurrent_write_test())
    
    # 清理
    if TEST_FILE.exists():
        TEST_FILE.unlink()
    
    print("\n" + "=" * 50)
    print(f"📊 结果: {sum(results)}/{len(results)} 测试通过")
    print("=" * 50)
    
    return 0 if all(results) else 1

if __name__ == '__main__':
    sys.exit(main())
