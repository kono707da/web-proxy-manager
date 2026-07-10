from __future__ import annotations

import logging
import time

import psutil
from fastapi import APIRouter, Depends, HTTPException, status

from .. import __version__
from ..deps import require_admin
from ..mihomo.client import MihomoAPIError
from ..mihomo.manager import get_manager
from ..schemas import LogLevelUpdateRequest, MessageResponse, MihomoStatusResponse, ModeUpdateRequest, SystemInfoResponse

logger = logging.getLogger("proxy_manager")

router = APIRouter(prefix="/api/system", tags=["系统"])


@router.get("/status", response_model=MihomoStatusResponse)
def get_status() -> MihomoStatusResponse:
    """获取 mihomo 内核运行状态。"""
    data = get_manager().get_status()
    return MihomoStatusResponse(**data)


@router.get("/info", response_model=SystemInfoResponse)
def get_info() -> SystemInfoResponse:
    """获取系统资源占用信息。"""
    mgr = get_manager()
    try:
        proc = psutil.Process()
        cpu = proc.cpu_percent(interval=0.1)
        mem_mb = proc.memory_info().rss / 1024 / 1024
    except Exception:
        cpu, mem_mb = 0.0, 0.0
    try:
        disk_mb = psutil.disk_usage("/").used / 1024 / 1024
    except Exception:
        disk_mb = 0.0
    return SystemInfoResponse(
        version=__version__,
        mihomo=MihomoStatusResponse(**mgr.get_status()),
        cpu_percent=round(cpu, 1),
        memory_mb=round(mem_mb, 1),
        disk_mb=round(disk_mb, 1),
    )


@router.post("/start", response_model=MessageResponse)
def start_core(_=Depends(require_admin)) -> MessageResponse:
    """启动 mihomo 内核。"""
    mgr = get_manager()
    if mgr.is_running():
        return MessageResponse(message="mihomo 已在运行")
    mgr.start()
    time.sleep(1)
    if mgr.is_running():
        return MessageResponse(message="mihomo 已启动")
    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"启动失败: {mgr._last_error or '未知错误'}")


@router.post("/stop", response_model=MessageResponse)
def stop_core(_=Depends(require_admin)) -> MessageResponse:
    """停止 mihomo 内核。"""
    get_manager().stop()
    return MessageResponse(message="mihomo 已停止")


@router.post("/restart", response_model=MessageResponse)
def restart_core(_=Depends(require_admin)) -> MessageResponse:
    """重启 mihomo 内核。"""
    mgr = get_manager()
    mgr.restart()
    time.sleep(1)
    if mgr.is_running():
        return MessageResponse(message="mihomo 已重启")
    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"重启失败: {mgr._last_error or '未知错误'}")


@router.post("/reload", response_model=MessageResponse)
def reload_core(_=Depends(require_admin)) -> MessageResponse:
    """热重载 mihomo 配置。"""
    try:
        get_manager().reload()
        return MessageResponse(message="配置已重载")
    except Exception as e:
        logger.error("重载失败: %s", e, exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"重载失败: {e}")


@router.patch("/mode", response_model=MessageResponse)
def update_mode(payload: ModeUpdateRequest, _=Depends(require_admin)) -> MessageResponse:
    """切换代理模式: rule / global / direct。"""
    if payload.mode not in ("rule", "global", "direct"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="模式必须为 rule/global/direct")
    mgr = get_manager()
    if not mgr.is_running():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="mihomo 未运行，请先启动")
    try:
        mgr.client.patch_configs({"mode": payload.mode})
        return MessageResponse(message=f"模式已切换为 {payload.mode}")
    except MihomoAPIError as e:
        logger.error("切换模式失败: %s", e, exc_info=True)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"切换模式失败: {e}")


@router.patch("/log-level", response_model=MessageResponse)
def update_log_level(payload: LogLevelUpdateRequest, _=Depends(require_admin)) -> MessageResponse:
    """切换日志级别。"""
    if payload.level not in ("debug", "info", "warning", "error", "silent"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="日志级别非法")
    mgr = get_manager()
    if not mgr.is_running():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="mihomo 未运行，请先启动")
    try:
        mgr.client.patch_configs({"log-level": payload.level})
        return MessageResponse(message=f"日志级别已切换为 {payload.level}")
    except MihomoAPIError as e:
        logger.error("切换日志级别失败: %s", e, exc_info=True)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"切换日志级别失败: {e}")
