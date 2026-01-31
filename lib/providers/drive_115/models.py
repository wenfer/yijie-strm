"""
115 网盘数据模型转换器

将 115 API 返回的数据转换为统一的核心模型
"""
from typing import Dict, List, Optional
from ...core.models import FileItem, FileType, FileEvent, EventType


def convert_to_file_item(item_115: Dict) -> FileItem:
    """将 115 文件项转换为 FileItem

    Args:
        item_115: 115 API 返回的文件项

    Returns:
        FileItem: 统一的文件项模型
    """
    # 判断文件类型
    fc = item_115.get("fc") or item_115.get("file_category", "")
    file_type = _map_file_type(fc, item_115.get("fn", ""))

    return FileItem(
        id=str(item_115.get("fid") or item_115.get("file_id", "")),
        name=item_115.get("fn") or item_115.get("file_name", ""),
        type=file_type,
        size=int(item_115.get("fs") or item_115.get("file_size", 0)),
        parent_id=str(item_115.get("cid") or item_115.get("pid", "")),
        download_id=item_115.get("pc") or item_115.get("pick_code"),  # 115 特有
        created_at=float(item_115.get("ct", 0)) if item_115.get("ct") else None,
        modified_at=float(item_115.get("te", 0)) if item_115.get("te") else None,
        raw_data=item_115
    )


def convert_to_file_items(items_115: List[Dict]) -> List[FileItem]:
    """批量转换文件项

    Args:
        items_115: 115 文件项列表

    Returns:
        List[FileItem]: 统一的文件项列表
    """
    return [convert_to_file_item(item) for item in items_115]


def _map_file_type(fc: str, filename: str) -> FileType:
    """映射 115 文件类型到统一类型

    Args:
        fc: 115 file_category (0=文件夹, 1=视频, 2=音频, 3=图片, 4=文档, 5=其他)
        filename: 文件名

    Returns:
        FileType: 统一的文件类型
    """
    if fc == "0" or fc == 0:
        return FileType.FOLDER

    if fc == "1" or fc == 1:
        return FileType.VIDEO

    if fc == "2" or fc == 2:
        return FileType.AUDIO

    if fc == "3" or fc == 3:
        return FileType.IMAGE

    if fc == "4" or fc == 4:
        return FileType.DOCUMENT

    # 根据扩展名推断
    if filename:
        ext = filename.lower().split('.')[-1] if '.' in filename else ""
        if ext in VIDEO_EXTENSIONS:
            return FileType.VIDEO
        elif ext in AUDIO_EXTENSIONS:
            return FileType.AUDIO
        elif ext in IMAGE_EXTENSIONS:
            return FileType.IMAGE
        elif ext in DOCUMENT_EXTENSIONS:
            return FileType.DOCUMENT

    return FileType.OTHER


def convert_to_file_event(event_115: Dict) -> Optional[FileEvent]:
    """将 115 事件转换为 FileEvent

    Args:
        event_115: 115 API 返回的事件

    Returns:
        Optional[FileEvent]: 统一的文件事件，无法识别返回 None
    """
    event_type_code = event_115.get("type")
    event_type = _map_event_type(event_type_code)

    if event_type == EventType.UNKNOWN:
        return None

    # 提取文件信息
    file_id = str(event_115.get("file_id", ""))
    file_name = event_115.get("file_name", "")
    parent_id = str(event_115.get("cid", ""))

    # 事件 ID（使用 id 字段）
    event_id = str(event_115.get("id", ""))

    # 时间戳
    timestamp = float(event_115.get("time", 0))

    return FileEvent(
        event_id=event_id,
        event_type=event_type,
        file_id=file_id,
        file_name=file_name,
        parent_id=parent_id,
        timestamp=timestamp,
        raw_data=event_115
    )


def _map_event_type(type_code: int) -> EventType:
    """映射 115 事件类型到统一类型

    115 事件类型：
    - 2: upload_file
    - 6: move_file
    - 14: receive_files
    - 17: new_folder
    - 20: folder_rename
    - 22: delete_file
    """
    EVENT_TYPE_MAP = {
        2: EventType.UPLOAD,
        6: EventType.MOVE,
        14: EventType.SHARE,
        17: EventType.CREATE_FOLDER,
        20: EventType.RENAME,
        22: EventType.DELETE,
    }

    return EVENT_TYPE_MAP.get(type_code, EventType.UNKNOWN)


# 文件扩展名映射
VIDEO_EXTENSIONS = {
    "mp4", "mkv", "avi", "mov", "wmv", "flv", "webm", "m4v",
    "mpg", "mpeg", "3gp", "ts", "m2ts", "rmvb", "rm"
}

AUDIO_EXTENSIONS = {
    "mp3", "flac", "wav", "aac", "m4a", "wma", "ogg", "ape",
    "alac", "dsd", "dsf", "dff"
}

IMAGE_EXTENSIONS = {
    "jpg", "jpeg", "png", "gif", "bmp", "webp", "svg", "ico",
    "tiff", "tif", "heic", "heif"
}

DOCUMENT_EXTENSIONS = {
    "pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx",
    "txt", "md", "csv", "rtf", "odt", "ods", "odp"
}
