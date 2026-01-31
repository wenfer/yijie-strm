"""
数据库工厂
根据配置创建数据库实例
"""
import logging
from typing import Optional
from .base import DatabaseInterface
from .sqlite_db import SQLiteDatabase
from .mysql_db import MySQLDatabase

logger = logging.getLogger(__name__)


def get_database(config) -> DatabaseInterface:
    """
    根据配置创建数据库实例

    Args:
        config: AppConfig 实例

    Returns:
        DatabaseInterface 实例
    """
    db_type = config.database.TYPE.lower()

    if db_type == 'sqlite':
        logger.info(f"factory.py:27 - Using SQLite database: {config.database.PATH}")
        return SQLiteDatabase(config.database.PATH)
    elif db_type == 'mysql':
        logger.info(f"factory.py:30 - Using MySQL database: {config.database.HOST}:{config.database.PORT}/{config.database.NAME}")
        return MySQLDatabase(
            host=config.database.HOST,
            port=config.database.PORT,
            database=config.database.NAME,
            user=config.database.USER,
            password=config.database.PASSWORD
        )
    else:
        raise ValueError(f"Unsupported database type: {db_type}")


# Alias for backwards compatibility
create_database = get_database
