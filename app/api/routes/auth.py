"""
认证管理 API 路由

基于 p115client 的授权码登录流程
"""
import logging
from pathlib import Path
from typing import Optional

import httpx
from fastapi import APIRouter, HTTPException, status

from app.api.schemas import AuthExchange, DataResponse, ResponseBase
from app.services.drive_service import DriveService
from app.core.config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["认证管理"])

# 存储正在进行的认证会话
# 实际生产环境应该使用 Redis 等分布式存储
_auth_sessions = {}


def get_drive_service() -> DriveService:
    """获取 DriveService 实例"""
    settings = get_settings()
    return DriveService(settings.data_dir)


@router.get("/qrcode")
async def get_qrcode():
    """
    获取二维码认证信息
    
    返回用于扫码登录的参数
    """
    try:
        from p115client import P115Client
        
        # 获取二维码 token（无需创建客户端实例）
        resp = await P115Client.login_qrcode_token(async_=True)
        qrcode_info = resp.get("data", {})
        
        # 存储会话信息
        session_id = qrcode_info.get("uid", "")
        _auth_sessions[session_id] = {
            "qrcode_info": qrcode_info
        }
        
        # 使用 API 返回的二维码 URL
        uid = qrcode_info.get("uid", "")
        
        return {
            "success": True,
            "qrcode_url": qrcode_info.get("qrcode"),
            "uid": uid,
            "time": qrcode_info.get("time"),
            "sign": qrcode_info.get("sign"),
            "code_verifier": "",  # p115client 不需要这个字段，但为了兼容前端保留
        }
        
    except Exception as e:
        logger.exception("Failed to get QR code")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取二维码失败: {str(e)}"
        )


@router.get("/status")
async def check_auth_status(
    uid: str,
    time: str,
    sign: str
):
    """
    检查认证状态
    
    - 0: 等待扫码
    - 1: 已扫码，等待确认
    - 2: 已确认，可以交换 token
    """
    try:
        from p115client import P115Client
        
        # 检查状态（使用 HTTP 请求，非阻塞）
        import httpx
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://qrcodeapi.115.com/get/status/",
                params={"uid": uid, "time": time, "sign": sign},
                timeout=30
            )
            status_result = resp.json()
        
        status_code = status_result.get("data", {}).get("status", 0)
        status_map = {
            0: "等待扫码",
            1: "已扫码，等待确认",
            2: "已确认，可以交换 token"
        }
        
        return {
            "success": True,
            "status": status_code,
            "message": status_map.get(status_code, "未知状态")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to check auth status")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"检查状态失败: {str(e)}"
        )


@router.post("/exchange")
async def exchange_token(data: AuthExchange):
    """
    交换 Token
    
    扫码确认后调用此接口完成认证
    """
    try:
        from p115client import P115Client
        
        # 确定目标网盘
        drive_service = get_drive_service()
        
        if data.drive_id:
            # 为指定网盘认证
            from app.models.drive import Drive
            drive = await Drive.filter(id=data.drive_id).first()
            if not drive:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"网盘不存在: {data.drive_id}"
                )
        else:
            # 使用当前网盘或创建新的
            drive = await drive_service.get_current_drive()
            if not drive:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="没有可用的网盘，请先创建网盘"
                )
        
        # 获取扫码登录后的 cookie
        login_result = await P115Client.login_qrcode_scan_result(
            data.uid,
            app="web",
            async_=True
        )
        
        # 提取 cookie 数据（cookie 信息嵌套在 data.cookie 中）
        login_data = login_result.get("data", {})
        cookie_info = login_data.get("cookie", {})
        
        # 保存 cookie 到文件
        cookie_path = Path(drive.cookie_file)
        cookie_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 构造 cookie 字符串并保存（P115Client 需要的格式：UID=xxx; CID=xxx; SEID=xxx）
        cookie_items = []
        for k, v in cookie_info.items():
            if v:
                cookie_items.append(f"{k}={v}")
        cookie_str = "; ".join(cookie_items)
        
        # 写入文件（P115Client 读取时使用 latin-1 编码）
        cookie_path.write_bytes(cookie_str.encode('latin-1'))
        
        # 清理会话
        if data.uid in _auth_sessions:
            del _auth_sessions[data.uid]
        
        return {
            "success": True,
            "message": "认证成功",
            "access_token": "",  # p115client 使用 cookie 文件，不需要返回 token
            "expires_in": 0
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to exchange token")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"交换 Token 失败: {str(e)}"
        )


@router.post("/logout/{drive_id}", response_model=ResponseBase)
async def logout(drive_id: str):
    """退出登录（清除 Cookie）"""
    try:
        from app.models.drive import Drive
        
        drive = await Drive.filter(id=drive_id).first()
        if not drive:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"网盘不存在: {drive_id}"
            )
        
        # 删除 cookie 文件
        if drive.cookie_file:
            cookie_path = Path(drive.cookie_file)
            if cookie_path.exists():
                cookie_path.unlink()
        
        # 移除 provider
        from app.providers.p115 import provider_manager
        await provider_manager.remove_provider(drive_id)
        
        return ResponseBase(message="退出成功")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to logout")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"退出失败: {str(e)}"
        )
