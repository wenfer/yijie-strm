"""
数据库接口基类
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any


class DatabaseInterface(ABC):
    """数据库接口抽象类"""

    @abstractmethod
    def connect(self):
        """连接数据库"""
        pass

    @abstractmethod
    def close(self):
        """关闭数据库连接"""
        pass

    @abstractmethod
    def execute(self, query: str, params: tuple = None) -> Any:
        """执行 SQL 语句"""
        pass

    @abstractmethod
    def fetchone(self, query: str, params: tuple = None) -> Optional[Dict]:
        """查询单条记录"""
        pass

    @abstractmethod
    def fetchall(self, query: str, params: tuple = None) -> List[Dict]:
        """查询多条记录"""
        pass

    @abstractmethod
    def init_schema(self):
        """初始化数据库表结构"""
        pass

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
