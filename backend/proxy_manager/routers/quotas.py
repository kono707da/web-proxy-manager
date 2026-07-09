from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import require_admin
from ..mihomo.manager import get_manager
from ..models import TrafficQuota, TrafficStat
from ..schemas import MessageResponse, QuotaCreate, QuotaOut, QuotaUpdate

logger = logging.getLogger("proxy_manager")

router = APIRouter(prefix="/api/quotas", tags=["流量配额"])

_VALID_SCOPES = {"client", "group"}
_VALID_PERIODS = {"total", "daily", "monthly"}


@router.get("", response_model=list[QuotaOut])
def list_quotas(db: Session = Depends(get_db)) -> list[TrafficQuota]:
    """列出全部流量配额。"""
    return db.query(TrafficQuota).order_by(TrafficQuota.id.asc()).all()


@router.post("", response_model=QuotaOut)
def create_quota(payload: QuotaCreate, db: Session = Depends(get_db), _=Depends(require_admin)) -> TrafficQuota:
    """新增流量配额。"""
    if payload.scope not in _VALID_SCOPES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"scope 必须为 {sorted(_VALID_SCOPES)} 之一")
    if payload.period not in _VALID_PERIODS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"period 必须为 {sorted(_VALID_PERIODS)} 之一")
    q = TrafficQuota(
        name=payload.name,
        scope=payload.scope,
        target=payload.target,
        quota_bytes=payload.quota_bytes,
        period=payload.period,
        reset_day=max(1, min(28, payload.reset_day)),
        enabled=payload.enabled,
    )
    db.add(q)
    db.commit()
    db.refresh(q)
    get_manager().reload(db)
    logger.info("新增配额: %s (target=%s, quota=%d)", q.name, q.target, q.quota_bytes)
    return q


@router.put("/{q_id}", response_model=QuotaOut)
def update_quota(q_id: int, payload: QuotaUpdate, db: Session = Depends(get_db), _=Depends(require_admin)) -> TrafficQuota:
    """更新配额。"""
    q = db.query(TrafficQuota).filter(TrafficQuota.id == q_id).one_or_none()
    if q is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"配额不存在: id={q_id}")
    data = payload.model_dump(exclude_unset=True)
    if "period" in data and data["period"] not in _VALID_PERIODS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"period 必须为 {sorted(_VALID_PERIODS)} 之一")
    if "reset_day" in data:
        data["reset_day"] = max(1, min(28, data["reset_day"]))
    for k, v in data.items():
        setattr(q, k, v)
    db.commit()
    db.refresh(q)
    get_manager().reload(db)
    return q


@router.delete("/{q_id}", response_model=MessageResponse)
def delete_quota(q_id: int, db: Session = Depends(get_db), _=Depends(require_admin)) -> MessageResponse:
    """删除配额。"""
    q = db.query(TrafficQuota).filter(TrafficQuota.id == q_id).one_or_none()
    if q is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"配额不存在: id={q_id}")
    db.delete(q)
    db.commit()
    get_manager().reload(db)
    return MessageResponse(message="配额已删除")


@router.post("/{q_id}/reset", response_model=MessageResponse)
def reset_quota_usage(q_id: int, db: Session = Depends(get_db), _=Depends(require_admin)) -> MessageResponse:
    """重置指定配额的已用流量。"""
    q = db.query(TrafficQuota).filter(TrafficQuota.id == q_id).one_or_none()
    if q is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"配额不存在: id={q_id}")
    stat = db.query(TrafficStat).filter(TrafficStat.client_ip == q.target).first()
    if stat:
        stat.upload_total = 0
        stat.download_total = 0
        stat.total_bytes = 0
    q.used_bytes = 0
    q.blocked = False
    db.commit()
    get_manager().reload(db)
    return MessageResponse(message="配额用量已重置")
