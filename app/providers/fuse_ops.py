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

        # 根据文档示例：P115FuseOperations().run_forever("mount_point", ...)
        # 似乎是无参数构造，然后在 run_forever 时传递路径
        # 但我们需要指定 cookie 和 root_cid

        from pathlib import Path

        # 尝试创建实例
        # 检查构造函数签名
        import inspect
        sig = inspect.signature(P115FuseOperations.__init__)
        fuse_log("INFO", f"P115FuseOperations.__init__ signature: {sig}")

        # 根据签名创建实例
        params = list(sig.parameters.keys())
        fuse_log("INFO", f"Constructor parameters: {params}")

        # 尝试不同的构造方式
        if len(params) <= 1:  # 只有 self
            # 无参数构造
            ops = P115FuseOperations()
            fuse_log("INFO", "Created with no args (will configure in run_forever)")
        else:
            # 有参数构造
            # 尝试常见的参数名
            kwargs = {}
            if 'path' in params or 'cookie_path' in params or 'cookies' in params:
                # 传递 cookie 路径
                param_name = 'path' if 'path' in params else ('cookie_path' if 'cookie_path' in params else 'cookies')
                kwargs[param_name] = Path(cookie_file)
            if 'cid' in params and root_cid != "0":
                kwargs['cid'] = root_cid

            fuse_log("INFO", f"Creating with kwargs: {kwargs}")
            ops = P115FuseOperations(**kwargs)

        fuse_log("INFO", "P115FuseOperations created successfully")
        # 保存配置供后续使用
        ops._cookie_file = cookie_file
        ops._root_cid = root_cid if root_cid != "0" else None

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
    fuse_log("INFO", f"  Mount point: {mount_point}")
    fuse_log("INFO", f"  Options: {kwargs}")

    # 根据文档示例，run_forever 的第一个参数是挂载点路径（或 cookie 路径）
    # 检查 run_forever 的签名
    import inspect
    sig = inspect.signature(ops.run_forever)
    params = list(sig.parameters.keys())
    fuse_log("INFO", f"run_forever parameters: {params}")

    try:
        # 根据保存的配置构建参数
        # 文档示例: run_forever("p115fuse", foreground=True, ...)
        # "p115fuse" 可能是挂载点，也可能是 cookie 路径

        # 提取 cookie 和 cid 配置
        cookie_file = getattr(ops, '_cookie_file', None)
        root_cid = getattr(ops, '_root_cid', None)

        fuse_log("INFO", f"  Cookie file: {cookie_file}")
        fuse_log("INFO", f"  Root CID: {root_cid}")

        # 构建 run_forever 参数
        run_kwargs = {
            "foreground": kwargs.get("foreground", True),
            "max_readahead": kwargs.get("max_readahead", 0),
            "noauto_cache": kwargs.get("noauto_cache", True),
            "allow_other": kwargs.get("allow_other", False),
        }

        if kwargs.get("nothreads"):
            run_kwargs["nothreads"] = True

        # 检查第一个参数应该是什么
        # 根据文档，可能是 cookie_path 或 mount_point
        # 先尝试传递 cookie_file (如果有)，否则传递 mount_point
        first_arg = cookie_file if cookie_file else mount_point

        fuse_log("INFO", f"Calling run_forever('{first_arg}', {run_kwargs})")

        # 如果有 cid 参数，添加到 kwargs
        if 'cid' in params and root_cid:
            run_kwargs['cid'] = root_cid
            fuse_log("INFO", f"  Added cid={root_cid} to run_kwargs")

        ops.run_forever(first_arg, **run_kwargs)

        fuse_log("INFO", "FUSE mount exited normally")
    except Exception as e:
        fuse_log("ERROR", f"FUSE mount failed: {e}")
        import traceback
        fuse_log("ERROR", traceback.format_exc())
        raise
