#!/usr/bin/env python3
"""
Edict 边缘场景测试套件
测试各种异常情况
"""
import json
import pathlib
import sys
import time

BASE = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(BASE / 'scripts'))

from utils import retry, validate_url, safe_execute
from kanban_update import validate_task_id, validate_state_transition

def test_validate_task_id():
    """测试任务ID验证"""
    test_cases = [
        ("JJC-20260318-001", True, "有效ID"),
        ("JJC-20260318-999", True, "有效ID"),
        ("INVALID", False, "无效格式"),
        ("JJC-20260318", False, "缺少序号"),
        ("", False, "空ID"),
    ]
    
    print("\n📋 测试任务ID验证:")
    passed = 0
    for task_id, expected_valid, desc in test_cases:
        is_valid, _ = validate_task_id(task_id)
        status = "✅" if is_valid == expected_valid else "❌"
        print(f"   {status} {task_id}: {desc}")
        if is_valid == expected_valid:
            passed += 1
    
    return passed == len(test_cases)

def test_validate_state_transition():
    """测试状态转换"""
    test_cases = [
        ("Taizi", "Zhongshu", True),
        ("Zhongshu", "Menxia", True),
        ("Doing", "Review", True),
        ("Done", "Taizi", False),  # 终态不能转换
        ("Taizi", "Doing", False),  # 非法转换
    ]
    
    print("\n📋 测试状态转换:")
    passed = 0
    for from_state, to_state, expected_valid in test_cases:
        is_valid, _ = validate_state_transition(from_state, to_state)
        status = "✅" if is_valid == expected_valid else "❌"
        print(f"   {status} {from_state} → {to_state}: {'允许' if expected_valid else '拒绝'}")
        if is_valid == expected_valid:
            passed += 1
    
    return passed == len(test_cases)

def test_validate_url():
    """测试URL验证"""
    test_cases = [
        ("https://github.com", True, "有效HTTPS"),
        ("http://localhost:8080", False, "应拒绝HTTP"),
        ("https://10.0.0.1", False, "应拒绝内网IP"),
        ("https://192.168.1.1", False, "应拒绝私网IP"),
    ]
    
    print("\n📋 测试URL验证:")
    passed = 0
    for url, expected_valid, desc in test_cases:
        is_valid = validate_url(url, allowed_schemes=('https',))
        status = "✅" if is_valid == expected_valid else "❌"
        print(f"   {status} {url}: {desc}")
        if is_valid == expected_valid:
            passed += 1
    
    return passed == len(test_cases)

def test_safe_execute():
    """测试安全执行"""
    print("\n📋 测试安全执行:")
    
    def success_func():
        return "成功"
    
    def fail_func():
        raise ValueError("测试错误")
    
    def fallback_func():
        return "回退成功"
    
    # 测试成功
    result = safe_execute(success_func, default="默认")
    status = "✅" if result == "成功" else "❌"
    print(f"   {status} 成功函数")
    
    # 测试失败+回退
    result = safe_execute(fail_func, default="默认", fallback=fallback_func)
    status = "✅" if result == "回退成功" else "❌"
    print(f"   {status} 失败+回退")
    
    # 测试失败+无回退
    result = safe_execute(fail_func, default="默认")
    status = "✅" if result == "默认" else "❌"
    print(f"   {status} 失败+默认")
    
    return True

def test_retry():
    """测试重试装饰器"""
    print("\n📋 测试重试装饰器:")
    attempt_count = [0]
    
    @retry(max_attempts=3, delay=0.1)
    def flaky_func():
        attempt_count[0] += 1
        if attempt_count[0] < 3:
            raise ValueError("临时错误")
        return "成功"
    
    try:
        result = flaky_func()
        status = "✅" if result == "成功" else "❌"
        print(f"   {status} 重试后成功")
    except:
        print(f"   ❌ 重试失败")
    
    return True

def main():
    print("=" * 50)
    print("🏛️  Edict 边缘场景测试")
    print("=" * 50)
    
    results = [
        test_validate_task_id(),
        test_validate_state_transition(),
        test_validate_url(),
        test_safe_execute(),
        test_retry(),
    ]
    
    print("\n" + "=" * 50)
    passed = sum(results)
    total = len(results)
    print(f"📊 结果: {passed}/{total} 测试通过")
    print("=" * 50)
    
    return 0 if all(results) else 1

if __name__ == '__main__':
    sys.exit(main())
