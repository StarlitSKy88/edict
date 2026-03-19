#!/usr/bin/env python3
"""
层级路由单元测试
"""
import unittest
import sys
from pathlib import Path

BASE = Path(__file__).parent.parent.parent
sys.path.insert(0, str(BASE / 'scripts'))

from hierarchical_router import HierarchicalRouter, AgentLevel, RouteRule


class TestHierarchicalRouter(unittest.TestCase):
    """层级路由测试"""
    
    def setUp(self):
        """测试前准备"""
        self.router = HierarchicalRouter()
    
    def test_initial_agents(self):
        """测试初始化Agent数量"""
        self.assertEqual(len(self.router.agents), 12)
        self.assertIn("太子", self.router.agents)
        self.assertIn("中书省", self.router.agents)
        self.assertIn("工部", self.router.agents)
    
    def test_pope_level(self):
        """测试太子层级"""
        taizi = self.router.agents["太子"]
        self.assertEqual(taizi.level, AgentLevel.CEO)
        self.assertIsNone(taizi.parent)
    
    def test_route_parent_to_child(self):
        """测试上级到下级路由"""
        result = self.router.route_message("太子", "中书省", "test")
        self.assertTrue(result["allowed"])
    
    def test_route_child_to_parent(self):
        """测试下级到上级路由"""
        result = self.router.route_message("工部", "太子", "test")
        self.assertTrue(result["allowed"])
    
    def test_route_peer_to_peer(self):
        """测试同级协作"""
        result = self.router.route_message("工部", "户部", "test")
        self.assertTrue(result["allowed"])
    
    def test_route_forbidden(self):
        """测试禁止跨级"""
        # 门下省(Manager) -> 工部(Manager)，虽然是不同parent但是同级别
        result = self.router.route_message("门下省", "工部", "test")
        self.assertTrue(result["allowed"])
    
    def test_add_agent(self):
        """测试添加Agent"""
        self.router.add_agent(
            agent_id="河北省",
            name="河北省",
            role="地方",
            parent="太子",
            level=AgentLevel.SPECIALIST
        )
        
        self.assertIn("河北省", self.router.agents)
        self.assertEqual(self.router.agents["河北省"].parent, "太子")
    
    def test_remove_agent(self):
        """测试移除Agent"""
        # 先添加
        self.router.add_agent("测试部", "测试部", "测试", "尚书省", AgentLevel.MANAGER)
        self.assertIn("测试部", self.router.agents)
        
        # 再移除
        self.router.remove_agent("测试部")
        self.assertNotIn("测试部", self.router.agents)
    
    def test_cannot_remove_pope(self):
        """测试不能删除太子"""
        result = self.router.remove_agent("太子")
        self.assertFalse(result)
    
    def test_get_team(self):
        """测试获取团队"""
        team = self.router.get_team("尚书省")
        self.assertIn("工部", team)
        self.assertIn("户部", team)
        self.assertIn("兵部", team)
    
    def test_get_parent_chain(self):
        """测试获取父级链"""
        chain = self.router.get_parent_chain("工部")
        self.assertIn("尚书省", chain)
        self.assertIn("太子", chain)
    
    def test_statistics(self):
        """测试统计信息"""
        stats = self.router.get_statistics()
        self.assertEqual(stats["total"], 12)
        self.assertIn("CEO", stats["by_level"])


class TestRouteRule(unittest.TestCase):
    """路由规则测试"""
    
    def test_route_rule_creation(self):
        """测试路由规则创建"""
        rule = RouteRule("from", "to", True, "测试原因")
        self.assertEqual(rule.from_agent, "from")
        self.assertEqual(rule.to_agent, "to")
        self.assertTrue(rule.allowed)
        self.assertEqual(rule.reason, "测试原因")


if __name__ == '__main__':
    unittest.main()
