import hashlib
import json
from functools import wraps
from django.core.cache import cache
from typing import Any, Optional

class CacheManager:
    """Redis缓存管理器"""
    
    @staticmethod
    def generate_key(prefix: str, *args, **kwargs) -> str:
        """生成缓存键"""
        key_parts = [prefix]
        key_parts.extend(str(arg) for arg in args)
        key_parts.extend(f"{k}:{v}" for k, v in sorted(kwargs.items()))
        key_string = ":".join(key_parts)
        return hashlib.md5(key_string.encode()).hexdigest()
    
    @staticmethod
    def get_or_set(key: str, default_func, timeout: int = 300) -> Any:
        """获取或设置缓存"""
        value = cache.get(key)
        if value is None:
            value = default_func()
            cache.set(key, value, timeout)
        return value
    
    @staticmethod
    def invalidate_pattern(pattern: str) -> None:
        """根据模式清除缓存"""
        from django_redis import get_redis_connection
        redis_conn = get_redis_connection("default")
        keys = redis_conn.keys(f"*{pattern}*")
        if keys:
            redis_conn.delete(*keys)

def cache_result(timeout: int = 300, key_prefix: str = "cache"):
    """缓存装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache_key = CacheManager.generate_key(key_prefix, *args, **kwargs)
            return CacheManager.get_or_set(cache_key, lambda: func(*args, **kwargs), timeout)
        return wrapper
    return decorator

# 使用示例
# @cache_result(timeout=600, key_prefix="user_data")
# def get_user_data(user_id):
#     return User.objects.get(id=user_id)