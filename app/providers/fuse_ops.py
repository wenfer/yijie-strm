"""
115 网盘 FUSE 挂载实现
使用 p115client 官方的 p115fuse 模块
"""
import logging
import time
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# FUSE 日志文件
FUSE_LOG_FILE = Path("/data/fuse_debug.log")


def fuse_log(level: str, message: str):
    """FUSE 日志输出到文件"""
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"{timestamp} - FUSE - {level} - {message}\n"

    # 写入文件
    try:
        with open(FUSE_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(log_line)
            f.flush()
    except Exception:
        pass

    # 同时输出到 stdout
    print(log_line.strip(), flush=True)


try:
    from p115fuse import P115FuseOperations
    HAS_FUSE = True
    fuse_log("INFO", "p115fuse module loaded successfully")
except (ImportError, OSError, EnvironmentError) as e:
    fuse_log("ERROR", f"Failed to import p115fuse: {e}")
    P115FuseOperations = None
    HAS_FUSE = False


def create_fuse_instance(cookie_file: str, root_cid: str = "0") -> Optional[P115FuseOperations]:
    """
    创建 P115FuseOperations 实例

    Args:
        cookie_file: Cookie 文件路径
        root_cid: 根目录 CID，默认为 "0" (网盘根目录)

    Returns:
        P115FuseOperations 实例，如果失败返回 None
    """
    if not HAS_FUSE:
        fuse_log("ERROR", "p115fuse not available")
        return None

    try:
        fuse_log("INFO", f"Creating P115FuseOperations with cookie_file={cookie_file}, root_cid={root_cid}")

        # 根据 p115fuse 的实现，它会自动读取 cookie 文件
        # 只需要传递 cookie 路径即可
        ops = P115FuseOperations(
            path_or_cookies=cookie_file,
            cid=root_cid if root_cid != "0" else None  # None 表示使用根目录
        )

        fuse_log("INFO", "P115FuseOperations created successfully")
        return ops
    except Exception as e:
        fuse_log("ERROR", f"Failed to create P115FuseOperations: {e}")
        import traceback
        fuse_log("ERROR", traceback.format_exc())
        return None


def mount_fuse(ops: P115FuseOperations, mount_point: str, **kwargs):
    """
    启动 FUSE 挂载

    Args:
        ops: P115FuseOperations 实例
        mount_point: 挂载点路径
        **kwargs: 传递给 run_forever 的额外参数
    """
    fuse_log("INFO", f"Starting FUSE mount on {mount_point}")
    fuse_log("INFO", f"  kwargs: {kwargs}")

    try:
        ops.run_forever(
            mount_point,
            foreground=kwargs.get("foreground", True),
            max_readahead=kwargs.get("max_readahead", 0),
            noauto_cache=kwargs.get("noauto_cache", True),
            allow_other=kwargs.get("allow_other", False),
            nothreads=kwargs.get("nothreads", False),
        )
        fuse_log("INFO", "FUSE mount exited normally")
    except Exception as e:
        fuse_log("ERROR", f"FUSE mount failed: {e}")
        import traceback
        fuse_log("ERROR", traceback.format_exc())
        raise
