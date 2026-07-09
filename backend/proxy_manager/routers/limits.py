from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import require_admin
from ..mihomo.manager import get_manager
from ..models import SpeedLimit
from ..schemas import MessageResponse, SpeedLimitCreate, SpeedLimitOut, SpeedLimitUpdate

logger = logging.getLogger("proxy_manager")

router = APIRouter(prefix="/api/limits", tags=["限速"])

_VALID_SCOPES = {"global", "group", "client"}


@router.get("", response_model=list[SpeedLimitOut])
def list_limits(db: Session = Depends(get_db)) -> list[SpeedLimit]:
    """列出全部限速规则。"""
    return db.query(SpeedLimit).order_by(SpeedLimit.id.asc()).all()


@router.post("", response_model=SpeedLimitOut)
def create_limit(payload: SpeedLimitCreate, db: Session = Depends(get_db), _=Depends(require_admin)) -> SpeedLimit:
    """新增限速规则。"""
    if payload.scope not in _VALID_SCOPES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"scope 必须为 {sorted(_VALID_SCOPES)} 之一")
    lim = SpeedLimit(
        name=payload.name,
        scope=payload.scope,
        target=payload.target,
        download_limit=payload.download_limit,
        upload_limit=payload.upload_limit,
        enabled=payload.enabled,
    )
    db.add(lim)
    db.commit()
    db.refresh(lim)
    get_manager().reload(db)
    logger.info("新增限速规则: %s (scope=%s, dl=%d, ul=%d)", lim.name, lim.scope, lim.download_limit, lim.upload_limit)
    return lim


@router.put("/{lim_id}", response_model=SpeedLimitOut)
def update_limit(lim_id: int, payload: SpeedLimitUpdate, db: Session = Depends(get_db), _=Depends(require_admin)) -> SpeedLimit:
    """更新限速规则。"""
    lim = db.query(SpeedLimit).filter(SpeedLimit.id == lim_id).one_or_none()
    if lim is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"限速规则不存在: id={lim_id}")
    data = payload.model_dump(exclude_unset=True)
    if "scope" in data and data["scope"] not in _VALID_SCOPES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"scope 必须为 {sorted(_VALID_SCOPES)} 之一")
    for k, v in data.items():
        setattr(lim, k, v)
    db.commit()
    db.refresh(lim)
    get_manager().reload(db)
    return lim


@router.delete("/{lim_id}", response_model=MessageResponse)
def delete_limit(lim_id: int, db: Session = Depends(get_db), _=Depends(require_admin)) -> MessageResponse:
    """删除限速规则。"""
    lim = db.query(SpeedLimit).filter(SpeedLimit.id == lim_id).one_or_none()
    if lim is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"限速规则不存在: id={lim_id}")
    db.delete(lim)
    db.commit()
    get_manager().reload(db)
    return MessageResponse(message="限速规则已删除")
