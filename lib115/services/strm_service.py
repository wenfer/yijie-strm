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

    def __init__(self, file_service: FileService = None, config: AppConfig = None):
        self.config = config or default_config
        self.file_service = file_service or FileService(config=self.config)
        self._index = FileIndex()

    def close(self):
        """关闭服务"""
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

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
