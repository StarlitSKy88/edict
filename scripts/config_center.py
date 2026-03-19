#!/usr/bin/env python3
"""
配置中心 - 集中管理所有配置
支持热更新、版本控制、环境隔离
"""
import os
import sys
import json
import logging
import time
import threading
from typing import Any, Dict, Optional
from pathlib import Path
from dataclasses import dataclass, field, asdict
from enum import Enum

BASE = Path(__file__).parent.parent
sys.path.insert(0, str(BASE / 'scripts'))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [Config] %(levelname)s: %(message)s',
    datefmt='%H:%M:%S'
)
log = logging.getLogger('config')

# ==================== 常量 ====================
class ConfigEnv(Enum):
    """环境"""
    DEVELOPMENT = "development"
    TEST = "test"
    STAGING = "staging"
    PRODUCTION = "production"


# ==================== 配置项 ====================
@dataclass
class ConfigItem:
    """配置项"""
    key: str
    value: Any
    env: str = "default"  # 环境标识
    version: int = 1
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    description: str = ""
    source: str = "manual"  # 来源: manual, env, file


@dataclass
class ConfigSnapshot:
    """配置快照"""
    version: int
    config: Dict[str, Any]
    created_at: float
    description: str = ""


# ==================== 配置中心 ====================
class ConfigCenter:
    """配置中心"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init()
        return cls._instance
    
    def _init(self):
        """初始化"""
        self._configs: Dict[str, ConfigItem] = {}
        self._snapshots: list = []
        self._lock = threading.RLock()
        self._version = 0
        self._env = ConfigEnv.DEVELOPMENT.value
        
        # 加载默认配置
        self._load_defaults()
        
        # 加载环境变量
        self._load_env_vars()
        
        log.info(f"配置中心初始化完成 (环境: {self._env})")
    
    def _load_defaults(self):
        """加载默认配置"""
        defaults = {
            # Agent配置
            "agent.default_timeout": 30,
            "agent.max_retries": 3,
            "agent.heartbeat_interval": 30,
            
            # 飞书配置
            "feishu.app_id": "",
            "feishu.app_secret": "",
            "feishu.verification_token": "",
            
            # Redis配置
            "redis.host": "localhost",
            "redis.port": 6379,
            "redis.db": 0,
            "redis.password": "",
            
            # 消息队列
            "queue.max_retries": 3,
            "queue.timeout": 60,
            "queue.dlq_enabled": True,
            
            # 熔断器
            "circuit.failure_threshold": 5,
            "circuit.success_threshold": 3,
            "circuit.timeout": 60,
            
            # 报告
            "report.daily_time": "18:00",
            "report.weekly_time": "17:00",
            "report.weekly_day": "friday",
            "report.monthly_day": 1,
            
            # 日志
            "log.level": "INFO",
            "log.format": "%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        }
        
        for key, value in defaults.items():
            self._configs[key] = ConfigItem(
                key=key,
                value=value,
                source="default"
            )
    
    def _load_env_vars(self):
        """从环境变量加载配置"""
        env_prefix = "EDICT_"
        
        for key, value in os.environ.items():
            if key.startswith(env_prefix):
                config_key = key[len(env_prefix):].lower().replace("_", ".")
                self.set(config_key, value, source="env")
    
    # ---- 基础操作 ----
    def get(self, key: str, default: Any = None, env: str = None) -> Any:
        """获取配置"""
        # 优先获取环境特定配置
        env = env or self._env
        env_key = f"{key}:{env}"
        
        with self._lock:
            if env_key in self._configs:
                return self._configs[env_key].value
            
            if key in self._configs:
                return self._configs[key].value
        
        return default
    
    def set(
        self,
        key: str,
        value: Any,
        source: str = "manual",
        description: str = ""
    ) -> bool:
        """设置配置"""
        with self._lock:
            old_value = None
            if key in self._configs:
                old_value = self._configs[key].value
            
            self._configs[key] = ConfigItem(
                key=key,
                value=value,
                source=source,
                description=description,
                version=self._configs[key].version + 1 if key in self._configs else 1
            )
            
            self._version += 1
            
            if old_value != value:
                log.info(f"配置更新: {key} = {value}")
            
            return True
    
    def delete(self, key: str) -> bool:
        """删除配置"""
        with self._lock:
            if key in self._configs:
                del self._configs[key]
                self._version += 1
                log.info(f"配置删除: {key}")
                return True
            return False
    
    # ---- 批量操作 ----
    def get_all(self, prefix: str = None) -> Dict[str, Any]:
        """获取所有配置"""
        with self._lock:
            result = {}
            for key, item in self._configs.items():
                if prefix is None or key.startswith(prefix):
                    result[key] = item.value
            return result
    
    def set_many(self, configs: Dict[str, Any], source: str = "manual") -> bool:
        """批量设置"""
        for key, value in configs.items():
            self.set(key, value, source)
        return True
    
    # ---- 快照管理 ----
    def snapshot(self, description: str = "") -> int:
        """创建快照"""
        with self._lock:
            version = len(self._snapshots) + 1
            
            snapshot = ConfigSnapshot(
                version=version,
                config={k: v.value for k, v in self._configs.items()},
                created_at=time.time(),
                description=description
            )
            
            self._snapshots.append(snapshot)
            
            log.info(f"配置快照创建: v{version}")
            return version
    
    def restore(self, version: int) -> bool:
        """恢复快照"""
        with self._lock:
            if version < 1 or version > len(self._snapshots):
                return False
            
            snapshot = self._snapshots[version - 1]
            
            self._configs.clear()
            for key, value in snapshot.config.items():
                self._configs[key] = ConfigItem(
                    key=key,
                    value=value,
                    source="snapshot"
                )
            
            log.info(f"配置恢复: v{version}")
            return True
    
    def list_snapshots(self) -> list:
        """列出快照"""
        return [
            {
                "version": s.version,
                "created_at": s.created_at,
                "description": s.description,
                "config_count": len(s.config)
            }
            for s in self._snapshots
        ]
    
    # ---- 环境管理 ----
    def set_env(self, env: ConfigEnv):
        """设置环境"""
        self._env = env.value
        log.info(f"切换环境: {self._env}")
    
    def get_env(self) -> str:
        """获取当前环境"""
        return self._env
    
    # ---- 文件持久化 ----
    def save_to_file(self, path: str = None):
        """保存到文件"""
        path = path or f"config/edict_config_{self._env}.json"
        
        with self._lock:
            data = {
                "version": self._version,
                "env": self._env,
                "configs": {
                    k: {
                        "value": v.value,
                        "version": v.version,
                        "source": v.source,
                        "description": v.description
                    }
                    for k, v in self._configs.items()
                }
            }
        
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        log.info(f"配置已保存: {path}")
    
    def load_from_file(self, path: str = None) -> bool:
        """从文件加载"""
        path = path or f"config/edict_config_{self._env}.json"
        
        if not os.path.exists(path):
            log.warning(f"配置文件不存在: {path}")
            return False
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            with self._lock:
                self._configs.clear()
                
                for key, item in data.get("configs", {}).items():
                    self._configs[key] = ConfigItem(
                        key=key,
                        value=item["value"],
                        version=item.get("version", 1),
                        source=item.get("source", "file"),
                        description=item.get("description", "")
                    )
                
                self._version = data.get("version", 0)
            
            log.info(f"配置已加载: {path}")
            return True
            
        except Exception as e:
            log.error(f"加载配置失败: {e}")
            return False
    
    # ---- 热更新回调 ----
    def watch(self, key: str, callback):
        """监听配置变化 (简化实现)"""
        # 实际生产环境可使用Redis Pub/Sub
        pass


# ==================== 便捷函数 ====================
def get_config(key: str, default: Any = None) -> Any:
    """获取配置"""
    return ConfigCenter().get(key, default)


def set_config(key: str, value: Any) -> bool:
    """设置配置"""
    return ConfigCenter().set(key, value)


# ==================== CLI ====================
def main():
    import argparse
    parser = argparse.ArgumentParser(description='配置中心')
    parser.add_argument('--get', help='获取配置')
    parser.add_argument('--set', nargs=2, metavar=("KEY", "VALUE"), help='设置配置')
    parser.add_argument('--list', action='store_true', help='列出所有配置')
    parser.add_argument('--prefix', help='配置前缀过滤')
    parser.add_argument('--save', action='store_true', help='保存到文件')
    parser.add_argument('--load', action='store_true', help='从文件加载')
    parser.add_argument('--snapshot', action='store_true', help='创建快照')
    parser.add_argument('--restore', type=int, help='恢复快照')
    parser.add_argument('--snapshots', action='store_true', help='列出快照')
    parser.add_argument('--env', choices=['development', 'test', 'staging', 'production'], help='设置环境')
    
    args = parser.parse_args()
    
    center = ConfigCenter()
    
    if args.get:
        value = center.get(args.get)
        print(f"{args.get} = {value}")
    
    elif args.set:
        center.set(args.set[0], args.set[1])
        print(f"已设置: {args.set[0]} = {args.set[1]}")
    
    elif args.list:
        import json
        configs = center.get_all(args.prefix)
        print(json.dumps(configs, indent=2, ensure_ascii=False))
    
    elif args.save:
        center.save_to_file()
        print("配置已保存")
    
    elif args.load:
        center.load_from_file()
        print("配置已加载")
    
    elif args.snapshot:
        version = center.snapshot(args.snapshot or "manual")
        print(f"快照创建: v{version}")
    
    elif args.restore:
        if center.restore(args.restore):
            print(f"已恢复: v{args.restore}")
        else:
            print("恢复失败")
    
    elif args.snapshots:
        import json
        print(json.dumps(center.list_snapshots(), indent=2))
    
    elif args.env:
        center.set_env(ConfigEnv[args.env.upper()])
        print(f"环境切换: {args.env}")


if __name__ == '__main__':
    main()
