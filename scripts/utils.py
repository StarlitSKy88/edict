#!/usr/bin/env python3
"""
三省六部 · 公共工具函数
避免 read_json / now_iso 等基础函数在多个脚本中重复定义
"""
import json
import pathlib
import datetime
import time
import logging
from typing import Any, Optional, Callable
from functools import wraps

logger = logging.getLogger('edict-utils')


def read_json(path, default=None):
    """安全读取 JSON 文件，失败返回 default"""
    try:
        return json.loads(pathlib.Path(path).read_text())
    except Exception:
        return default if default is not None else {}


def write_json(path, data, indent=2):
    """安全写入 JSON 文件"""
    p = pathlib.Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=indent))
    return True


def retry(max_attempts=3, delay=1, backoff=2, exceptions=(Exception,)):
    """重试装饰器 - 网络请求自动重试
    
    用法:
        @retry(max_attempts=3, delay=1, backoff=2)
        def my_function():
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            attempt = 0
            current_delay = delay
            while attempt < max_attempts:
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    attempt += 1
                    if attempt >= max_attempts:
                        logger.warning(f"{func.__name__} 失败 {max_attempts} 次: {e}")
                        raise
                    logger.debug(f"{func.__name__} 重试 {attempt}/{max_attempts}, 等待 {current_delay}s")
                    time.sleep(current_delay)
                    current_delay *= backoff
            return None
        return wrapper
    return decorator


def now_iso():
    """返回 UTC ISO 8601 时间字符串（末尾 Z）"""
    return datetime.datetime.now(datetime.timezone.utc).isoformat().replace('+00:00', 'Z')


def today_str(fmt='%Y%m%d'):
    """返回今天日期字符串，默认 YYYYMMDD"""
    return datetime.date.today().strftime(fmt)


def safe_name(s: str) -> bool:
    """检查名称是否只含安全字符（字母、数字、下划线、连字符、中文）"""
    import re
    return bool(re.match(r'^[a-zA-Z0-9_\-\u4e00-\u9fff]+$', s))


def validate_url(url: str, allowed_schemes=('https',), allowed_domains=None) -> bool:
    """校验 URL 合法性，防 SSRF"""
    from urllib.parse import urlparse
    try:
        parsed = urlparse(url)
        if parsed.scheme not in allowed_schemes:
            return False
        if allowed_domains and parsed.hostname not in allowed_domains:
            return False
        if not parsed.hostname:
            return False
        # 禁止内网地址
        import ipaddress
        try:
            ip = ipaddress.ip_address(parsed.hostname)
            if ip.is_private or ip.is_loopback or ip.is_reserved:
                return False
        except ValueError:
            pass  # hostname 不是 IP，放行
        return True
    except Exception:
        return False


class ConfigLoader:
    """配置加载器 - 支持多环境配置"""
    
    def __init__(self, base_path: pathlib.Path):
        self.base_path = base_path
        self._cache = {}
    
    def load(self, name: str, default: Any = None) -> Any:
        """加载配置文件，支持缓存"""
        if name in self._cache:
            return self._cache[name]
        
        # 尝试多种格式
        for ext in ['json', 'yaml', 'yml']:
            path = self.base_path / f"{name}.{ext}"
            if path.exists():
                try:
                    if ext == 'json':
                        data = json.loads(path.read_text())
                    else:
                        # 简化处理，YAML需要额外库
                        continue
                    self._cache[name] = data
                    return data
                except Exception as e:
                    logger.warning(f"加载配置 {name} 失败: {e}")
        
        return default
    
    def clear_cache(self):
        """清空缓存"""
        self._cache.clear()


def safe_execute(func: Callable, default: Any = None, fallback: Optional[Callable] = None) -> Any:
    """安全执行函数，失败返回默认值或执行 fallback"""
    try:
        return func()
    except Exception as e:
        logger.debug(f"执行失败: {e}")
        if fallback:
            try:
                return fallback()
            except Exception:
                pass
        return default
