"""
WebDAV 服务实现
提供 115 网盘的 WebDAV 访问接口，无需 FUSE 支持
"""
import os
import logging
import time
from datetime import datetime
from typing import Optional, Dict, Any, List
from xml.etree import ElementTree as ET
from urllib.parse import quote

from fastapi import Request, Response, HTTPException
from fastapi.responses import StreamingResponse
import httpx

from p115client import P115Client

logger = logging.getLogger(__name__)

# WebDAV XML 命名空间
DAV_NS = "DAV:"
NSMAP = {"D": DAV_NS}


def dav_tag(name: str) -> str:
    """生成 DAV 命名空间标签"""
    return f"{{{DAV_NS}}}{name}"


class WebDAVProvider:
    """
    WebDAV 服务提供者
    将 115 网盘映射为 WebDAV 接口
    """

    def __init__(self, client: P115Client, drive_id: str, root_cid: str = "0"):
        self.client = client
        self.drive_id = drive_id
        self.root_cid = root_cid
        # 缓存: path -> file_info
        self._cache: Dict[str, Any] = {}
        self._cache_time: Dict[str, float] = {}
        self._cache_ttl = 60  # 缓存 60 秒
        # HTTP 客户端
        self._http_client = httpx.AsyncClient(follow_redirects=True, timeout=30.0)
        # 初始化根目录缓存
        self._cache["/"] = {
            "id": root_cid,
            "name": "",
            "is_dir": True,
            "size": 0,
            "mtime": datetime.now().timestamp()
        }
        self._cache_time["/"] = time.time()

    async def close(self):
        """关闭资源"""
        await self._http_client.aclose()

    def _is_cache_valid(self, path: str) -> bool:
        """检查缓存是否有效"""
        if path not in self._cache_time:
            return False
        return time.time() - self._cache_time[path] < self._cache_ttl

    def _set_cache(self, path: str, info: Any):
        """设置缓存"""
        self._cache[path] = info
        self._cache_time[path] = time.time()

    async def get_file_info(self, path: str) -> Optional[Dict[str, Any]]:
        """获取文件/目录信息"""
        path = path.rstrip("/") or "/"
        logger.debug(f"[WebDAV] get_file_info: path={path}")

        # 检查缓存
        if self._is_cache_valid(path):
            logger.debug(f"[WebDAV] Cache hit for {path}")
            return self._cache.get(path)

        # 根目录
        if path == "/":
            info = {
                "id": self.root_cid,
                "name": "",
                "is_dir": True,
                "size": 0,
                "mtime": datetime.now().timestamp()
            }
            self._set_cache(path, info)
            return info

        # 查找父目录并列出内容
        parent_path = os.path.dirname(path)
        if parent_path == path:
            return None

        # 先确保父目录信息存在
        parent_info = self._cache.get(parent_path)
        if not parent_info:
            parent_info = await self.get_file_info(parent_path)

        if not parent_info or not parent_info.get("is_dir"):
            logger.warning(f"[WebDAV] Parent not found or not a directory: {parent_path}")
            return None

        # 列出父目录内容来获取当前文件信息
        await self._list_directory_internal(parent_path, parent_info["id"])

        return self._cache.get(path)

    async def _list_directory_internal(self, path: str, cid: str) -> List[Dict[str, Any]]:
        """内部方法：列出目录内容"""
        logger.info(f"[WebDAV] Listing directory: path={path}, cid={cid}")

        try:
            resp = self.client.fs_files(cid, limit=10000)
            logger.debug(f"[WebDAV] fs_files response state: {resp.get('state')}, count: {resp.get('count', 0)}")

            if not resp.get("state"):
                logger.error(f"[WebDAV] Failed to list directory {path}: {resp.get('error')}")
                return []

            files = resp.get("data", [])
            logger.info(f"[WebDAV] Found {len(files)} items in {path}")
            result = []

            for item in files:
                name = item.get("n")
                if not name:
                    continue

                child_path = f"{path}/{name}" if path != "/" else f"/{name}"

                # 判断是否为目录
                is_dir = not bool(item.get("sha"))

                file_info = {
                    "id": str(item.get("cid")),
                    "name": name,
                    "is_dir": is_dir,
                    "size": int(item.get("s", 0)),
                    "pick_code": item.get("pc", ""),
                    "mtime": int(item.get("t", 0)) or datetime.now().timestamp()
                }

                self._set_cache(child_path, file_info)
                result.append(file_info)
                logger.debug(f"[WebDAV] Cached: {child_path} (is_dir={is_dir})")

            return result

        except Exception as e:
            logger.exception(f"[WebDAV] Error listing directory {path}: {e}")
            return []

    async def list_directory(self, path: str) -> List[Dict[str, Any]]:
        """列出目录内容"""
        path = path.rstrip("/") or "/"
        logger.info(f"[WebDAV] list_directory called: path={path}")

        info = await self.get_file_info(path)
        if not info:
            logger.warning(f"[WebDAV] Directory not found: {path}")
            return []

        if not info.get("is_dir"):
            logger.warning(f"[WebDAV] Not a directory: {path}")
            return []

        cid = info["id"]
        return await self._list_directory_internal(path, cid)

    async def get_download_url(self, path: str) -> Optional[str]:
        """获取文件下载链接"""
        info = await self.get_file_info(path)
        if not info or info.get("is_dir"):
            return None

        pick_code = info.get("pick_code")
        if not pick_code:
            return None

        try:
            url = self.client.download_url(pick_code, app="chrome")
            return url
        except Exception as e:
            logger.error(f"[WebDAV] Failed to get download URL for {path}: {e}")
            return None

    def build_propfind_response(self, path: str, info: Dict[str, Any], children: List[Dict[str, Any]] = None, depth: str = "0") -> str:
        """构建 PROPFIND 响应 XML"""
        multistatus = ET.Element(dav_tag("multistatus"))

        # 添加当前资源
        self._add_response_element(multistatus, path, info)

        # 如果 depth=1，添加子资源
        if depth == "1" and children:
            logger.info(f"[WebDAV] Adding {len(children)} children to response")
            for child in children:
                child_path = f"{path}/{child['name']}" if path != "/" else f"/{child['name']}"
                self._add_response_element(multistatus, child_path, child)

        xml_str = ET.tostring(multistatus, encoding="unicode", xml_declaration=True)
        logger.debug(f"[WebDAV] PROPFIND response length: {len(xml_str)}")
        return xml_str

    def _add_response_element(self, parent: ET.Element, path: str, info: Dict[str, Any]):
        """添加响应元素"""
        response = ET.SubElement(parent, dav_tag("response"))

        # href - 需要包含完整的 WebDAV 路径前缀
        href = ET.SubElement(response, dav_tag("href"))
        # URL 编码路径中的特殊字符，但保留斜杠
        full_path = f"/webdav/{self.drive_id}{path}"
        encoded_path = quote(full_path, safe="/:@")
        href.text = encoded_path

        # propstat
        propstat = ET.SubElement(response, dav_tag("propstat"))
        prop = ET.SubElement(propstat, dav_tag("prop"))

        # displayname
        displayname = ET.SubElement(prop, dav_tag("displayname"))
        displayname.text = info.get("name") or os.path.basename(path) or "/"

        # resourcetype
        resourcetype = ET.SubElement(prop, dav_tag("resourcetype"))
        if info.get("is_dir"):
            ET.SubElement(resourcetype, dav_tag("collection"))

        # getcontentlength
        if not info.get("is_dir"):
            contentlength = ET.SubElement(prop, dav_tag("getcontentlength"))
            contentlength.text = str(info.get("size", 0))

        # getlastmodified
        lastmodified = ET.SubElement(prop, dav_tag("getlastmodified"))
        mtime = info.get("mtime", datetime.now().timestamp())
        lastmodified.text = datetime.fromtimestamp(mtime).strftime("%a, %d %b %Y %H:%M:%S GMT")

        # status
        status = ET.SubElement(propstat, dav_tag("status"))
        status.text = "HTTP/1.1 200 OK"


class WebDAVHandler:
    """
    WebDAV 请求处理器
    """

    def __init__(self):
        # drive_id -> WebDAVProvider
        self._providers: Dict[str, WebDAVProvider] = {}

    def get_provider(self, drive_id: str, client: P115Client, root_cid: str = "0") -> WebDAVProvider:
        """获取或创建 WebDAV 提供者"""
        if drive_id not in self._providers:
            logger.info(f"[WebDAV] Creating new provider for drive_id={drive_id}")
            self._providers[drive_id] = WebDAVProvider(client, drive_id, root_cid)
        return self._providers[drive_id]

    async def handle_options(self, request: Request) -> Response:
        """处理 OPTIONS 请求"""
        return Response(
            status_code=200,
            headers={
                "Allow": "OPTIONS, GET, HEAD, PROPFIND",
                "DAV": "1, 2",
                "MS-Author-Via": "DAV"
            }
        )

    async def handle_propfind(self, provider: WebDAVProvider, path: str, depth: str = "0") -> Response:
        """处理 PROPFIND 请求"""
        logger.info(f"[WebDAV] PROPFIND: path={path}, depth={depth}")

        info = await provider.get_file_info(path)
        if not info:
            logger.warning(f"[WebDAV] PROPFIND: Not found: {path}")
            raise HTTPException(status_code=404, detail="Not Found")

        children = []
        if depth == "1" and info.get("is_dir"):
            logger.info(f"[WebDAV] PROPFIND: Listing children for {path}")
            children = await provider.list_directory(path)
            logger.info(f"[WebDAV] PROPFIND: Found {len(children)} children")

        xml_response = provider.build_propfind_response(path, info, children, depth)

        return Response(
            content=xml_response,
            status_code=207,
            media_type="application/xml; charset=utf-8"
        )

    async def handle_get(self, provider: WebDAVProvider, path: str) -> Response:
        """处理 GET 请求"""
        logger.info(f"[WebDAV] GET: path={path}")

        info = await provider.get_file_info(path)
        if not info:
            raise HTTPException(status_code=404, detail="Not Found")

        if info.get("is_dir"):
            # 目录返回简单的 HTML 列表
            children = await provider.list_directory(path)
            html = self._build_directory_html(path, children, provider.drive_id)
            return Response(content=html, media_type="text/html")

        # 文件：获取下载链接并重定向
        url = await provider.get_download_url(path)
        if not url:
            raise HTTPException(status_code=500, detail="Failed to get download URL")

        # 302 重定向到实际下载链接
        return Response(status_code=302, headers={"Location": url})

    def _build_directory_html(self, path: str, children: List[Dict[str, Any]], drive_id: str) -> str:
        """构建目录 HTML 页面"""
        html = f"""<!DOCTYPE html>
<html>
<head><title>Index of {path}</title></head>
<body>
<h1>Index of {path}</h1>
<hr>
<pre>
"""
        # 父目录链接
        if path != "/":
            parent = os.path.dirname(path.rstrip("/")) or "/"
            parent_href = f"/webdav/{drive_id}{parent}"
            html += f'<a href="{parent_href}">..</a>\n'

        for child in children:
            name = child["name"]
            display_name = name + "/" if child.get("is_dir") else name
            child_path = f"{path}/{name}" if path != "/" else f"/{name}"
            child_href = f"/webdav/{drive_id}{child_path}"
            size = child.get("size", 0) if not child.get("is_dir") else "-"
            html += f'<a href="{child_href}">{display_name}</a>    {size}\n'

        html += """</pre>
<hr>
</body>
</html>"""
        return html


# 全局处理器实例
webdav_handler = WebDAVHandler()
