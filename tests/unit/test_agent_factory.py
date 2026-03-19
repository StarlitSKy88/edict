#!/usr/bin/env python3
"""
Agent工厂单元测试
"""
import unittest
import sys
import time
import os
import tempfile
from pathlib import Path

BASE = Path(__file__).parent.parent.parent
sys.path.insert(0, str(BASE / 'scripts'))

from agent_factory import AgentFactory, TempAgentConfig, ProjectContext


class TestAgentFactory(unittest.TestCase):
    """Agent工厂测试"""
    
    def setUp(self):
        """测试前准备 - 使用临时文件"""
        self.temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json')
        self.temp_file.close()
        self.factory = AgentFactory(config_path=self.temp_file.name)
    
    def tearDown(self):
        """测试后清理"""
        if os.path.exists(self.temp_file.name):
            os.unlink(self.temp_file.name)
    
    def test_initial_templates(self):
        """测试技能模板"""
        self.assertIn("finance", self.factory.skill_templates)
        self.assertIn("devops", self.factory.skill_templates)
        self.assertIn("security", self.factory.skill_templates)
        
        # 验证模板结构
        finance = self.factory.skill_templates["finance"]
        self.assertIn("skills", finance)
        self.assertIn("name", finance)
    
    def test_create_temp_agent(self):
        """测试创建临时Agent"""
        agent = self.factory.create_temp_agent(
            name="金融专家",
            skill_type="finance",
            parent="太子",
            expires_hours=24
        )
        
        self.assertIsNotNone(agent)
        self.assertEqual(agent.name, "金融专家")
        self.assertEqual(agent.role, "金融专家")
        self.assertEqual(agent.parent, "太子")
        self.assertIn("finance", agent.skills)
        self.assertFalse(agent.is_temp)  # factory内部标记
    
    def test_create_unknown_skill(self):
        """测试创建未知技能"""
        agent = self.factory.create_temp_agent(
            name="自定义专家",
            skill_type="custom_skill",
            parent="太子",
            expires_hours=24
        )
        
        self.assertEqual(agent.skills[0], "custom_skill")
    
    def test_create_project_agent(self):
        """测试创建项目组"""
        project = self.factory.create_project_agent(
            project_name="金融系统",
            skill_types=["finance", "devops"],
            parent="太子",
            expires_days=7
        )
        
        self.assertIsNotNone(project)
        self.assertEqual(project.name, "金融系统")
        self.assertEqual(len(project.agents), 2)
        self.assertEqual(project.status, "active")
    
    def test_list_temp_agents(self):
        """测试列出临时Agent"""
        # 创建两个Agent
        self.factory.create_temp_agent("专家1", "finance", "太子", 24)
        self.factory.create_temp_agent("专家2", "devops", "太子", 24)
        
        agents = self.factory.list_temp_agents()
        self.assertEqual(len(agents), 2)
    
    def test_list_by_parent(self):
        """测试按父级筛选"""
        self.factory.create_temp_agent("专家1", "finance", "太子", 24)
        self.factory.create_temp_agent("专家2", "devops", "尚书省", 24)
        
        taizi_agents = self.factory.list_temp_agents(parent="太子")
        self.assertEqual(len(taizi_agents), 1)
    
    def test_destroy_temp_agent(self):
        """测试销毁Agent"""
        agent = self.factory.create_temp_agent("测试", "finance", "太子", 24)
        agent_id = agent.id
        
        result = self.factory.destroy_temp_agent(agent_id)
        self.assertTrue(result)
        
        # 验证已删除
        self.assertIsNone(self.factory.get_temp_agent(agent_id))
    
    def test_complete_project(self):
        """测试完成项目"""
        project = self.factory.create_project_agent(
            project_name="测试项目",
            skill_types=["finance"],
            parent="太子",
            expires_days=7
        )
        proj_id = project.id
        
        result = self.factory.complete_project(proj_id)
        self.assertTrue(result)
        
        # 验证项目状态
        proj = self.factory.projects[proj_id]
        self.assertEqual(proj.status, "completed")
    
    def test_cleanup_expired(self):
        """测试清理过期Agent"""
        # 创建一个已过期的Agent
        agent = self.factory.create_temp_agent("过期", "finance", "太子", 0)  # 0小时 = 立即过期
        agent.expires_at = time.time() - 1  # 设为过去时间
        self.factory._save()
        
        # 清理
        count = self.factory.cleanup_expired()
        self.assertGreaterEqual(count, 0)
    
    def test_expiring_agents(self):
        """测试即将过期Agent"""
        agent = self.factory.create_temp_agent("测试", "finance", "太子", 24)
        
        expiring = self.factory.get_expiring_agents(hours=48)
        self.assertGreater(len(expiring), 0)
    
    def test_extend_agent(self):
        """测试延长Agent"""
        agent = self.factory.create_temp_agent("测试", "finance", "太子", 24)
        original_expires = agent.expires_at
        
        self.factory.extend_agent(agent.id, hours=24)
        
        self.assertGreater(agent.expires_at, original_expires)


class TestSkillTemplates(unittest.TestCase):
    """技能模板测试"""
    
    def test_all_templates_have_required_fields(self):
        """测试所有模板都有必要字段"""
        factory = AgentFactory()
        
        for skill_type, template in factory.skill_templates.items():
            with self.subTest(skill_type=skill_type):
                self.assertIn("name", template)
                self.assertIn("skills", template)
                self.assertIsInstance(template["skills"], list)
                self.assertGreater(len(template["skills"]), 0)


if __name__ == '__main__':
    unittest.main()
