#!/usr/bin/env python3
"""
看板任务更新工具 - 单元测试
"""
import json
import pathlib
import sys
import tempfile
import unittest

# 添加项目路径
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / 'scripts'))

# 直接导入模块文件
import importlib.util
spec = importlib.util.spec_from_file_location(
    "kanban_update", 
    str(pathlib.Path(__file__).parent.parent / 'scripts' / 'kanban_update.py')
)
kanban_update = importlib.util.module_from_spec(spec)
spec.loader.exec_module(kanban_update)

validate_task_id = kanban_update.validate_task_id
validate_state_transition = kanban_update.validate_state_transition


class TestKanbanUpdate(unittest.TestCase):
    """看板更新测试"""
    
    def setUp(self):
        """测试前准备"""
        self.temp_dir = tempfile.mkdtemp()
        self.tasks_file = pathlib.Path(self.temp_dir) / 'tasks.json'
        self.tasks_file.write_text(json.dumps({'tasks': [], 'stats': {}}))
    
    def test_validate_task_id_valid(self):
        """测试有效的任务ID"""
        valid_ids = [
            'JJC-20260322-001',
            'TEST-20250101-999',
            'ABC-20241231-100',
        ]
        for task_id in valid_ids:
            is_valid, _ = validate_task_id(task_id)
            self.assertTrue(is_valid, f"应该通过: {task_id}")
    
    def test_validate_task_id_invalid(self):
        """测试无效的任务ID"""
        invalid_ids = [
            '',  # 空字符串
            'invalid',  # 无格式
            'jjc-20260322-001',  # 小写
            'JJC-2026-01-001',  # 错误日期格式
            'JJC-20260322',  # 缺少序号
        ]
        for task_id in invalid_ids:
            is_valid, _ = validate_task_id(task_id)
            self.assertFalse(is_valid, f"应该失败: {task_id}")
    
    def test_validate_state_transition_valid(self):
        """测试有效的状态转换"""
        valid_transitions = [
            ('Pending', 'Doing'),
            ('Doing', 'Review'),
            ('Review', 'Done'),
            ('Doing', 'Blocked'),
            ('Pending', 'Cancelled'),
        ]
        for from_state, to_state in valid_transitions:
            is_valid = validate_state_transition(from_state, to_state)
            self.assertTrue(is_valid, f"应该通过: {from_state} -> {to_state}")
    
    def test_validate_state_transition_invalid(self):
        """测试无效的状态转换"""
        invalid_transitions = [
            ('Done', 'Doing'),  # 已完成不能逆转
            ('Cancelled', 'Doing'),  # 已取消不能恢复
            ('Pending', 'Done'),  # Pending 不能直接到 Done
        ]
        for from_state, to_state in invalid_transitions:
            is_valid = validate_state_transition(from_state, to_state)
            self.assertFalse(is_valid, f"应该失败: {from_state} -> {to_state}")


if __name__ == '__main__':
    unittest.main()
