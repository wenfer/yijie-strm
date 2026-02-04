"""
系统 API 路由
"""
import logging
import time
from datetime import datetime
from pathlib import Path
import yaml
import shutil
import collections

from fastapi import APIRouter, Query, HTTPException, Body

from app.api.schemas import DataResponse, SystemConfig, GatewayConfig, DatabaseConfig, LogConfig
from app.core.config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/system", tags=["系统"])


@router.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "version": "3.0.0"
    }


@router.get("/info", response_model=DataResponse)
async def system_info():
    """获取系统信息"""
    import platform
    import sys

    return DataResponse(data={
        "name": "多网盘 STRM 网关",
        "version": "3.0.0",
        "python_version": sys.version,
        "platform": platform.platform(),
        "start_time": datetime.now().isoformat()
    })


@router.get("/directories", response_model=DataResponse)
async def list_directories(
    path: str = Query("/", description="要浏览的目录路径")
):
    """浏览服务器本地目录"""
    try:
        dir_path = Path(path).expanduser().resolve()

        if not dir_path.exists():
            return DataResponse(success=False, message=f"路径不存在: {path}")

        if not dir_path.is_dir():
            return DataResponse(success=False, message=f"不是一个目录: {path}")

        dirs = []
        try:
            for item in sorted(dir_path.iterdir(), key=lambda x: x.name.lower()):
                if item.is_dir() and not item.name.startswith('.'):
                    dirs.append({
                        "name": item.name,
                        "path": str(item),
                    })
        except PermissionError:
            return DataResponse(success=False, message=f"没有权限访问: {path}")

        return DataResponse(data={
            "current_path": str(dir_path),
            "parent_path": str(dir_path.parent) if dir_path != dir_path.parent else None,
            "directories": dirs,
        })
    except Exception as e:
        logger.error(f"Failed to list directories: {e}")
        return DataResponse(success=False, message=f"浏览目录失败: {str(e)}")


@router.get("/config", response_model=DataResponse)
async def get_system_config():
    """获取系统配置"""
    try:
        config_path = Path("config.yaml")

        # 如果配置文件存在，从文件读取
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                raw_config = yaml.safe_load(f) or {}

            # 构造响应
            # 确保即使配置文件缺少某些字段，也能返回默认值
            default_settings = get_settings()

            gateway_data = raw_config.get("gateway", {})
            database_data = raw_config.get("database", {})
            log_data = raw_config.get("log", {})

            # 合并默认值
            gateway_config = GatewayConfig(
                host=gateway_data.get("host", default_settings.gateway.host),
                port=gateway_data.get("port", default_settings.gateway.port),
                debug=gateway_data.get("debug", default_settings.gateway.debug),
                strm_base_url=gateway_data.get("strm_base_url", default_settings.gateway.strm_base_url),
                cache_ttl=gateway_data.get("cache_ttl", default_settings.gateway.cache_ttl),
                enable_cors=gateway_data.get("enable_cors", default_settings.gateway.enable_cors)
            )

            database_config = DatabaseConfig(
                url=database_data.get("url", default_settings.database.url),
                generate_schemas=database_data.get("generate_schemas", default_settings.database.generate_schemas),
                pool_min=database_data.get("pool_min", default_settings.database.min_size),
                pool_max=database_data.get("pool_max", default_settings.database.max_size)
            )

            log_config = LogConfig(
                level=log_data.get("level", default_settings.log.level),
                format=log_data.get("format", default_settings.log.format)
            )

            return DataResponse(data=SystemConfig(
                gateway=gateway_config,
                database=database_config,
                log=log_config
            ))

        else:
            # 配置文件不存在，返回当前运行配置
            settings = get_settings()
            return DataResponse(data=SystemConfig(
                gateway=GatewayConfig(
                    host=settings.gateway.host,
                    port=settings.gateway.port,
                    debug=settings.gateway.debug,
                    strm_base_url=settings.gateway.strm_base_url,
                    cache_ttl=settings.gateway.cache_ttl,
                    enable_cors=settings.gateway.enable_cors
                ),
                database=DatabaseConfig(
                    url=settings.database.url,
                    generate_schemas=settings.database.generate_schemas,
                    pool_min=settings.database.min_size,
                    pool_max=settings.database.max_size
                ),
                log=LogConfig(
                    level=settings.log.level,
                    format=settings.log.format
                )
            ))

    except Exception as e:
        logger.error(f"Failed to get system config: {e}")
        return DataResponse(success=False, message=f"获取配置失败: {str(e)}")


@router.post("/config", response_model=DataResponse)
async def update_system_config(config: SystemConfig):
    """更新系统配置"""
    try:
        config_path = Path("config.yaml")

        # 备份现有配置
        if config_path.exists():
            backup_path = config_path.with_suffix(f".yaml.bak.{int(time.time())}")
            shutil.copy2(config_path, backup_path)

        # 准备写入的数据
        config_data = {
            "gateway": config.gateway.model_dump(exclude_none=True),
            "database": config.database.model_dump(exclude_none=True),
            "log": config.log.model_dump(exclude_none=True)
        }

        # 写入文件
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(config_data, f, default_flow_style=False, allow_unicode=True)

        return DataResponse(
            message="配置已保存。注意：某些配置（如端口、数据库连接）需要重启服务才能生效。"
        )

    except Exception as e:
        logger.error(f"Failed to update system config: {e}")
        return DataResponse(success=False, message=f"保存配置失败: {str(e)}")


@router.get("/logs", response_model=DataResponse)
async def get_system_logs(
    lines: int = Query(100, ge=1, le=2000, description="获取最后 N 行日志")
):
    """获取系统日志"""
    try:
        settings = get_settings()
        log_file = settings.data_dir / "app.log"

        if not log_file.exists():
            return DataResponse(data=[])

        # 使用 deque 高效读取最后 N 行
        with open(log_file, "r", encoding="utf-8", errors="replace") as f:
            last_lines = collections.deque(f, maxlen=lines)

        # 去除每行末尾的换行符
        logs = [line.rstrip() for line in last_lines]

        return DataResponse(data=logs)

    except Exception as e:
        logger.error(f"Failed to get system logs: {e}")
        return DataResponse(success=False, message=f"获取日志失败: {str(e)}")
