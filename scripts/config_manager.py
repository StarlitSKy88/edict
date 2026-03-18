#!/usr/bin/env python3
"""
Edict 配置管理系统 - 扩展性
功能: 配置加载、多环境支持、热更新、配置验证
"""
import os
import sys
import json
import logging
from pathlib import Path
from typing import Any, Optional, Dict
from dataclasses import dataclass, field, asdict
from enum import Enum

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(name)s] %(message)s', datefmt='%H:%M:%S')
log = logging.getLogger('config')

BASE = Path(__file__).parent.parent
CONFIG_DIR = BASE / 'config'

# ==================== 环境 ====================
class Env(Enum):
    DEVELOPMENT = "development"
    TESTING = "testing"
    PRODUCTION = "production"

@dataclass
class ConfigSchema:
    """配置Schema"""
    name: str
    type: type
    default: Any
    description: str = ""
    required: bool = False

# ==================== 配置管理器 ====================
class ConfigManager:
    """配置管理器"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self.config: Dict[str, Any] = {}
        self.env = Env(os.getenv('EDICT_ENV', 'development'))
        self._initialized = True
        
        # 加载配置
        self._load_config()
        
        log.info(f"配置管理器初始化完成 (环境: {self.env.value})")
    
    def _load_config(self):
        """加载配置"""
        # 默认配置
        default_file = CONFIG_DIR / 'default.json'
        if default_file.exists():
            self.config.update(json.loads(default_file.read_text()))
        
        # 环境配置
        env_file = CONFIG_DIR / f'{self.env.value}.json'
        if env_file.exists():
            env_config = json.loads(env_file.read_text())
            self._deep_merge(self.config, env_config)
        
        # 环境变量覆盖
        self._load_env_vars()
    
    def _deep_merge(self, base: dict, override: dict):
        """深度合并"""
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value
    
    def _load_env_vars(self):
        """加载环境变量"""
        prefix = "EDICT_"
        for key, value in os.environ.items():
            if key.startswith(prefix):
                config_key = key[len(prefix):].lower()
                self.config[config_key] = value
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置"""
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
                if value is None:
                    return default
            else:
                return default
        
        return value
    
    def set(self, key: str, value: Any):
        """设置配置"""
        keys = key.split('.')
        target = self.config
        
        for k in keys[:-1]:
            if k not in target:
                target[k] = {}
            target = target[k]
        
        target[keys[-1]] = value
        log.info(f"配置已更新: {key}")
    
    def save(self):
        """保存配置"""
        config_file = CONFIG_DIR / f'{self.env.value}.json'
        config_file.write_text(json.dumps(self.config, indent=2, ensure_ascii=False))
        log.info(f"配置已保存: {config_file}")
    
    def validate(self, schema: list[ConfigSchema]) -> tuple[bool, list]:
        """验证配置"""
        errors = []
        
        for field in schema:
            value = self.get(field.name)
            
            if field.required and value is None:
                errors.append(f"必填字段缺失: {field.name}")
            elif value is not None and not isinstance(value, field.type):
                errors.append(f"类型错误: {field.name}, 期望 {field.type}, 实际 {type(value)}")
        
        return len(errors) == 0, errors

# ==================== 配置装饰器 ====================
def config(key: str, default: Any = None):
    """配置装饰器"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            config_manager = ConfigManager()
            value = config_manager.get(key, default)
            return func(value) if callable(func) else value
        return wrapper
    return decorator

# ==================== CLI ====================
def main():
    import argparse
    parser = argparse.ArgumentParser(description='Edict配置管理')
    parser.add_argument('--get', help='获取配置')
    parser.add_argument('--set', nargs=2, help='设置配置 key value')
    parser.add_argument('--list', action='store_true', help='列出所有配置')
    parser.add_argument('--validate', action='store_true', help='验证配置')
    
    args = parser.parse_args()
    
    manager = ConfigManager()
    
    if args.get:
        print(manager.get(args.get))
    
    elif args.set:
        key, value = args.set
        # 尝试转换为适当类型
        if value.isdigit():
            value = int(value)
        elif value.lower() in ('true', 'false'):
            value = value.lower() == 'true'
        
        manager.set(key, value)
        manager.save()
    
    elif args.list:
        print(json.dumps(manager.config, indent=2, ensure_ascii=False))

if __name__ == '__main__':
    main()
