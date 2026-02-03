"""
文件服务

封装基于 p115client 的文件操作
"""
import logging
from pathlib import Path
from typing import List, Optional, Callable, AsyncGenerator
from dataclasses import dataclass

from app.providers.p115 import P115Provider, FileInfo

logger = logging.getLogger(__name__)


@dataclass
class TraverseOptions:
    """遍历选项"""
    max_depth: int = -1  # 最大深度，-1 表示无限制
    include_folders: bool = False  # 是否包含文件夹
    file_filter: Optional[Callable[[FileInfo], bool]] = None  # 文件过滤函数


class FileService:
    """文件服务"""
    
    def __init__(self, provider: P115Provider):
        """
        初始化文件服务
        
        Args:
            provider: P115Provider 实例
        """
        self.provider = provider
    
    async def list_files(
        self, 
        cid: str = "0",
        limit: int = 100,
        offset: int = 0
    ) -> tuple[List[FileInfo], int]:
        """
        获取目录下的文件列表
        
        Args:
            cid: 文件夹 ID
            limit: 每页数量
            offset: 偏移量
            
        Returns:
            (文件列表, 总数)
        """
        return await self.provider.list_files(cid, limit, offset)
    
    async def get_file_info(self, file_id: str) -> Optional[FileInfo]:
        """
        获取文件信息
        
        Args:
            file_id: 文件 ID
            
        Returns:
            文件信息
        """
        return await self.provider.get_file_info(file_id)
    
    async def search_files(
        self, 
        keyword: str,
        cid: str = "0",
        limit: int = 100
    ) -> List[FileInfo]:
        """
        搜索文件
        
        Args:
            keyword: 搜索关键词
            cid: 搜索目录
            limit: 最大结果数
            
        Returns:
            文件列表
        """
        return await self.provider.search_files(keyword, cid, limit)
    
    async def traverse_folder(
        self,
        cid: str = "0",
        options: Optional[TraverseOptions] = None
    ) -> AsyncGenerator[tuple[FileInfo, str], None]:
        """
        遍历文件夹
        
        Args:
            cid: 起始文件夹 ID
            options: 遍历选项
            
        Yields:
            (文件信息, 文件路径) 元组
        """
        options = options or TraverseOptions()
        
        # 使用栈实现深度优先遍历
        # 栈元素: (folder_id, path, depth)
        stack = [(cid, "", 0)]
        
        while stack:
            folder_id, path, depth = stack.pop()
            
            # 检查深度限制
            if options.max_depth >= 0 and depth > options.max_depth:
                continue
            
            try:
                # 获取目录内容
                files, _ = await self.provider.list_files(folder_id, limit=1000)
                logger.info(f"Folder {folder_id}: found {len(files)} items")

                for file_info in files:
                    file_path = f"{path}/{file_info.name}" if path else file_info.name
                    logger.info(f"  Item: {file_info.name} is_dir={file_info.is_dir}")

                    if file_info.is_dir:
                        # 处理文件夹
                        if options.include_folders:
                            yield file_info, file_path

                        # 将子目录加入栈
                        stack.append((file_info.id, file_path, depth + 1))
                    else:
                        # 处理文件
                        if options.file_filter and not options.file_filter(file_info):
                            logger.info(f"    Filtered out: {file_info.name}")
                            continue

                        yield file_info, file_path
                        
            except Exception as e:
                logger.exception(f"Error traversing folder {folder_id}: {e}")
    
    async def get_folder_tree(
        self,
        cid: str = "0",
        max_depth: int = 3
    ) -> dict:
        """
        获取目录树结构
        
        Args:
            cid: 起始文件夹 ID
            max_depth: 最大深度
            
        Returns:
            目录树字典
        """
        folder_info = await self.get_file_info(cid)
        if not folder_info:
            return {}
        
        tree = {
            "id": cid,
            "name": folder_info.name if cid != "0" else "根目录",
            "children": []
        }
        
        if max_depth <= 0:
            return tree
        
        try:
            files, _ = await self.list_files(cid, limit=1000)
            
            for file_info in files:
                if file_info.is_dir:
                    child_tree = await self.get_folder_tree(
                        file_info.id,
                        max_depth - 1
                    )
                    if child_tree:
                        tree["children"].append(child_tree)
            
        except Exception as e:
            logger.exception(f"Error building folder tree: {e}")
        
        return tree
    
    async def get_download_url(
        self,
        pick_code: str,
        user_agent: Optional[str] = None
    ) -> Optional[str]:
        """
        获取文件下载链接
        
        Args:
            pick_code: 文件的 pick_code
            user_agent: 可选的 User-Agent
            
        Returns:
            下载链接
        """
        return await self.provider.get_download_url(pick_code, user_agent)
