from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status

from ..deps import require_admin
from ..mihomo.client import MihomoAPIError
from ..mihomo.manager import get_manager
from ..schemas import ConnectionListResponse, MessageResponse

logger = logging.getLogger("proxy_manager")

router = APIRouter(prefix="/api/connections", tags=["连接管理"])


def _ensure_running() -> None:
    mgr = get_manager()
    if not mgr.is_running():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="mihomo 未运行，请先在系统设置中启动")


@router.get("", response_model=ConnectionListResponse)
def list_connections() -> ConnectionListResponse:
    """列出当前所有连接及总流量。"""
    _ensure_running()
    try:
        data = get_manager().client.get_connections()
    except MihomoAPIError as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"获取连接列表失败: {e}")
    return ConnectionListResponse(
        downloadTotal=int(data.get("downloadTotal", 0)),
        uploadTotal=int(data.get("uploadTotal", 0)),
        connections=data.get("connections", []) or [],
        memory=int(data.get("memory", 0)),
    )


@router.delete("/{conn_id}", response_model=MessageResponse)
def close_connection(conn_id: str, _=Depends(require_admin)) -> MessageResponse:
    """关闭指定连接。"""
    _ensure_running()
    try:
        get_manager().client.close_connection(conn_id)
        return MessageResponse(message="连接已关闭")
    except MihomoAPIError as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"关闭连接失败: {e}")


@router.delete("", response_model=MessageResponse)
def close_all_connections(_=Depends(require_admin)) -> MessageResponse:
    """关闭所有连接。"""
    _ensure_running()
    try:
        get_manager().client.close_all_connections()
        return MessageResponse(message="已关闭所有连接")
    except MihomoAPIError as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"关闭所有连接失败: {e}")
