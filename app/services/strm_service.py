"""
STRM 文件生成服务
"""
import logging
import asyncio
from pathlib import Path
from typing import List, Optional, Dict, Callable, Set
from datetime import datetime
from urllib.parse import urljoin

from tortoise.transactions import in_transaction

from app.providers.p115 import P115Provider, FileInfo
from app.models.task import StrmTask, StrmRecord, TaskLog, TaskStatus
from app.services.file_service import FileService, TraverseOptions

logger = logging.getLogger(__name__)


class StrmService:
    """STRM 文件生成服务"""

    # 默认视频扩展名
    VIDEO_EXTENSIONS = {
        '.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm',
        '.m4v', '.mpg', '.mpeg', '.3gp', '.ts', '.m2ts', '.rmvb'
    }

    # 默认音频扩展名
    AUDIO_EXTENSIONS = {
        '.mp3', '.flac', '.wav', '.aac', '.m4a', '.wma', '.ogg',
        '.ape', '.opus', '.alac', '.aiff'
    }

    # 刮削资源文件扩展名
    METADATA_EXTENSIONS = {'.nfo'}

    # 图片扩展名
    IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png'}

    # 图片文件名关键词（用于识别封面图等）
    METADATA_IMAGE_PATTERNS = {
        'poster', 'fanart', 'banner', 'thumb', 'logo',
        'clearart', 'landscape', 'disc', 'folder', 'backdrop'
    }

    # 字幕扩展名
    SUBTITLE_EXTENSIONS = {'.srt', '.ass', '.sub', '.ssa', '.idx', '.vtt', '.sup'}

    def __init__(
            self,
            file_service: FileService,
            provider: P115Provider,
            base_url: Optional[str] = None
    ):
        """
        初始化 STRM 服务
        
        Args:
            file_service: 文件服务实例
            provider: Provider 实例
            base_url: STRM 文件中的基础 URL
        """
        self.file_service = file_service
        self.provider = provider
        self.base_url = base_url or ""

    def _should_include_file(self, task: StrmTask, file_info: FileInfo) -> bool:
        """
        判断是否应该包含文件

        Args:
            task: 任务配置
            file_info: 文件信息

        Returns:
            是否应该包含
        """
        ext = Path(file_info.name).suffix.lower()

        # 自定义扩展名优先
        if task.custom_extensions:
            result = ext in [e.lower() if e.startswith('.') else f'.{e.lower()}'
                             for e in task.custom_extensions]
            logger.debug(f"Custom filter: {file_info.name} ext={ext} included={result}")
            return result

        # 默认过滤规则
        if task.include_video and ext in self.VIDEO_EXTENSIONS:
            logger.debug(f"Video filter: {file_info.name} ext={ext} included=True")
            return True

        if task.include_audio and ext in self.AUDIO_EXTENSIONS:
            logger.debug(f"Audio filter: {file_info.name} ext={ext} included=True")
            return True

        logger.debug(f"Filter: {file_info.name} ext={ext} included=False")
        return False

    def _is_metadata_file(self, filename: str) -> bool:
        """
        判断是否为刮削资源文件

        Args:
            filename: 文件名

        Returns:
            是否为刮削资源文件
        """
        ext = Path(filename).suffix.lower()
        stem = Path(filename).stem.lower()

        # NFO 文件
        if ext in self.METADATA_EXTENSIONS:
            return True

        # 字幕文件
        if ext in self.SUBTITLE_EXTENSIONS:
            return True

        # 封面图文件（需要匹配文件名关键词）
        if ext in self.IMAGE_EXTENSIONS:
            for pattern in self.METADATA_IMAGE_PATTERNS:
                if pattern in stem:
                    return True

        return False

    def _build_strm_url(self, pick_code: str, base_url: Optional[str] = None) -> str:
        """
        构建 STRM URL
        
        Args:
            pick_code: 文件的 pick_code
            base_url: 基础 URL
            
        Returns:
            STRM URL
        """
        base = base_url or self.base_url or ""
        # 确保 base_url 以 / 结尾
        if base and not base.endswith('/'):
            base += '/'
        return f"{base}stream/{pick_code}"

    def _build_strm_path(
            self,
            output_dir: str,
            file_path: str,
            preserve_structure: bool = True
    ) -> Path:
        """
        构建 STRM 文件路径
        
        Args:
            output_dir: 输出目录
            file_path: 原文件路径
            preserve_structure: 是否保留目录结构
            
        Returns:
            STRM 文件路径
        """
        output_path = Path(output_dir)

        if preserve_structure:
            # 保留目录结构
            strm_path = output_path / f"{file_path}.strm"
        else:
            # 扁平化存储
            file_name = Path(file_path).name
            strm_path = output_path / f"{file_name}.strm"

        return strm_path

    async def generate_strm_files(
            self,
            task: StrmTask,
            progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> Dict[str, any]:
        """
        为任务生成 STRM 文件
        
        Args:
            task: STRM 任务
            progress_callback: 进度回调函数 (current, total)
            
        Returns:
            执行结果统计
        """
        start_time = datetime.now()

        # 创建任务日志
        log_id = f"{task.id}_{int(start_time.timestamp() * 1000)}"
        await TaskLog.create(
            id=log_id,
            task=task,
            status="running"
        )

        # 更新任务状态
        task.status = TaskStatus.RUNNING
        await task.save()

        stats = {
            "files_scanned": 0,
            "files_added": 0,
            "files_updated": 0,
            "files_deleted": 0,
            "files_skipped": 0,
            "metadata_downloaded": 0,
            "metadata_skipped": 0,
            "errors": []
        }

        try:
            # 确保输出目录存在
            output_path = Path(task.output_dir)
            output_path.mkdir(parents=True, exist_ok=True)

            # 收集需要处理的文件
            files_to_process = []

            options = TraverseOptions(
                max_depth=-1,
                include_folders=False,
                file_filter=lambda f: self._should_include_file(task, f)
            )

            async for file_info, file_path in self.file_service.traverse_folder(
                    task.source_cid,
                    options
            ):
                files_to_process.append((file_info, file_path))
                stats["files_scanned"] += 1
                logger.info(f"Scanned file: {file_path} (is_dir={file_info.is_dir}, ext={Path(file_info.name).suffix})")

            logger.info(f"Total files scanned: {stats['files_scanned']}, filtered: {len(files_to_process)}")

            # 更新任务文件总数
            task.total_files = len(files_to_process)
            await task.save()

            # 如果启用删除孤立文件，收集当前文件 ID
            current_file_ids = set()

            # 记录包含媒体文件的目录（用于下载刮削资源）
            media_dirs: Dict[str, str] = {}  # {parent_id: parent_path}

            # 处理文件
            for index, (file_info, file_path) in enumerate(files_to_process):
                task.current_file_index = index + 1
                await task.save()

                if progress_callback:
                    progress_callback(index + 1, len(files_to_process))

                current_file_ids.add(file_info.id)

                # 记录包含媒体文件的目录
                if file_info.parent_id and file_info.parent_id != "0":
                    parent_path = str(Path(file_path).parent)
                    media_dirs[file_info.parent_id] = parent_path

                try:
                    result = await self._process_file(task, file_info, file_path)

                    if result == "added":
                        stats["files_added"] += 1
                        task.total_files_generated += 1
                    elif result == "updated":
                        stats["files_updated"] += 1
                    elif result == "skipped":
                        stats["files_skipped"] += 1

                except Exception as e:
                    logger.exception(f"Error processing file {file_info.name}: {e}")
                    stats["errors"].append(f"{file_info.name}: {str(e)}")

            # 删除孤立文件
            if task.delete_orphans:
                deleted = await self._cleanup_orphan_records(task, current_file_ids)
                stats["files_deleted"] = deleted

            # 下载刮削资源文件
            if task.download_metadata and media_dirs:
                logger.info(f"Starting metadata download for {len(media_dirs)} directories")
                meta_downloaded, meta_skipped = await self._download_metadata_files(task, media_dirs)
                stats["metadata_downloaded"] = meta_downloaded
                stats["metadata_skipped"] = meta_skipped

            # 更新任务状态
            task.status = TaskStatus.SUCCESS
            task.last_run_status = "success"
            msg_parts = [
                f"新增: {stats['files_added']}",
                f"更新: {stats['files_updated']}",
                f"删除: {stats['files_deleted']}",
                f"跳过: {stats['files_skipped']}"
            ]
            if task.download_metadata:
                msg_parts.append(f"刮削下载: {stats['metadata_downloaded']}")
                msg_parts.append(f"刮削跳过: {stats['metadata_skipped']}")
            task.last_run_message = ", ".join(msg_parts)
            task.last_run_time = datetime.now()
            task.total_runs += 1
            await task.save()

            # 更新任务日志
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            await TaskLog.filter(id=log_id).update(
                end_time=end_time,
                duration=duration,
                status="success",
                message=task.last_run_message,
                files_scanned=stats["files_scanned"],
                files_added=stats["files_added"],
                files_updated=stats["files_updated"],
                files_deleted=stats["files_deleted"],
                files_skipped=stats["files_skipped"],
                metadata_downloaded=stats["metadata_downloaded"],
                metadata_skipped=stats["metadata_skipped"]
            )

        except Exception as e:
            logger.exception(f"Task execution failed: {e}")

            # 更新任务状态
            task.status = TaskStatus.ERROR
            task.last_run_status = "error"
            task.last_run_message = str(e)
            task.last_run_time = datetime.now()
            await task.save()

            # 更新任务日志
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            import traceback
            await TaskLog.filter(id=log_id).update(
                end_time=end_time,
                duration=duration,
                status="error",
                message=str(e),
                error_trace=traceback.format_exc(),
                files_scanned=stats["files_scanned"]
            )

            raise

        return stats

    async def _process_file(
            self,
            task: StrmTask,
            file_info: FileInfo,
            file_path: str
    ) -> str:
        """
        处理单个文件
        
        Args:
            task: 任务配置
            file_info: 文件信息
            file_path: 文件路径
            
        Returns:
            处理结果: added, updated, skipped
        """
        # 获取 pick_code
        pick_code = file_info.pick_code
        if not pick_code:
            pick_code = await self.provider.to_pickcode(file_info.id)

        if not pick_code:
            raise ValueError(f"无法获取 pick_code: {file_info.name}")

        # 构建 STRM URL
        strm_url = self._build_strm_url(pick_code, task.base_url)

        # 构建 STRM 文件路径
        strm_path = self._build_strm_path(
            task.output_dir,
            file_path,
            task.preserve_structure
        )

        # 检查是否已存在记录
        record_id = f"{task.id}_{file_info.id}"
        existing_record = await StrmRecord.filter(id=record_id).first()

        if existing_record:
            # 检查是否需要更新
            if not task.overwrite_strm:
                return "skipped"

            # 更新记录
            existing_record.pick_code = pick_code
            existing_record.strm_content = strm_url
            await existing_record.save()

            # 更新文件
            strm_path.write_text(strm_url, encoding='utf-8')

            return "updated"

        # 创建新记录
        # 确保父目录存在
        strm_path.parent.mkdir(parents=True, exist_ok=True)

        # 写入 STRM 文件
        strm_path.write_text(strm_url, encoding='utf-8')

        # 创建数据库记录
        await StrmRecord.create(
            id=record_id,
            task=task,
            file_id=file_info.id,
            pick_code=pick_code,
            file_name=file_info.name,
            file_size=file_info.size,
            file_path=file_path,
            strm_path=str(strm_path),
            strm_content=strm_url,
            status="active"
        )

        return "added"

    async def _cleanup_orphan_records(
            self,
            task: StrmTask,
            current_file_ids: set
    ) -> int:
        """
        清理孤立记录
        
        Args:
            task: 任务
            current_file_ids: 当前存在的文件 ID 集合
            
        Returns:
            删除的记录数
        """
        # 获取所有活跃记录
        records = await StrmRecord.filter(
            task=task,
            status="active"
        ).all()

        deleted_count = 0
        for record in records:
            if record.file_id not in current_file_ids:
                # 删除物理文件
                try:
                    path = Path(record.strm_path)
                    if path.exists():
                        path.unlink()
                except Exception as e:
                    logger.error(f"Failed to delete STRM file: {e}")

                # 更新记录状态
                record.status = "deleted"
                await record.save()

                deleted_count += 1

        return deleted_count

    async def get_stream_url(self, pick_code: str, id: int, user_agent: str) -> Optional[str]:
        """
        获取流媒体 URL（用于 302 重定向）

        Args:
            pick_code: 文件的 pick_code

        Returns:
            下载链接
        """
        return await self.provider.get_download_url(pick_code, id, user_agent)

    async def _download_metadata_files(
            self,
            task: StrmTask,
            media_dirs: Dict[str, str]
    ) -> tuple:
        """
        下载刮削资源文件

        Args:
            task: STRM 任务
            media_dirs: 包含媒体文件的目录 {parent_id: parent_path}

        Returns:
            (downloaded_count, skipped_count)
        """
        downloaded_count = 0
        skipped_count = 0

        for dir_id, dir_path in media_dirs.items():
            try:
                # 列出目录内所有文件
                files, _ = await self.provider.list_files(dir_id, limit=1000)

                for file_info in files:
                    # 跳过文件夹
                    if file_info.is_dir:
                        continue

                    # 检查是否为刮削资源文件
                    if not self._is_metadata_file(file_info.name):
                        continue

                    # 构建本地保存路径
                    if task.preserve_structure:
                        local_path = Path(task.output_dir) / dir_path / file_info.name
                    else:
                        local_path = Path(task.output_dir) / file_info.name

                    # 检查文件是否已存在
                    if local_path.exists() and not task.overwrite_strm:
                        logger.debug(f"Metadata file already exists, skipping: {local_path}")
                        skipped_count += 1
                        continue

                    # 获取 pick_code
                    pick_code = file_info.pick_code
                    if not pick_code:
                        pick_code = await self.provider.to_pickcode(file_info.id)

                    if not pick_code:
                        logger.warning(f"Cannot get pick_code for metadata file: {file_info.name}")
                        continue

                    # 下载文件
                    success = await self.provider.download_file(
                        pick_code=pick_code,
                        file_id=int(file_info.id),
                        output_path=local_path,
                        user_agent=None
                    )

                    if success:
                        downloaded_count += 1
                        logger.info(f"Downloaded metadata file: {file_info.name} -> {local_path}")
                    else:
                        logger.warning(f"Failed to download metadata file: {file_info.name}")

            except Exception as e:
                logger.exception(f"Error downloading metadata files from directory {dir_id}: {e}")

        logger.info(f"Metadata download completed: downloaded={downloaded_count}, skipped={skipped_count}")
        return downloaded_count, skipped_count
