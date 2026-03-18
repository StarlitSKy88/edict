#!/usr/bin/env python3
"""
Edict 插件系统 - 扩展性框架
功能: 插件注册、动态加载、热更新、钩子机制
"""
import os
import sys
import json
import importlib
import logging
from pathlib import Path
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional, Callable, Dict
from enum import Enum

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(name)s] %(message)s', datefmt='%H:%M:%S')
log = logging.getLogger('plugin')

BASE = Path(__file__).parent.parent
PLUGINS_DIR = BASE / 'plugins'

# ==================== 插件基类 ====================
class PluginHook(Enum):
    """插件钩子"""
    ON_START = "on_start"
    ON_STOP = "on_stop"
    ON_MESSAGE = "on_message"
    ON_TASK_CREATE = "on_task_create"
    ON_TASK_COMPLETE = "on_task_complete"
    ON_ERROR = "on_error"
    BEFORE_AGENT_CALL = "before_agent_call"
    AFTER_AGENT_CALL = "after_agent_call"

@dataclass
class PluginMetadata:
    """插件元数据"""
    name: str
    version: str
    author: str = "Unknown"
    description: str = ""
    dependencies: list = field(default_factory=list)
    hooks: list = field(default_factory=list)

class Plugin(ABC):
    """插件基类"""
    
    metadata: PluginMetadata
    
    @abstractmethod
    def initialize(self, context: dict) -> bool:
        """初始化插件"""
        pass
    
    @abstractmethod
    def execute(self, hook: PluginHook, **kwargs) -> Any:
        """执行插件"""
        pass
    
    def shutdown(self):
        """关闭插件"""
        pass

# ==================== 插件管理器 ====================
class PluginManager:
    """插件管理器"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self.plugins: Dict[str, Plugin] = {}
        self.hooks: Dict[PluginHook, list] = {h: [] for h in PluginHook}
        self.context: dict = {}
        self._initialized = True
        
        log.info("插件管理器初始化完成")
    
    def register_plugin(self, plugin: Plugin) -> bool:
        """注册插件"""
        name = plugin.metadata.name
        
        # 检查依赖
        for dep in plugin.metadata.dependencies:
            if dep not in self.plugins:
                log.error(f"插件 {name} 依赖 {dep} 未安装")
                return False
        
        # 初始化
        if plugin.initialize(self.context):
            self.plugins[name] = plugin
            
            # 注册钩子
            for hook in plugin.metadata.hooks:
                if hook in self.hooks:
                    self.hooks[hook].append(plugin)
            
            log.info(f"插件注册成功: {name}")
            return True
        
        log.error(f"插件初始化失败: {name}")
        return False
    
    def unregister_plugin(self, name: str) -> bool:
        """卸载插件"""
        if name not in self.plugins:
            return False
        
        plugin = self.plugins[name]
        plugin.shutdown()
        
        # 移除钩子
        for hook_list in self.hooks.values():
            if plugin in hook_list:
                hook_list.remove(plugin)
        
        del self.plugins[name]
        log.info(f"插件已卸载: {name}")
        return True
    
    def execute_hook(self, hook: PluginHook, **kwargs) -> list:
        """执行钩子"""
        results = []
        
        for plugin in self.hooks.get(hook, []):
            try:
                result = plugin.execute(hook, **kwargs)
                results.append({'plugin': plugin.metadata.name, 'result': result})
            except Exception as e:
                log.error(f"插件 {plugin.metadata.name} 执行失败: {e}")
        
        return results
    
    def get_plugin(self, name: str) -> Optional[Plugin]:
        """获取插件"""
        return self.plugins.get(name)
    
    def list_plugins(self) -> list:
        """列出所有插件"""
        return [
            {
                'name': p.metadata.name,
                'version': p.metadata.version,
                'author': p.metadata.author,
                'hooks': [h.value for h in p.metadata.hooks]
            }
            for p in self.plugins.values()
        ]

# ==================== 插件加载器 ====================
class PluginLoader:
    """插件加载器"""
    
    @staticmethod
    def load_from_directory(directory: Path = None) -> int:
        """从目录加载插件"""
        directory = directory or PLUGINS_DIR
        
        if not directory.exists():
            directory.mkdir(parents=True, exist_ok=True)
            return 0
        
        loaded = 0
        manager = PluginManager()
        
        for plugin_file in directory.glob('*/plugin.py'):
            try:
                # 动态导入
                plugin_dir = plugin_file.parent
                sys.path.insert(0, str(plugin_dir))
                
                module = importlib.import_module('plugin')
                
                # 获取插件类
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if isinstance(attr, type) and issubclass(attr, Plugin) and attr != Plugin:
                        plugin = attr()
                        if manager.register_plugin(plugin):
                            loaded += 1
                        break
                
            except Exception as e:
                log.error(f"加载插件失败 {plugin_file}: {e}")
        
        return loaded
    
    @staticmethod
    def create_plugin_scaffold(name: str, directory: Path = None):
        """创建插件脚手架"""
        directory = directory or PLUGINS_DIR
        plugin_dir = directory / name
        plugin_dir.mkdir(parents=True, exist_ok=True)
        
        # 创建 __init__.py
        (plugin_dir / '__init__.py').write_text('')
        
        # 创建 plugin.py
        plugin_code = f'''"""Edict 插件: {name}"""
from scripts.plugin_system import Plugin, PluginMetadata, PluginHook

class {name.replace("-", "_").title().replace("_", "")}Plugin(Plugin):
    """{name} 插件"""
    
    metadata = PluginMetadata(
        name="{name}",
        version="1.0.0",
        author="Edict Team",
        description="{name} 插件描述",
        hooks=[PluginHook.ON_START, PluginHook.ON_MESSAGE]
    )
    
    def initialize(self, context: dict) -> bool:
        """初始化"""
        log.info("插件 {name} 初始化")
        return True
    
    def execute(self, hook: PluginHook, **kwargs) -> Any:
        """执行"""
        if hook == PluginHook.ON_MESSAGE:
            message = kwargs.get("message", "")
            # 处理消息
            return {{"processed": True}}
        return None
    
    def shutdown(self):
        """关闭"""
        log.info("插件 {name} 关闭")
'''
        
        (plugin_dir / 'plugin.py').write_text(plugin_code)
        log.info(f"插件脚手架已创建: {plugin_dir}")

# ==================== 钩子装饰器 ====================
def hook(hook_type: PluginHook):
    """钩子装饰器"""
    def decorator(func: Callable) -> Callable:
        func._hook_type = hook_type
        return func
    return decorator

# ==================== 内置插件示例 ====================
class LoggingPlugin(Plugin):
    """日志插件"""
    
    metadata = PluginMetadata(
        name="logging",
        version="1.0.0",
        author="Edict",
        description="统一日志记录",
        hooks=[PluginHook.ON_MESSAGE, PluginHook.ON_ERROR]
    )
    
    def initialize(self, context: dict) -> bool:
        log.info("日志插件初始化")
        return True
    
    def execute(self, hook: PluginHook, **kwargs) -> Any:
        if hook == PluginHook.ON_MESSAGE:
            log.info(f"消息: {kwargs.get('message', '')[:50]}")
        elif hook == PluginHook.ON_ERROR:
            log.error(f"错误: {kwargs.get('error', '')}")

# ==================== CLI ====================
def main():
    import argparse
    parser = argparse.ArgumentParser(description='Edict插件系统')
    parser.add_argument('--list', action='store_true', help='列出插件')
    parser.add_argument('--load', action='store_true', help='加载插件')
    parser.add_argument('--create', help='创建插件脚手架')
    
    args = parser.parse_args()
    
    manager = PluginManager()
    
    # 注册内置插件
    manager.register_plugin(LoggingPlugin())
    
    if args.list:
        plugins = manager.list_plugins()
        print(f"已加载 {len(plugins)} 个插件:")
        for p in plugins:
            print(f"  - {p['name']} v{p['version']}")
    
    if args.load:
        loaded = PluginLoader.load_from_directory()
        print(f"加载了 {loaded} 个插件")
    
    if args.create:
        PluginLoader.create_plugin_scaffold(args.create)
        print(f"已创建插件: {args.create}")

if __name__ == '__main__':
    main()
