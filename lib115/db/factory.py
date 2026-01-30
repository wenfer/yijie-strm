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
    db_type = config.database.DB_TYPE.lower()

    if db_type == 'sqlite':
        logger.info(f"Using SQLite database: {config.database.DB_PATH}")
        return SQLiteDatabase(config.database.DB_PATH)
    elif db_type == 'mysql':
        logger.info(f"Using MySQL database: {config.database.DB_HOST}:{config.database.DB_PORT}/{config.database.DB_NAME}")
        return MySQLDatabase(
            host=config.database.DB_HOST,
            port=config.database.DB_PORT,
            database=config.database.DB_NAME,
            user=config.database.DB_USER,
            password=config.database.DB_PASSWORD
        )
    else:
        raise ValueError(f"Unsupported database type: {db_type}")


# Alias for backwards compatibility
create_database = get_database
