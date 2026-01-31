"""
STRM 服务模块

提供 STRM 文件生成、解析和流媒体重定向功能
使用 Provider 接口，支持多种网盘类型
"""
from __future__ import annotations
import logging
import os
import re
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from ..core.models import FileItem, FileType
from .drive_service import DriveService
from .file_service import FileService, FileIndex

logger = logging.getLogger(__name__)


@dataclass
class StrmFile:
    """STRM 文件信息"""
    path: str  # STRM 文件路径
    content: str  # STRM 文件内容（URL）
    source_item: FileItem  # 源文件信息（统一模型）


class StrmService:
    """STRM 服务 - 提供 STRM 文件生成和流媒体服务（支持多网盘）"""

    def __init__(self, drive_service: DriveService, task_service=None, cache_ttl: int = 3600):
        """
        Args:
            drive_service: 网盘管理服务
            task_service: 可选的任务服务
            cache_ttl: 下载链接缓存时间（秒）
        """
        self.drive_service = drive_service
        self.task_service = task_service
        self.cache_ttl = cache_ttl
        self._index = FileIndex()

    def close(self):
        """关闭服务"""
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    # ==================== 任务执行 ====================

    def execute_task(self, task_id: str) -> Dict:
        """
        执行 STRM 任务

        Args:
            task_id: 任务 ID

        Returns:
            执行结果字典
        """
        if not self.task_service:
            return {
                'success': False,
                'message': 'Task service not available'
            }

        # 获取任务
        task = self.task_service.get_task(task_id)
        if not task:
            return {
                'success': False,
                'message': f'Task not found: {task_id}'
            }

        logger.info(f"strm_service.py:79 - ========== Starting task execution: {task_id} ({task.task_name}) ==========")
        logger.info(f"strm_service.py:80 - Task config: drive_id={task.drive_id}, source_cid={task.source_cid}, output_dir={task.output_dir}")

        try:
            # 获取 Provider
            provider = self.drive_service.get_provider(task.drive_id)
            if not provider:
                return {
                    'success': False,
                    'message': f'Provider not available for drive: {task.drive_id}'
                }

            # 扫描源目录
            logger.info(f"strm_service.py:93 - Scanning directory: {task.source_cid}")
            current_files = self.scan_directory(task.drive_id, task.source_cid, task)
            logger.info(f"strm_service.py:95 - Scan completed: found {len(current_files)} files")

            # 更新任务进度：总文件数
            self.task_service.update_task(task_id, {
                'total_files': len(current_files),
                'current_file_index': 0
            })

            # 获取历史记录（已生成的 STRM 文件）
            logger.info(f"strm_service.py:104 - Loading STRM records")
            records = self.task_service.get_strm_records(task_id)
            logger.info(f"strm_service.py:106 - Found {len(records)} existing STRM records")

            # 构建历史文件映射（file_id -> record）
            record_map = {r['file_id']: r for r in records}

            # 需要创建的 STRM 文件
            to_create = []
            # 需要更新的 STRM 文件（源文件已改名）
            to_update = []
            # 已失效的 STRM 记录（源文件已被删除或移出源目录）
            to_delete_ids = []

            # 分析当前文件
            logger.info(f"strm_service.py:119 - Analyzing current files (overwrite_strm={task.overwrite_strm})")
            for file_item in current_files:
                record = record_map.get(file_item.id)

                if not record:
                    # 新文件，需要创建
                    to_create.append(file_item)
                else:
                    # 检查是否需要覆盖
                    if task.overwrite_strm:
                        # 覆盖模式：强制重新生成
                        logger.debug(f"strm_service.py:127 - Overwrite mode: will recreate STRM for {file_item.name}")
                        to_update.append((file_item, record))
                    else:
                        # 非覆盖模式：检查文件是否实际存在
                        strm_path = record.get('strm_path')
                        if strm_path and not os.path.exists(strm_path):
                            # STRM 文件不存在，需要重新生成
                            logger.info(f"strm_service.py:133 - STRM file missing: {strm_path}, will recreate")
                            to_update.append((file_item, record))
                        elif record.get('file_name') != file_item.name:
                            # 文件名改变，需要更新
                            logger.info(f"strm_service.py:137 - File renamed: {record.get('file_name')} -> {file_item.name}")
                            to_update.append((file_item, record))
                    # 从映射中移除（剩下的就是已失效的）
                    record_map.pop(file_item.id)

            # 剩余的记录都是源文件已不存在的
            if task.delete_orphans:
                to_delete_ids = [r['id'] for r in record_map.values()]
                logger.info(f"strm_service.py:137 - Found {len(to_delete_ids)} orphaned STRM records to delete")

            # 生成统计
            stats = {
                'total_scanned': len(current_files),
                'to_create': len(to_create),
                'to_update': len(to_update),
                'to_delete': len(to_delete_ids),
                'unchanged': len(current_files) - len(to_create) - len(to_update)
            }

            logger.info(f"strm_service.py:148 - Execution plan: create={stats['to_create']}, update={stats['to_update']}, delete={stats['to_delete']}, unchanged={stats['unchanged']}")

            # 执行创建
            created_count = 0
            for i, file_item in enumerate(to_create):
                try:
                    # 更新进度
                    self.task_service.update_task(task_id, {
                        'current_file_index': i + 1
                    })

                    # 生成 STRM 文件
                    relative_path = self._build_relative_path(file_item, task)
                    strm_path = os.path.join(task.output_dir, relative_path)
                    strm_url = self._build_strm_url(file_item, task.base_url)

                    # 创建目录
                    os.makedirs(os.path.dirname(strm_path), exist_ok=True)

                    # 写入 STRM 文件
                    with open(strm_path, 'w', encoding='utf-8') as f:
                        f.write(strm_url)

                    # 记录到数据库
                    self.task_service.add_strm_record(
                        task_id=task_id,
                        file_id=file_item.id,
                        file_name=file_item.name,
                        file_path=file_item.parent_id,
                        strm_path=strm_path,
                        strm_url=strm_url
                    )

                    created_count += 1
                    logger.debug(f"strm_service.py:184 - Created STRM: {strm_path}")

                except Exception as e:
                    logger.error(f"strm_service.py:187 - Failed to create STRM for {file_item.name}: {e}")

            # 执行更新
            updated_count = 0
            for file_item, old_record in to_update:
                try:
                    # 生成新的 STRM 文件路径
                    relative_path = self._build_relative_path(file_item, task)
                    new_strm_path = os.path.join(task.output_dir, relative_path)
                    old_strm_path = old_record.get('strm_path')

                    # 如果路径改变，删除旧文件
                    if old_strm_path and old_strm_path != new_strm_path and os.path.exists(old_strm_path):
                        try:
                            os.remove(old_strm_path)
                            logger.debug(f"strm_service.py:203 - Removed old STRM: {old_strm_path}")
                        except Exception as e:
                            logger.error(f"strm_service.py:205 - Failed to remove old STRM: {e}")

                    # 创建新文件
                    strm_url = self._build_strm_url(file_item, task.base_url)
                    os.makedirs(os.path.dirname(new_strm_path), exist_ok=True)
                    with open(new_strm_path, 'w', encoding='utf-8') as f:
                        f.write(strm_url)

                    # 更新记录
                    self.task_service.update_strm_record(
                        old_record['id'],
                        file_name=file_item.name,
                        strm_path=new_strm_path,
                        strm_url=strm_url
                    )

                    updated_count += 1
                    logger.debug(f"strm_service.py:223 - Updated STRM: {new_strm_path}")

                except Exception as e:
                    logger.error(f"strm_service.py:226 - Failed to update STRM for {file_item.name}: {e}")

            # 执行删除
            deleted_count = 0
            for record_id in to_delete_ids:
                try:
                    record = next((r for r in records if r['id'] == record_id), None)
                    if record:
                        # 删除 STRM 文件
                        strm_path = record.get('strm_path')
                        if strm_path and os.path.exists(strm_path):
                            try:
                                os.remove(strm_path)
                                logger.debug(f"strm_service.py:239 - Removed orphaned STRM: {strm_path}")
                            except Exception as e:
                                logger.error(f"strm_service.py:241 - Failed to remove STRM file: {e}")

                        # 删除记录
                        self.task_service.delete_strm_record(record_id)
                        deleted_count += 1

                except Exception as e:
                    logger.error(f"strm_service.py:248 - Failed to delete STRM record {record_id}: {e}")

            # 记录执行日志
            log_entry = (
                f"Execution completed: "
                f"created={created_count}, updated={updated_count}, deleted={deleted_count}, "
                f"total_files={len(current_files)}"
            )
            self.task_service.add_task_log(task_id, 'info', log_entry)

            logger.info(f"strm_service.py:258 - ========== Task execution completed: {task_id} ==========")
            logger.info(f"strm_service.py:259 - {log_entry}")

            return {
                'success': True,
                'stats': stats,
                'created': created_count,
                'updated': updated_count,
                'deleted': deleted_count
            }

        except Exception as e:
            logger.exception(f"strm_service.py:269 - Task execution failed: {e}")
            if self.task_service:
                self.task_service.add_task_log(task_id, 'error', f"Execution failed: {str(e)}")
            return {
                'success': False,
                'message': str(e)
            }

    def scan_directory(self, drive_id: str, root_cid: str, task) -> List[FileItem]:
        """
        扫描目录，返回所有视频/音频文件

        Args:
            drive_id: 网盘 ID
            root_cid: 根目录 ID
            task: 任务对象（包含 include_video, include_audio 配置）

        Returns:
            文件列表（统一的 FileItem 模型）
        """
        # 获取 Provider
        provider = self.drive_service.get_provider(drive_id)
        if not provider:
            logger.error(f"strm_service.py:294 - Provider not available for drive: {drive_id}")
            return []

        # 创建 FileService（使用 Provider）
        file_service = FileService(provider, cache_ttl=self.cache_ttl)

        # 清空索引
        self._index.clear()

        # 遍历文件夹
        all_items = file_service.traverse_folder(
            root_folder_id=root_cid,
            root_name="",
            item_handler=lambda item, path: self._index.add(item, path)
        )

        # 过滤媒体文件
        media_files = []
        for item in all_items:
            # 跳过文件夹
            if item.is_folder:
                continue

            # 根据任务配置过滤
            if task.include_video and item.type == FileType.VIDEO:
                media_files.append(item)
            elif task.include_audio and item.type == FileType.AUDIO:
                media_files.append(item)

        logger.info(f"strm_service.py:323 - Scanned {len(all_items)} items, filtered {len(media_files)} media files")
        return media_files

    # ==================== 辅助方法 ====================

    def _build_relative_path(self, file_item: FileItem, task) -> str:
        """
        构建相对路径

        Args:
            file_item: 文件项
            task: 任务对象

        Returns:
            相对路径（用于 STRM 文件）
        """
        # 从索引获取相对路径
        indexed_item = self._index.get_by_id(file_item.id)
        if indexed_item:
            # 尝试从索引获取路径
            for path, item in self._index._by_path.items():
                if item.id == file_item.id:
                    # 替换扩展名为 .strm
                    base_name = os.path.splitext(path)[0]
                    return f"{base_name}.strm"

        # 如果索引没有路径，使用文件名
        base_name = os.path.splitext(file_item.name)[0]
        return f"{base_name}.strm"

    def _build_strm_url(self, file_item: FileItem, base_url: str) -> str:
        """
        构建 STRM URL

        Args:
            file_item: 文件项
            base_url: 基础 URL

        Returns:
            STRM URL（使用 download_id）
        """
        # 使用 download_id（如 115 的 pick_code）
        download_id = file_item.download_id or file_item.id

        # 构建 URL
        if base_url.endswith('/'):
            base_url = base_url[:-1]

        return f"{base_url}/stream/{download_id}"

    # ==================== 兼容性方法（保留） ====================

    def generate_strm_files(
        self,
        root_cid: str,
        output_dir: str,
        base_url: str,
        include_video: bool = True,
        include_audio: bool = False,
        preserve_structure: bool = True,
        drive_id: Optional[str] = None
    ) -> Dict:
        """
        生成 STRM 文件（向后兼容方法）

        注意：此方法仅用于向后兼容，新代码应使用任务管理系统

        Args:
            root_cid: 根目录 ID
            output_dir: 输出目录
            base_url: 基础 URL
            include_video: 是否包含视频
            include_audio: 是否包含音频
            preserve_structure: 是否保留目录结构
            drive_id: 网盘 ID（可选，默认使用当前网盘）

        Returns:
            生成结果字典
        """
        logger.warning("strm_service.py:412 - generate_strm_files() is deprecated, use task system instead")

        # 获取 Provider
        provider = self.drive_service.get_provider(drive_id)
        if not provider:
            return {
                'success': False,
                'message': 'Provider not available'
            }

        # 创建 FileService
        file_service = FileService(provider, cache_ttl=self.cache_ttl)

        # 遍历文件夹
        self._index.clear()
        all_items = file_service.traverse_folder(
            root_folder_id=root_cid,
            root_name="",
            item_handler=lambda item, path: self._index.add(item, path)
        )

        # 过滤媒体文件
        media_files = []
        for item in all_items:
            if item.is_folder:
                continue

            if include_video and item.type == FileType.VIDEO:
                media_files.append(item)
            elif include_audio and item.type == FileType.AUDIO:
                media_files.append(item)

        # 生成 STRM 文件
        created_count = 0
        for item in media_files:
            try:
                # 构建路径
                if preserve_structure:
                    # 从索引获取相对路径
                    relative_path = None
                    for path, indexed_item in self._index._by_path.items():
                        if indexed_item.id == item.id:
                            relative_path = path
                            break

                    if not relative_path:
                        relative_path = item.name

                    # 替换扩展名
                    base_name = os.path.splitext(relative_path)[0]
                    strm_path = os.path.join(output_dir, f"{base_name}.strm")
                else:
                    # 平铺到输出目录
                    base_name = os.path.splitext(item.name)[0]
                    strm_path = os.path.join(output_dir, f"{base_name}.strm")

                # 构建 URL
                download_id = item.download_id or item.id
                if base_url.endswith('/'):
                    base_url = base_url[:-1]
                strm_url = f"{base_url}/stream/{download_id}"

                # 创建目录
                os.makedirs(os.path.dirname(strm_path), exist_ok=True)

                # 写入文件
                with open(strm_path, 'w', encoding='utf-8') as f:
                    f.write(strm_url)

                created_count += 1

            except Exception as e:
                logger.error(f"strm_service.py:492 - Failed to create STRM for {item.name}: {e}")

        return {
            'success': True,
            'total_scanned': len(all_items),
            'media_files': len(media_files),
            'created': created_count
        }

    def parse_strm_url(self, strm_path: str) -> Optional[str]:
        """
        解析 STRM 文件，提取 download_id

        Args:
            strm_path: STRM 文件路径

        Returns:
            download_id（如 115 的 pick_code），失败返回 None
        """
        try:
            with open(strm_path, 'r', encoding='utf-8') as f:
                url = f.read().strip()

            # 提取 download_id
            # URL 格式: http://host:port/stream/{download_id}
            match = re.search(r'/stream/([^/\?]+)', url)
            if match:
                return match.group(1)

            return None

        except Exception as e:
            logger.error(f"strm_service.py:527 - Failed to parse STRM file {strm_path}: {e}")
            return None
