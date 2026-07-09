from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import require_admin
from ..mihomo.manager import get_manager
from ..models import TrafficStat
from ..schemas import MemorySnapshot, MessageResponse, TrafficSnapshot, TrafficStatOut

logger = logging.getLogger("proxy_manager")

router = APIRouter(prefix="/api/traffic", tags=["流量统计"])


@router.get("/realtime", response_model=TrafficSnapshot)
def realtime_traffic() -> TrafficSnapshot:
    """实时上下行速度（B/s，来自 mihomo /traffic 缓存）。"""
    data = get_manager().get_realtime_traffic()
    return TrafficSnapshot(up=data.get("up", 0), down=data.get("down", 0))


@router.get("/memory", response_model=MemorySnapshot)
def memory_usage() -> MemorySnapshot:
    """mihomo 内存占用。"""
    data = get_manager().get_memory()
    return MemorySnapshot(inuse=data.get("inuse", 0), oslimit=data.get("oslimit", 0))


@router.get("/stats", response_model=list[TrafficStatOut])
def list_traffic_stats(db: Session = Depends(get_db)) -> list[TrafficStat]:
    """按客户端 IP 的累计流量统计。"""
    return db.query(TrafficStat).order_by(TrafficStat.total_bytes.desc()).all()


@router.delete("/stats", response_model=MessageResponse)
def reset_traffic_stats(db: Session = Depends(get_db), _=Depends(require_admin)) -> MessageResponse:
    """重置所有累计流量统计。"""
    deleted = db.query(TrafficStat).delete()
    db.commit()
    get_manager().reload(db)
    return MessageResponse(message=f"已重置流量统计，清除 {deleted} 条记录")
