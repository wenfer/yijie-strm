"""
115 网盘事件监听服务
基于 115 生活事件 API 实现实时文件变化监听
"""
import time
import logging
from typing import Dict, List, Optional, Set, Callable
from datetime import datetime

logger = logging.getLogger(__name__)


# 115 生活操作事件类型映射
BEHAVIOR_TYPE_TO_NAME = {
    1: "upload_image_file",
    2: "upload_file",
    3: "star_image",
    4: "star_file",
    5: "move_image_file",
    6: "move_file",
    7: "browse_image",
    8: "browse_video",
    9: "browse_audio",
    10: "browse_document",
    14: "receive_files",
    17: "new_folder",
    18: "copy_folder",
    19: "folder_label",
    20: "folder_rename",
    22: "delete_file",
}

# 需要触发 STRM 同步的事件类型（文件系统变更事件）
SYNC_TRIGGER_TYPES = {2, 5, 6, 14, 17, 18, 20, 22}  # upload, move, receive, new_folder, copy, rename, delete

# 默认忽略的事件类型（浏览类事件）
IGNORE_BEHAVIOR_TYPES = frozenset((3, 4, 7, 8, 9, 10, 19))


class EventMonitor:
    """115 网盘事件监听器"""

    def __init__(self, client, cooldown: float = 0.2):
        """
        Args:
            client: Client115 实例
            cooldown: API 调用冷却时间（秒）
        """
        self.client = client
        self.cooldown = cooldown
        self._last_event_ids: Dict[str, int] = {}  # task_id -> last_event_id
        self._last_check_times: Dict[str, float] = {}  # task_id -> last_check_time

    def start_monitoring(self, task_id: str, source_cid: str,
                         callback: Callable[[List[Dict]], None],
                         from_event_id: int = 0) -> bool:
        """
        开始监听指定目录的文件变化

        Args:
            task_id: 任务 ID
            source_cid: 监听的目录 ID
            callback: 检测到变化时的回调函数，接收事件列表
            from_event_id: 起始事件 ID（0 表示从当前时间开始）

        Returns:
            是否成功开始监听
        """
        self._last_event_ids[task_id] = from_event_id
        self._last_check_times[task_id] = time.time()
        logger.info(f"Started event monitoring for task {task_id}, cid={source_cid}, from_event_id={from_event_id}")
        return True

    def stop_monitoring(self, task_id: str):
        """停止监听"""
        self._last_event_ids.pop(task_id, None)
        self._last_check_times.pop(task_id, None)
        logger.info(f"Stopped event monitoring for task {task_id}")

    def check_events(self, task_id: str, source_cid: str) -> Optional[List[Dict]]:
        """
        检查是否有新事件

        Args:
            task_id: 任务 ID
            source_cid: 监听的目录 ID

        Returns:
            新事件列表，如果没有新事件则返回 None
        """
        if task_id not in self._last_event_ids:
            logger.warning(f"Task {task_id} not being monitored")
            return None

        try:
            # 获取最新事件
            events = self._fetch_new_events(
                from_event_id=self._last_event_ids[task_id],
                source_cid=source_cid
            )

            if not events:
                return None

            # 过滤相关事件
            relevant_events = self._filter_relevant_events(events, source_cid)

            if relevant_events:
                # 更新最后事件 ID
                max_event_id = max(int(e['id']) for e in events)
                self._last_event_ids[task_id] = max_event_id
                self._last_check_times[task_id] = time.time()

                logger.info(
                    f"Task {task_id}: Found {len(relevant_events)} relevant events "
                    f"(total {len(events)} events, max_id={max_event_id})"
                )
                return relevant_events

            # 即使没有相关事件，也更新最后事件 ID
            max_event_id = max(int(e['id']) for e in events)
            self._last_event_ids[task_id] = max_event_id

            return None

        except Exception as e:
            logger.error(f"Error checking events for task {task_id}: {e}")
            return None

    def _fetch_new_events(self, from_event_id: int, source_cid: str,
                          limit: int = 1000) -> List[Dict]:
        """
        从 115 API 获取新事件

        Args:
            from_event_id: 起始事件 ID（不含）
            source_cid: 目录 ID（用于过滤）
            limit: 每次获取的最大事件数

        Returns:
            事件列表（按时间倒序，最新的在前）
        """
        events = []
        offset = 0

        while True:
            # 调用 API
            result = self.client.get_life_behavior_list(
                type="",  # 获取所有类型
                date="",  # 不限日期
                limit=limit,
                offset=offset
            )

            if not result or not result.get('list'):
                break

            batch = result['list']

            # 检查是否已经到达起始事件
            for event in batch:
                event_id = int(event['id'])

                if event_id <= from_event_id:
                    # 已经到达起始点，停止获取
                    return events

                events.append(event)

            # 检查是否还有更多数据
            if len(batch) < limit or offset + len(batch) >= result.get('count', 0):
                break

            offset += len(batch)

            # 冷却
            if self.cooldown > 0:
                time.sleep(self.cooldown)

        return events

    def _filter_relevant_events(self, events: List[Dict], source_cid: str) -> List[Dict]:
        """
        过滤出相关的事件

        Args:
            events: 事件列表
            source_cid: 监听的目录 ID

        Returns:
            相关事件列表
        """
        relevant = []
        source_cid_int = int(source_cid)

        for event in events:
            event_type = event.get('type')

            # 忽略浏览类事件
            if event_type in IGNORE_BEHAVIOR_TYPES:
                continue

            # 只关注文件系统变更事件
            if event_type not in SYNC_TRIGGER_TYPES:
                continue

            # 检查事件是否发生在监听的目录或其子目录中
            if self._is_event_in_directory(event, source_cid_int):
                # 添加事件名称
                event['event_name'] = BEHAVIOR_TYPE_TO_NAME.get(event_type, f"unknown_{event_type}")
                relevant.append(event)

        return relevant

    def _is_event_in_directory(self, event: Dict, target_cid: int) -> bool:
        """
        检查事件是否发生在目标目录或其子目录中

        Args:
            event: 事件数据
            target_cid: 目标目录 ID

        Returns:
            是否在目标目录中
        """
        # 如果目标是根目录，接受所有事件
        if target_cid == 0:
            return True

        # 获取事件相关的目录 ID
        # 不同事件类型的目录 ID 字段可能不同
        parent_id = event.get('parent_id') or event.get('category_id') or event.get('cid')

        if not parent_id:
            # 如果没有目录信息，暂时接受（后续可以通过 API 查询）
            return True

        parent_id = int(parent_id)

        # 简单检查：事件的父目录是否匹配
        # 注意：这里只检查直接父目录，不检查祖先目录
        # 如果需要完整的祖先检查，需要额外的 API 调用
        return parent_id == target_cid

    def get_monitoring_status(self, task_id: str) -> Optional[Dict]:
        """
        获取监听状态

        Args:
            task_id: 任务 ID

        Returns:
            状态信息字典
        """
        if task_id not in self._last_event_ids:
            return None

        return {
            'task_id': task_id,
            'last_event_id': self._last_event_ids[task_id],
            'last_check_time': self._last_check_times.get(task_id, 0),
            'monitoring': True
        }


class EventProcessor:
    """事件处理器 - 将事件转换为文件变更信息"""

    @staticmethod
    def process_events(events: List[Dict]) -> Dict[str, Set[str]]:
        """
        处理事件列表，提取文件变更信息

        Args:
            events: 事件列表

        Returns:
            变更信息字典: {
                'added': set of file_ids,
                'modified': set of file_ids,
                'deleted': set of file_ids,
                'moved': set of file_ids
            }
        """
        changes = {
            'added': set(),
            'modified': set(),
            'deleted': set(),
            'moved': set()
        }

        for event in events:
            event_type = event.get('type')
            file_id = str(event.get('file_id', ''))

            if not file_id:
                continue

            event_name = event.get('event_name', '')

            # 上传、接收、新建文件夹 -> 添加
            if event_type in (2, 14, 17):  # upload_file, receive_files, new_folder
                changes['added'].add(file_id)

            # 移动、复制 -> 移动/添加
            elif event_type in (5, 6, 18):  # move_image_file, move_file, copy_folder
                changes['moved'].add(file_id)

            # 重命名 -> 修改
            elif event_type == 20:  # folder_rename
                changes['modified'].add(file_id)

            # 删除 -> 删除
            elif event_type == 22:  # delete_file
                changes['deleted'].add(file_id)

        return changes

    @staticmethod
    def summarize_changes(changes: Dict[str, Set[str]]) -> str:
        """
        生成变更摘要

        Args:
            changes: 变更信息字典

        Returns:
            摘要字符串
        """
        parts = []
        if changes['added']:
            parts.append(f"+{len(changes['added'])} added")
        if changes['modified']:
            parts.append(f"~{len(changes['modified'])} modified")
        if changes['deleted']:
            parts.append(f"-{len(changes['deleted'])} deleted")
        if changes['moved']:
            parts.append(f"→{len(changes['moved'])} moved")

        return ", ".join(parts) if parts else "no changes"
