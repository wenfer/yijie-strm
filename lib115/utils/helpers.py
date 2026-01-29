"""
115 网盘辅助工具模块
"""
from __future__ import annotations
import os
import re
from typing import List, Union


def format_bytes(num_bytes: int) -> str:
    """将字节数转换为人类可读格式"""
    if num_bytes == 0:
        return "0 B"
    size_names = ("B", "KB", "MB", "GB", "TB", "PB")
    i = 0
    while num_bytes >= 1024 and i < len(size_names) - 1:
        num_bytes /= 1024
        i += 1
    return f"{round(num_bytes, 2)} {size_names[i]}"


def parse_size(size_str: str) -> int:
    """
    解析人类可读的大小字符串为字节数

    支持格式: "1GB", "500MB", "1.5TB", "0B"
    """
    if not isinstance(size_str, str):
        return 0

    size_str = size_str.strip()
    if size_str in ("0 B", "0B", "0"):
        return 0

    match = re.match(r'^([\d.]+)\s*([KMGTPE]B?)?$', size_str, re.IGNORECASE)
    if not match:
        return 0

    number_str, unit = match.groups()
    try:
        number = float(number_str)
    except ValueError:
        return 0

    unit = (unit or 'B').upper().rstrip('B')
    multipliers = {
        '': 1,
        'K': 1024,
        'M': 1024 ** 2,
        'G': 1024 ** 3,
        'T': 1024 ** 4,
        'P': 1024 ** 5,
        'E': 1024 ** 6,
    }
    return int(number * multipliers.get(unit, 1))


def safe_filename(filename: str, allowed_chars: str = "._- ()[]{}+#@&", max_length: int = 255) -> str:
    """
    将文件名转换为安全的文件名

    Args:
        filename: 原始文件名
        allowed_chars: 允许的特殊字符
        max_length: 最大长度

    Returns:
        安全的文件名
    """
    if not isinstance(filename, str):
        filename = str(filename)

    # 替换不安全字符
    safe = "".join(c if c.isalnum() or c in allowed_chars else '_' for c in filename).strip()
    # 合并连续下划线
    safe = '_'.join(filter(None, safe.split('_')))

    # 截断过长文件名
    if len(safe) > max_length:
        ext = os.path.splitext(safe)[1]
        base = os.path.splitext(safe)[0]
        max_base = max_length - len(ext) - 3 if ext else max_length - 3
        if max_base > 0:
            safe = base[:max_base] + "..." + ext
        else:
            safe = safe[:max_length]

    return safe or "unnamed_file"


def parse_indices(input_str: str, total: int) -> List[int]:
    """
    解析索引输入字符串

    支持格式:
    - 单个索引: "0", "5"
    - 范围: "0-5", "10-20"
    - 混合: "0,2-5,8"
    - 全部: "a", "all"

    Args:
        input_str: 输入字符串
        total: 总数量

    Returns:
        索引列表
    """
    input_str = input_str.strip().lower()

    if input_str in ('a', 'all'):
        return list(range(total))

    indices = set()
    for part in input_str.split(','):
        part = part.strip()
        if not part:
            continue

        if '-' in part:
            try:
                start, end = map(int, part.split('-'))
                if start <= end:
                    indices.update(i for i in range(start, end + 1) if 0 <= i < total)
            except ValueError:
                pass
        else:
            try:
                idx = int(part)
                if 0 <= idx < total:
                    indices.add(idx)
            except ValueError:
                pass

    return sorted(indices)


def join_path(*parts: str) -> str:
    """
    安全地拼接路径，使用正斜杠

    Args:
        *parts: 路径部分

    Returns:
        拼接后的路径
    """
    return os.path.join(*parts).replace("\\", "/")


def get_file_extension(filename: str) -> str:
    """获取文件扩展名（小写）"""
    return os.path.splitext(filename)[1].lower()


def is_video_file(filename: str) -> bool:
    """判断是否为视频文件"""
    video_exts = {
        '.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm',
        '.m4v', '.mpg', '.mpeg', '.ts', '.m2ts', '.vob', '.iso',
        '.rmvb', '.rm', '.asf', '.3gp', '.3g2', '.f4v', '.ogv'
    }
    return get_file_extension(filename) in video_exts


def is_audio_file(filename: str) -> bool:
    """判断是否为音频文件"""
    audio_exts = {
        '.mp3', '.flac', '.wav', '.aac', '.ogg', '.wma', '.m4a',
        '.ape', '.alac', '.opus', '.aiff', '.dsd', '.dsf', '.dff'
    }
    return get_file_extension(filename) in audio_exts


def is_media_file(filename: str) -> bool:
    """判断是否为媒体文件（视频或音频）"""
    return is_video_file(filename) or is_audio_file(filename)


def chunk_list(lst: list, chunk_size: int) -> list:
    """
    将列表分块

    Args:
        lst: 原始列表
        chunk_size: 块大小

    Returns:
        分块后的列表
    """
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]
