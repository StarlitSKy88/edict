#!/usr/bin/env python3
"""
LLM Gateway - 统一 LLM 服务层
=====================
功能:
- 统一 API Key 配置（一次配置，所有 Agent 共享）
- 多模型支持（不同 Agent 可用不同模型）
- 快速切换（API Key / 模型热更新）
- 多 Provider 适配（OpenRouter, OpenAI, Anthropic）

使用方式:
  from llm_gateway import LLMGateway
  
  llm = LLMGateway()
  # 获取 Agent 应使用的模型
  model = llm.get_agent_model("gongbu")
  # 获取 API Key
  api_key = llm.get_api_key("openrouter")
"""
import json
import os
import re
import pathlib
import threading
import time
import logging
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field
from functools import lru_cache

logging.basicConfig(level=logging.INFO, format='%(asctime)s [llm_gateway] %(message)s')
log = logging.getLogger('llm_gateway')

# 项目根目录
PROJECT_ROOT = pathlib.Path(__file__).parent.parent
CONFIG_FILE = PROJECT_ROOT / 'config' / 'llm_config.yaml'
DATA_DIR = PROJECT_ROOT / 'data'


@dataclass
class ModelInfo:
    """模型信息"""
    id: str
    name: str
    provider: str
    price: str = "未知"
    context_window: int = 4096
    enabled: bool = True


@dataclass
class LLMConfig:
    """LLM 配置"""
    default_provider: str = "openrouter"
    default_model: str = "deepseek/deepseek-chat"
    api_keys: Dict[str, str] = field(default_factory=dict)
    agent_models: Dict[str, str] = field(default_factory=dict)
    available_models: List[Dict] = field(default_factory=list)


class LLMGateway:
    """
    统一 LLM 服务入口
    
    示例:
        llm = LLMGateway()
        
        # 获取某个 Agent 应该使用的模型
        model = llm.get_agent_model("gongbu")
        # 如果 Agent 没有单独配置，使用全局默认
        
        # 获取某个 Provider 的 API Key
        api_key = llm.get_api_key("openrouter")
        
        # 切换全局默认模型
        llm.set_default_model("qwen/qwen-2.5-7b-instruct")
        
        # 切换单个 Agent 的模型
        llm.set_agent_model("gongbu", "anthropic/claude-sonnet-4-6")
        
        # 切换 API Key
        llm.set_api_key("openrouter", "sk-xxx")
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """单例模式"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._config: Optional[LLMConfig] = None
        self._models_cache: List[ModelInfo] = []
        self._models_cache_time: float = 0
        self._cache_lock = threading.Lock()
        self._load_config()
    
    def _load_config(self):
        """加载配置文件"""
        try:
            import yaml
            if CONFIG_FILE.exists():
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f) or {}
            else:
                data = {}
        except ImportError:
            # 没有 yaml 模块时，使用 JSON 配置文件
            json_config = CONFIG_FILE.with_suffix('.json')
            if json_config.exists():
                with open(json_config, 'r', encoding='utf-8') as f:
                    data = json.load(f) or {}
            else:
                data = {}
            
            llm_data = data.get('llm', {})
            
            # 处理环境变量
            api_keys = {}
            for provider, key in llm_data.get('api_keys', {}).items():
                if isinstance(key, str) and key.startswith('${') and key.endswith('}'):
                    env_var = key[2:-1]
                    api_keys[provider] = os.environ.get(env_var, '')
                else:
                    api_keys[provider] = key
            
            self._config = LLMConfig(
                default_provider=llm_data.get('default_provider', 'openrouter'),
                default_model=llm_data.get('default_model', 'deepseek/deepseek-chat'),
                api_keys=api_keys,
                agent_models=llm_data.get('agent_models', {}),
                available_models=llm_data.get('available_models', []),
            )
            log.info(f"配置加载成功: 默认模型={self._config.default_model}")
        except Exception as e:
            log.warning(f"配置加载失败，使用默认配置: {e}")
            self._config = LLMConfig()
    
    def _save_config(self):
        """保存配置文件"""
        data = {}
        
        # 尝试读取现有配置
        try:
            import yaml
            if CONFIG_FILE.exists():
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f) or {}
        except ImportError:
            # 没有 yaml，使用 JSON
            json_config = CONFIG_FILE.with_suffix('.json')
            if json_config.exists():
                with open(json_config, 'r', encoding='utf-8') as f:
                    data = json.load(f) or {}
        
        # 更新配置
        if 'llm' not in data:
            data['llm'] = {}
        
        data['llm']['default_provider'] = self._config.default_provider
        data['llm']['default_model'] = self._config.default_model
        data['llm']['api_keys'] = self._config.api_keys
        data['llm']['agent_models'] = self._config.agent_models
        data['llm']['available_models'] = self._config.available_models
        
        # 尝试保存
        try:
            import yaml
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                yaml.dump(data, f, allow_unicode=True, default_flow_style=False)
        except ImportError:
            # 没有 yaml，保存为 JSON
            json_config = CONFIG_FILE.with_suffix('.json')
            with open(json_config, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        
        log.info("配置已保存")
        return True
    
    # ==================== 核心 API ====================
    
    def get_agent_model(self, agent_id: str) -> str:
        """
        获取 Agent 应当使用的模型
        
        Args:
            agent_id: Agent ID (如 "gongbu", "taizi", "hubu")
            
        Returns:
            模型 ID (如 "deepseek/deepseek-chat")
        """
        if not self._config:
            self._load_config()
        
        # 优先使用 Agent 专用配置
        if agent_id in self._config.agent_models:
            model = self._config.agent_models[agent_id]
            if model:
                return model
        
        # 否则使用全局默认
        return self._config.default_model
    
    def get_api_key(self, provider: str = None) -> str:
        """
        获取 API Key
        
        Args:
            provider: Provider 名称 (如 "openrouter", "openai")
                     如果为 None，返回默认 provider 的 key
                     
        Returns:
            API Key 字符串
        """
        if not self._config:
            self._load_config()
        
        if provider is None:
            provider = self._config.default_provider
        
        return self._config.api_keys.get(provider, '')
    
    def get_provider_for_model(self, model_id: str) -> str:
        """
        根据模型 ID 推断 Provider
        
        Args:
            model_id: 模型 ID
            
        Returns:
            Provider 名称
        """
        # 简单映射逻辑
        if '/' in model_id:
            # 格式 like "deepseek/deepseek-chat" -> provider = "deepseek"
            return model_id.split('/')[0]
        
        # 常见模型映射
        model_provider_map = {
            'gpt-4': 'openai',
            'gpt-3.5': 'openai',
            'claude': 'anthropic',
        }
        
        for prefix, provider in model_provider_map.items():
            if model_id.lower().startswith(prefix):
                return provider
        
        return self._config.default_provider
    
    def get_default_provider(self) -> str:
        """获取默认 Provider"""
        if not self._config:
            self._load_config()
        return self._config.default_provider
    
    def get_default_model(self) -> str:
        """获取默认模型"""
        if not self._config:
            self._load_config()
        return self._config.default_model
    
    # ==================== 切换 API ====================
    
    def set_default_model(self, model: str) -> bool:
        """设置全局默认模型"""
        if not self._config:
            self._load_config()
        self._config.default_model = model
        return self._save_config()
    
    def set_default_provider(self, provider: str) -> bool:
        """设置默认 Provider"""
        if not self._config:
            self._load_config()
        self._config.default_provider = provider
        return self._save_config()
    
    def set_agent_model(self, agent_id: str, model: str) -> bool:
        """
        设置单个 Agent 的模型
        
        Args:
            agent_id: Agent ID
            model: 模型 ID
            
        Returns:
            是否成功
        """
        if not self._config:
            self._load_config()
        
        if model:
            self._config.agent_models[agent_id] = model
        else:
            # 空模型表示使用全局默认
            self._config.agent_models.pop(agent_id, None)
        
        return self._save_config()
    
    def set_api_key(self, provider: str, api_key: str) -> bool:
        """
        设置 API Key
        
        Args:
            provider: Provider 名称
            api_key: API Key
        """
        if not self._config:
            self._load_config()
        
        self._config.api_keys[provider] = api_key
        return self._save_config()
    
    def clear_agent_model(self, agent_id: str) -> bool:
        """清除 Agent 的专用模型配置（使用全局默认）"""
        return self.set_agent_model(agent_id, '')
    
    # ==================== 模型列表 ====================
    
    def get_available_models(self, force_refresh: bool = False) -> List[ModelInfo]:
        """
        获取可用模型列表
        
        Args:
            force_refresh: 强制刷新缓存
        """
        with self._cache_lock:
            now = time.time()
            cache_ttl = 3600  # 1小时
            
            if (not force_refresh and 
                self._models_cache and 
                now - self._models_cache_time < cache_ttl):
                return self._models_cache
            
            # 如果手动配置了模型，直接返回
            if self._config.available_models:
                self._models_cache = [
                    ModelInfo(**m) if isinstance(m, dict) else m
                    for m in self._config.available_models
                ]
                self._models_cache_time = now
                return self._models_cache
            
            # 否则从 OpenRouter 获取
            self._models_cache = self._fetch_openrouter_models()
            self._models_cache_time = now
            return self._models_cache
    
    def _fetch_openrouter_models(self) -> List[ModelInfo]:
        """从 OpenRouter 获取免费模型列表"""
        try:
            import urllib.request
            import urllib.error
            
            url = "https://openrouter.ai/api/v1/models"
            req = urllib.request.Request(url, method='GET')
            req.add_header('Accept', 'application/json')
            
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())
            
            models = []
            for m in data.get('data', []):
                model_id = m.get('id', '')
                # 只保留免费或便宜的模型
                pricing = m.get('pricing', {})
                prompt_price = float(pricing.get('prompt', '0') or '0')
                
                if prompt_price == 0:  # 免费
                    models.append(ModelInfo(
                        id=model_id,
                        name=m.get('name', model_id),
                        provider='openrouter',
                        price='免费',
                        context_window=m.get('context_limit', 4096),
                    ))
            
            log.info(f"从 OpenRouter 获取到 {len(models)} 个免费模型")
            return models[:50]  # 限制数量
        except Exception as e:
            log.warning(f"获取模型列表失败: {e}")
            # 返回一些常见免费模型作为后备
            return [
                ModelInfo(id='deepseek/deepseek-chat', name='DeepSeek Chat', provider='openrouter', price='免费', context_window=64000),
                ModelInfo(id='qwen/qwen-2.5-7b-instruct', name='Qwen 2.5', provider='openrouter', price='免费', context_window=32000),
                ModelInfo(id='meta-llama/llama-3.1-8b-instruct', name='Llama 3.1', provider='openrouter', price='免费', context_window=128000),
                ModelInfo(id='mistralai/mistral-7b-instruct', name='Mistral 7B', provider='openrouter', context_window=32000),
            ]
    
    # ==================== 状态查询 ====================
    
    def get_status(self) -> Dict[str, Any]:
        """获取当前状态"""
        if not self._config:
            self._load_config()
        
        return {
            'default_provider': self._config.default_provider,
            'default_model': self._config.default_model,
            'api_keys_configured': {
                p: bool(k) for p, k in self._config.api_keys.items()
            },
            'agent_models': dict(self._config.agent_models),
            'models_count': len(self.get_available_models()),
        }
    
    def reload(self):
        """重新加载配置"""
        self._load_config()
        with self._cache_lock:
            self._models_cache_time = 0


# 便捷函数
def get_agent_model(agent_id: str) -> str:
    """获取 Agent 模型"""
    return LLMGateway().get_agent_model(agent_id)


def get_api_key(provider: str = None) -> str:
    """获取 API Key"""
    return LLMGateway().get_api_key(provider)


def set_agent_model(agent_id: str, model: str) -> bool:
    """设置 Agent 模型"""
    return LLMGateway().set_agent_model(agent_id, model)


def set_api_key(provider: str, api_key: str) -> bool:
    """设置 API Key"""
    return LLMGateway().set_api_key(provider, api_key)


def get_status() -> Dict[str, Any]:
    """获取状态"""
    return LLMGateway().get_status()


if __name__ == '__main__':
    # 测试
    llm = LLMGateway()
    print("=== LLM Gateway 测试 ===")
    print(f"状态: {json.dumps(llm.get_status(), indent=2, ensure_ascii=False)}")
    print(f"\nAgent 模型:")
    for agent in ['taizi', 'gongbu', 'hubu']:
        print(f"  {agent}: {llm.get_agent_model(agent)}")
