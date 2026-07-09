from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import require_admin
from ..mihomo.manager import get_manager
from ..models import Rule
from ..schemas import MessageResponse, RuleCreate, RuleOut, RuleUpdate

logger = logging.getLogger("proxy_manager")

router = APIRouter(prefix="/api/rules", tags=["规则路由"])


@router.get("", response_model=list[RuleOut])
def list_rules(db: Session = Depends(get_db)) -> list[Rule]:
    """列出全部自定义规则。"""
    return db.query(Rule).order_by(Rule.priority.desc(), Rule.id.asc()).all()


@router.post("", response_model=RuleOut)
def create_rule(payload: RuleCreate, db: Session = Depends(get_db), _=Depends(require_admin)) -> Rule:
    """新增规则。"""
    rule = Rule(
        name=payload.name,
        rule_type=payload.rule_type,
        value=payload.value,
        target=payload.target,
        enabled=payload.enabled,
        priority=payload.priority,
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    get_manager().reload(db)
    logger.info("新增规则: %s (%s,%s,%s)", rule.name, rule.rule_type, rule.value, rule.target)
    return rule


@router.put("/{rule_id}", response_model=RuleOut)
def update_rule(rule_id: int, payload: RuleUpdate, db: Session = Depends(get_db), _=Depends(require_admin)) -> Rule:
    """更新规则。"""
    rule = db.query(Rule).filter(Rule.id == rule_id).one_or_none()
    if rule is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"规则不存在: id={rule_id}")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(rule, k, v)
    db.commit()
    db.refresh(rule)
    get_manager().reload(db)
    return rule


@router.delete("/{rule_id}", response_model=MessageResponse)
def delete_rule(rule_id: int, db: Session = Depends(get_db), _=Depends(require_admin)) -> MessageResponse:
    """删除规则。"""
    rule = db.query(Rule).filter(Rule.id == rule_id).one_or_none()
    if rule is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"规则不存在: id={rule_id}")
    db.delete(rule)
    db.commit()
    get_manager().reload(db)
    return MessageResponse(message="规则已删除")
