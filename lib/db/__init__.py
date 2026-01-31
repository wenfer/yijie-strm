"""
数据库访问层

支持 SQLite 和 MySQL
"""
from .base import DatabaseInterface
from .sqlite_db import SQLiteDatabase
from .mysql_db import MySQLDatabase
from .factory import get_database

__all__ = [
    "DatabaseInterface",
    "SQLiteDatabase",
    "MySQLDatabase",
    "get_database",
]
