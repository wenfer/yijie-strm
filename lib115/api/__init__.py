"""
115 网盘 API 模块
"""
from .client import Client115, is_folder, get_item_attr, RateLimiter

__all__ = ['Client115', 'is_folder', 'get_item_attr', 'RateLimiter']
