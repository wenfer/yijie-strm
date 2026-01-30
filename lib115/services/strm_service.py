"""
STRM 服务模块
提供 STRM 文件生成、解析和流媒体重定向功能
"""
from __future__ import annotations
import logging
import os
import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from urllib.parse import quote, urljoin

from ..api.client import Client115, is_folder, get_item_attr
from ..config import AppConfig, default_config
from .file_service import FileService, FileIndex

logger = logging.getLogger(__name__)

# 支持的视频文件扩展名
VIDEO_EXTENSIONS = {
    '.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm',
    '.m4v', '.mpg', '.mpeg', '.ts', '.m2ts', '.vob', '.iso',
    '.rmvb', '.rm', '.asf', '.3gp', '.3g2', '.f4v', '.ogv'
}

# 支持的音频文件扩展名
AUDIO_EXTENSIONS = {
    '.mp3', '.flac', '.wav', '.aac', '.ogg', '.wma', '.m4a',
    '.ape', '.alac', '.opus', '.aiff', '.dsd', '.dsf', '.dff'
}


@dataclass
class StrmFile:
    """STRM 文件信息"""
    path: str  # STRM 文件路径
    content: str  # STRM 文件内容（URL）
    source_item: Dict  # 源文件信息


class StrmService:
    """STRM 服务 - 提供 STRM 文件生成和流媒体服务"""

    def __init__(self, file_service: FileService = None, config: AppConfig = None, task_service=None, drive_service=None):
        self.config = config or default_config
        self.file_service = file_service or FileService(config=self.config)
        self._index = FileIndex()
        self.task_service = task_service  # 可选的任务服务
        self.drive_service = drive_service  # 可选的网盘服务（用于多账号支持）

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

        logger.info(f"========== Starting task execution: {task_id} ({task.task_name}) ==========")
        logger.info(f"Task config: drive_id={task.drive_id}, source_cid={task.source_cid}, output_dir={task.output_dir}")

        try:
            # 扫描源目录
            logger.info(f"Scanning directory: {task.source_cid}")
            current_files = self.scan_directory(task.drive_id, task.source_cid, task)
            logger.info(f"Scan completed: found {len(current_files)} files")

            # 更新任务进度：总文件数
            self.task_service.update_task(task_id, {
                'total_files': len(current_files),
                'current_file_index': 0
            })

            # 获取现有记录
            existing_records = {r['pick_code']: r for r in self.task_service.get_strm_records(task_id)}
            logger.info(f"Found {len(existing_records)} existing STRM records")

            # 统计信息
            files_scanned = len(current_files)
            files_added = 0
            files_updated = 0
            files_skipped = 0

            # 处理每个文件
            for index, file_info in enumerate(current_files, 1):
                pick_code = file_info['pick_code']
                file_name = file_info['file_name']

                # 更新当前处理进度
                self.task_service.update_task(task_id, {
                    'current_file_index': index
                })

                if pick_code in existing_records:
                    # 已存在，检查是否需要更新
                    record = existing_records[pick_code]
                    if self._need_update_record(record, file_info):
                        logger.info(f"[{index}/{files_scanned}] Updating STRM: {file_name}")
                        self._update_strm_file(task, file_info, record)
                        files_updated += 1
                    else:
                        logger.debug(f"[{index}/{files_scanned}] Skipping (unchanged): {file_name}")
                        files_skipped += 1
                else:
                    # 新文件，生成 STRM
                    logger.info(f"[{index}/{files_scanned}] Creating STRM: {file_name}")
                    self._generate_strm_for_task(task, file_info)
                    files_added += 1

            # 处理删除的文件
            files_deleted = 0
            if task.delete_orphans:
                logger.info("Cleaning up orphan STRM files...")
                current_file_ids = {f['file_id'] for f in current_files}
                files_deleted = self.task_service.cleanup_orphan_records(task_id, list(current_file_ids))
                logger.info(f"Deleted {files_deleted} orphan STRM files")

            # 更新快照
            logger.info("Creating file snapshot...")
            self.task_service.create_snapshot(task_id, current_files)

            # 清除进度信息
            self.task_service.update_task(task_id, {
                'total_files': 0,
                'current_file_index': 0
            })

            logger.info(f"========== Task execution completed: {task_id} ==========")
            logger.info(f"Summary: scanned={files_scanned}, added={files_added}, updated={files_updated}, deleted={files_deleted}, skipped={files_skipped}")

            return {
                'success': True,
                'message': 'Task executed successfully',
                'files_scanned': files_scanned,
                'files_added': files_added,
                'files_updated': files_updated,
                'files_deleted': files_deleted,
                'files_skipped': files_skipped
            }

        except Exception as e:
            logger.error(f"========== Task execution failed: {task_id} ==========")
            logger.error(f"Error: {e}", exc_info=True)

            # 检查是否是 token 相关错误
            error_msg = str(e).lower()
            if 'token' in error_msg or 'auth' in error_msg or 'unauthorized' in error_msg or '401' in error_msg:
                logger.error(f"Token error detected for drive {task.drive_id}, marking as unauthenticated")
                if self.drive_service:
                    self.drive_service.mark_drive_unauthenticated(task.drive_id)
                return {
                    'success': False,
                    'message': f'Token expired or invalid. Please re-authenticate drive {task.drive_id}.',
                    'token_error': True,
                    'files_scanned': 0,
                    'files_added': 0,
                    'files_updated': 0,
                    'files_deleted': 0,
                    'files_skipped': 0
                }

            # 清除进度信息
            self.task_service.update_task(task_id, {
                'total_files': 0,
                'current_file_index': 0
            })

            return {
                'success': False,
                'message': str(e),
                'files_scanned': 0,
                'files_added': 0,
                'files_updated': 0,
                'files_deleted': 0,
                'files_skipped': 0
            }

    def scan_directory(self, drive_id: str, cid: str, task) -> List[Dict]:
        """
        扫描目录获取所有符合条件的文件

        Args:
            drive_id: 网盘 ID
            cid: 目录 CID
            task: 任务对象

        Returns:
            文件信息列表
        """
        files = []

        # 获取该 drive 的 file_service
        file_service = self._get_file_service_for_drive(drive_id)
        if not file_service:
            raise RuntimeError(f"Cannot get file service for drive {drive_id}. Please ensure the drive is authenticated.")

        def _process_item(item):
            if is_folder(item):
                return

            file_name = get_item_attr(item, "fn", "file_name", default="")

            # 检查是否应该包含此文件
            if not self.task_service.should_include_file(task, file_name):
                return

            pick_code = get_item_attr(item, "pc", "pick_code")
            if not pick_code:
                return

            file_info = {
                'file_id': get_item_attr(item, "fid", "file_id"),
                'pick_code': pick_code,
                'file_name': file_name,
                'file_size': get_item_attr(item, "fs", "file_size"),
                'file_path': item.get("_relative_path", file_name),
                'modified_time': get_item_attr(item, "utime", "update_time")
            }
            files.append(file_info)

        # 遍历目录
        file_service.traverse_folder(cid, "", item_handler=_process_item)

        return files

    def _get_file_service_for_drive(self, drive_id: str) -> Optional[FileService]:
        """
        获取指定网盘的 file_service

        Args:
            drive_id: 网盘 ID

        Returns:
            FileService 实例，如果无法获取则返回 None
        """
        if not self.drive_service:
            # 没有 drive_service，使用默认的 file_service
            return self.file_service

        # 从 drive_service 获取该 drive 的 client
        client = self.drive_service.get_client(drive_id)
        if not client:
            logger.error(f"Cannot get client for drive {drive_id}")
            return None

        # 创建该 drive 的 file_service
        return FileService(client, self.config)

    def _generate_strm_for_task(self, task, file_info: Dict):
        """为任务生成 STRM 文件"""
        # 构建 STRM 文件路径
        if task.preserve_structure:
            rel_path = file_info['file_path']
            strm_path = os.path.join(
                task.output_dir,
                os.path.splitext(rel_path)[0] + ".strm"
            )
        else:
            strm_path = os.path.join(
                task.output_dir,
                os.path.splitext(file_info['file_name'])[0] + ".strm"
            )

        # 构建 STRM 内容
        base_url = task.base_url or self.config.gateway.STRM_BASE_URL
        if base_url:
            from urllib.parse import urljoin
            content_url = urljoin(base_url.rstrip("/") + "/", f"stream/{file_info['pick_code']}")
        else:
            content_url = f"strm://115/{file_info['pick_code']}"

        # 写入文件
        try:
            os.makedirs(os.path.dirname(strm_path), exist_ok=True)
            with open(strm_path, 'w', encoding='utf-8') as f:
                f.write(content_url)
            logger.debug(f"Created STRM: {strm_path}")
        except Exception as e:
            logger.error(f"Failed to write STRM file {strm_path}: {e}")
            raise

        # 添加记录
        record = {
            'file_id': file_info['file_id'],
            'pick_code': file_info['pick_code'],
            'file_name': file_info['file_name'],
            'file_size': file_info.get('file_size'),
            'file_path': file_info.get('file_path'),
            'strm_path': strm_path,
            'strm_content': content_url
        }
        self.task_service.add_strm_record(task.task_id, record)

    def _update_strm_file(self, task, file_info: Dict, record: Dict):
        """更新 STRM 文件"""
        # 重新生成 STRM 内容
        base_url = task.base_url or self.config.gateway.STRM_BASE_URL
        if base_url:
            from urllib.parse import urljoin
            content_url = urljoin(base_url.rstrip("/") + "/", f"stream/{file_info['pick_code']}")
        else:
            content_url = f"strm://115/{file_info['pick_code']}"

        # 更新文件
        try:
            with open(record['strm_path'], 'w', encoding='utf-8') as f:
                f.write(content_url)
            logger.debug(f"Updated STRM: {record['strm_path']}")
        except Exception as e:
            logger.error(f"Failed to update STRM file {record['strm_path']}: {e}")
            raise

        # 更新记录
        self.task_service.update_strm_record(record['record_id'], {
            'file_name': file_info['file_name'],
            'file_size': file_info.get('file_size'),
            'file_path': file_info.get('file_path'),
            'strm_content': content_url
        })

    def _need_update_record(self, record: Dict, file_info: Dict) -> bool:
        """检查记录是否需要更新"""
        return (record['file_name'] != file_info['file_name'] or
                record.get('file_size') != file_info.get('file_size'))

    # ==================== STRM 文件生成 ====================

    def generate_strm_files(
        self,
        root_cid: str,
        output_dir: str,
        base_url: str = "",
        include_audio: bool = False,
        preserve_structure: bool = True
    ) -> List[StrmFile]:
        """
        为指定目录生成 STRM 文件

        Args:
            root_cid: 根目录 CID
            output_dir: STRM 文件输出目录
            base_url: STRM 文件中的基础 URL（如 http://localhost:8115/stream/）
            include_audio: 是否包含音频文件
            preserve_structure: 是否保持目录结构

        Returns:
            生成的 STRM 文件列表
        """
        strm_files = []
        extensions = VIDEO_EXTENSIONS.copy()
        if include_audio:
            extensions.update(AUDIO_EXTENSIONS)

        def _process_item(item):
            if is_folder(item):
                return

            name = get_item_attr(item, "fn", "file_name", default="")
            ext = os.path.splitext(name)[1].lower()
            if ext not in extensions:
                return

            pick_code = get_item_attr(item, "pc", "pick_code")
            if not pick_code:
                return

            # 构建 STRM 文件路径
            rel_path = item.get("_relative_path", name)
            if preserve_structure:
                strm_path = os.path.join(output_dir, os.path.splitext(rel_path)[0] + ".strm")
            else:
                strm_path = os.path.join(output_dir, os.path.splitext(name)[0] + ".strm")

            # 构建 STRM 内容（URL）
            if base_url:
                content_url = urljoin(base_url.rstrip("/") + "/", f"stream/{pick_code}")
            else:
                content_url = f"strm://115/{pick_code}"

            strm_files.append(StrmFile(
                path=strm_path,
                content=content_url,
                source_item=item
            ))

            # 添加到索引
            self._index.add(item)

        # 遍历目录
        logger.info(f"Scanning directory CID: {root_cid}")
        self.file_service.traverse_folder(root_cid, "", item_handler=_process_item)

        # 写入 STRM 文件
        for strm in strm_files:
            self._write_strm_file(strm)

        logger.info(f"Generated {len(strm_files)} STRM files")
        return strm_files

    def _write_strm_file(self, strm: StrmFile):
        """写入单个 STRM 文件"""
        try:
            os.makedirs(os.path.dirname(strm.path), exist_ok=True)
            with open(strm.path, 'w', encoding='utf-8') as f:
                f.write(strm.content)
            logger.debug(f"Created STRM: {strm.path}")
        except Exception as e:
            logger.error(f"Failed to write STRM file {strm.path}: {e}")

    # ==================== STRM 解析服务 ====================

    def parse_strm_file(self, strm_path: str) -> Optional[str]:
        """
        解析 STRM 文件，提取 pick_code

        Args:
            strm_path: STRM 文件路径

        Returns:
            pick_code 或 None
        """
        try:
            with open(strm_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
            return self.extract_pick_code(content)
        except Exception as e:
            logger.error(f"Failed to read STRM file {strm_path}: {e}")
            return None

    def extract_pick_code(self, url: str) -> Optional[str]:
        """
        从 URL 中提取 pick_code

        支持的格式:
        - strm://115/{pick_code}
        - http://host/stream/{pick_code}
        - 直接的 pick_code 字符串
        """
        url = url.strip()

        # 格式: strm://115/{pick_code}
        if url.startswith("strm://115/"):
            return url[11:]

        # 格式: http://host/stream/{pick_code}
        match = re.search(r'/stream/([a-zA-Z0-9]+)', url)
        if match:
            return match.group(1)

        # 格式: 直接的 pick_code（字母数字组合）
        if re.match(r'^[a-zA-Z0-9]+$', url):
            return url

        return None

    # ==================== 流媒体重定向服务 ====================

    def get_stream_url(self, pick_code: str, use_cache: bool = True) -> Optional[str]:
        """
        获取流媒体直链 URL

        Args:
            pick_code: 文件的 pick_code
            use_cache: 是否使用缓存

        Returns:
            下载直链 URL
        """
        return self.file_service.get_download_url(pick_code, use_cache)

    def get_stream_info(self, pick_code: str) -> Optional[Dict]:
        """
        获取流媒体文件信息

        Returns:
            {
                "pick_code": str,
                "file_name": str,
                "file_size": int,
                "download_url": str
            }
        """
        # 先从索引查找
        item = self._index.get_by_pick_code(pick_code)

        if not item:
            # 尝试通过 API 获取下载链接来验证 pick_code 有效性
            url = self.get_stream_url(pick_code)
            if not url:
                return None
            return {
                "pick_code": pick_code,
                "file_name": None,
                "file_size": None,
                "download_url": url
            }

        url = self.get_stream_url(pick_code)
        return {
            "pick_code": pick_code,
            "file_name": get_item_attr(item, "fn", "file_name"),
            "file_size": get_item_attr(item, "fs", "file_size"),
            "download_url": url
        }

    # ==================== 索引管理 ====================

    def build_index(self, root_cid: str):
        """构建文件索引"""
        logger.info(f"Building index for CID: {root_cid}")
        self._index.clear()

        def _add_to_index(item):
            self._index.add(item)

        self.file_service.traverse_folder(root_cid, "", item_handler=_add_to_index)
        logger.info(f"Index built with {len(self._index)} items")

    def get_index_stats(self) -> Dict:
        """获取索引统计信息"""
        return {
            "total_items": len(self._index)
        }

    def lookup_by_path(self, path: str) -> Optional[Dict]:
        """通过路径查找文件"""
        return self._index.get_by_path(path)

    def lookup_by_pick_code(self, pick_code: str) -> Optional[Dict]:
        """通过 pick_code 查找文件"""
        return self._index.get_by_pick_code(pick_code)


class StrmGenerator:
    """STRM 文件批量生成器"""

    def __init__(self, strm_service: StrmService):
        self.strm_service = strm_service

    def generate_for_folders(
        self,
        folder_configs: List[Dict],
        output_base_dir: str,
        base_url: str = ""
    ) -> Dict[str, List[StrmFile]]:
        """
        为多个文件夹生成 STRM 文件

        Args:
            folder_configs: 文件夹配置列表
                [{"cid": "xxx", "name": "电影"}, ...]
            output_base_dir: 输出基础目录
            base_url: STRM 文件中的基础 URL

        Returns:
            {folder_name: [StrmFile, ...], ...}
        """
        results = {}

        for config in folder_configs:
            cid = config.get("cid")
            name = config.get("name", cid)

            if not cid:
                continue

            output_dir = os.path.join(output_base_dir, name)
            strm_files = self.strm_service.generate_strm_files(
                root_cid=cid,
                output_dir=output_dir,
                base_url=base_url
            )
            results[name] = strm_files

        return results

    def sync_strm_files(
        self,
        root_cid: str,
        strm_dir: str,
        base_url: str = "",
        delete_orphans: bool = False
    ) -> Tuple[int, int, int]:
        """
        同步 STRM 文件（增量更新）

        Args:
            root_cid: 根目录 CID
            strm_dir: STRM 文件目录
            base_url: 基础 URL
            delete_orphans: 是否删除孤立的 STRM 文件

        Returns:
            (added, updated, deleted) 数量
        """
        added = 0
        updated = 0
        deleted = 0

        # 获取现有 STRM 文件
        existing_strm = set()
        if os.path.exists(strm_dir):
            for root, dirs, files in os.walk(strm_dir):
                for f in files:
                    if f.endswith('.strm'):
                        rel_path = os.path.relpath(os.path.join(root, f), strm_dir)
                        existing_strm.add(rel_path)

        # 生成新的 STRM 文件
        new_strm_files = self.strm_service.generate_strm_files(
            root_cid=root_cid,
            output_dir=strm_dir,
            base_url=base_url
        )

        new_strm_paths = set()
        for strm in new_strm_files:
            rel_path = os.path.relpath(strm.path, strm_dir)
            new_strm_paths.add(rel_path)

            if rel_path in existing_strm:
                updated += 1
            else:
                added += 1

        # 删除孤立文件
        if delete_orphans:
            orphans = existing_strm - new_strm_paths
            for orphan in orphans:
                orphan_path = os.path.join(strm_dir, orphan)
                try:
                    os.remove(orphan_path)
                    deleted += 1
                    logger.info(f"Deleted orphan STRM: {orphan}")
                except Exception as e:
                    logger.error(f"Failed to delete orphan {orphan}: {e}")

        return added, updated, deleted
