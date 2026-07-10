from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, status

from ..deps import require_admin
from ..log_handler import MemoryLogHandler
from ..mihomo.manager import get_manager

logger = logging.getLogger("proxy_manager")

router = APIRouter(prefix="/api/logs", tags=["日志"])


@router.get("/app")
def get_app_logs(
    tail: int = Query(200, ge=1, le=2000, description="返回最近的日志条数"),
    level: str | None = Query(None, description="最低日志级别: DEBUG/INFO/WARNING/ERROR"),
    keyword: str | None = Query(None, description="关键词过滤"),
    _=Depends(require_admin),
) -> dict:
    """返回应用（Python）内存日志。"""
    handler = MemoryLogHandler.get_instance()
    logs = handler.get_logs(tail=tail, level=level, keyword=keyword)
    return {"source": "app", "total": len(logs), "logs": logs}


@router.get("/mihomo")
def get_mihomo_logs(
    tail: int = Query(200, ge=1, le=5000, description="返回最近的日志行数"),
    keyword: str | None = Query(None, description="关键词过滤"),
    _=Depends(require_admin),
) -> dict:
    """读取 mihomo 日志文件尾部。"""
    mgr = get_manager()
    log_path: Path = mgr._log_path
    if not log_path.exists():
        return {"source": "mihomo", "total": 0, "logs": [], "message": f"日志文件不存在: {log_path}"}
    try:
        # 读取文件全部内容后取尾部行（mihomo 日志不会太大）
        text = log_path.read_text(encoding="utf-8", errors="replace")
        lines = text.splitlines()
        if keyword:
            kw = keyword.lower()
            lines = [ln for ln in lines if kw in ln.lower()]
        if tail > 0:
            lines = lines[-tail:]
        # 尝试解析每行为结构化条目
        parsed: list[dict] = []
        for ln in lines:
            parsed.append({"line": ln})
        return {"source": "mihomo", "total": len(parsed), "logs": parsed}
    except Exception as e:
        logger.error("读取 mihomo 日志失败: %s", e, exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"读取日志失败: {e}")


@router.get("")
def get_all_logs(
    tail: int = Query(200, ge=1, le=2000),
    level: str | None = Query(None),
    keyword: str | None = Query(None),
    _=Depends(require_admin),
) -> dict:
    """同时返回应用日志和 mihomo 日志。"""
    # 应用日志
    handler = MemoryLogHandler.get_instance()
    app_logs = handler.get_logs(tail=tail, level=level, keyword=keyword)
    # mihomo 日志
    mgr = get_manager()
    mihomo_logs: list[dict] = []
    mihomo_msg = ""
    log_path: Path = mgr._log_path
    if log_path.exists():
        try:
            text = log_path.read_text(encoding="utf-8", errors="replace")
            lines = text.splitlines()
            if keyword:
                kw = keyword.lower()
                lines = [ln for ln in lines if kw in ln.lower()]
            if tail > 0:
                lines = lines[-tail:]
            mihomo_logs = [{"line": ln} for ln in lines]
        except Exception as e:
            mihomo_msg = f"读取失败: {e}"
    else:
        mihomo_msg = "日志文件不存在（mihomo 可能未启动过）"
    return {
        "app": {"total": len(app_logs), "logs": app_logs},
        "mihomo": {"total": len(mihomo_logs), "logs": mihomo_logs, "message": mihomo_msg},
    }
