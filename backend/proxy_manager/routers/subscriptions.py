from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import require_admin
from ..mihomo import config_builder
from ..mihomo.manager import get_manager
from ..models import Subscription, User
from ..schemas import MessageResponse, SubscriptionCreate, SubscriptionOut, SubscriptionUpdate

logger = logging.getLogger("proxy_manager")

router = APIRouter(prefix="/api/subscriptions", tags=["订阅"])


@router.get("", response_model=list[SubscriptionOut])
def list_subscriptions(db: Session = Depends(get_db)) -> list[Subscription]:
    """列出全部订阅。"""
    return db.query(Subscription).order_by(Subscription.id.asc()).all()


@router.post("", response_model=SubscriptionOut)
def create_subscription(payload: SubscriptionCreate, db: Session = Depends(get_db), _=Depends(require_admin)) -> Subscription:
    """新增订阅。"""
    sub = Subscription(
        name=payload.name,
        url=payload.url,
        enabled=payload.enabled,
        auto_update=payload.auto_update,
        update_interval=payload.update_interval,
    )
    db.add(sub)
    db.commit()
    db.refresh(sub)
    logger.info("新增订阅: %s", sub.name)
    return sub


@router.put("/{sub_id}", response_model=SubscriptionOut)
def update_subscription(sub_id: int, payload: SubscriptionUpdate, db: Session = Depends(get_db), _=Depends(require_admin)) -> Subscription:
    """更新订阅。"""
    sub = db.query(Subscription).filter(Subscription.id == sub_id).one_or_none()
    if sub is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"订阅不存在: id={sub_id}")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(sub, k, v)
    db.commit()
    db.refresh(sub)
    try:
        get_manager().reload(db)
    except Exception as e:
        logger.warning("订阅更新后 reload 失败（数据已保存）: %s", e)
    return sub


@router.delete("/{sub_id}", response_model=MessageResponse)
def delete_subscription(sub_id: int, db: Session = Depends(get_db), _=Depends(require_admin)) -> MessageResponse:
    """删除订阅。"""
    sub = db.query(Subscription).filter(Subscription.id == sub_id).one_or_none()
    if sub is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"订阅不存在: id={sub_id}")
    # 清理缓存文件
    cache = config_builder.SUB_CACHE_DIR / f"{sub_id}.yaml"
    if cache.exists():
        cache.unlink()
    db.delete(sub)
    db.commit()
    logger.info("删除订阅: %s", sub.name)
    get_manager().reload(db)
    return MessageResponse(message="订阅已删除")


@router.post("/{sub_id}/update", response_model=SubscriptionOut)
def update_subscription_now(
    sub_id: int,
    use_proxy: bool = False,
    db: Session = Depends(get_db),
    _=Depends(require_admin),
) -> Subscription:
    """立即拉取并更新订阅节点。

    - use_proxy=true: 通过 mihomo 的 mixed-port 代理拉取，需先在设备管理中添加本机（127.0.0.1）
      并分配节点，再开启系统代理指向 mihomo 端口，流量才会经分配的节点代理。
    """
    sub = db.query(Subscription).filter(Subscription.id == sub_id).one_or_none()
    if sub is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"订阅不存在: id={sub_id}")
    try:
        proxies = config_builder.fetch_subscription(sub.url, use_proxy=use_proxy)
    except Exception as e:
        sub.last_error = str(e)
        sub.last_update = datetime.now(timezone.utc)
        db.commit()
        db.refresh(sub)
        logger.error("订阅 %s 更新失败: %s", sub.name, e, exc_info=True)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"订阅更新失败: {e}")
    config_builder.save_subscription_cache(sub.id, proxies)
    sub.node_count = len(proxies)
    sub.last_update = datetime.now(timezone.utc)
    sub.last_error = None
    db.commit()
    db.refresh(sub)
    try:
        get_manager().reload(db)
    except Exception as e:
        logger.warning("订阅更新后 reload 失败（数据已保存）: %s", e)
    logger.info("订阅 %s 更新成功，节点数=%d (use_proxy=%s)", sub.name, sub.node_count, use_proxy)
    return sub


@router.post("/update-all", response_model=MessageResponse)
def update_all_subscriptions(
    use_proxy: bool = False,
    db: Session = Depends(get_db),
    _=Depends(require_admin),
) -> MessageResponse:
    """拉取更新所有已启用订阅。

    - use_proxy=true: 通过 mihomo 的 mixed-port 代理拉取，需先在设备管理中添加本机（127.0.0.1）
      并分配节点，再开启系统代理指向 mihomo 端口，流量才会经分配的节点代理。
    """
    subs = db.query(Subscription).filter(Subscription.enabled.is_(True)).all()
    ok, fail = 0, 0
    for sub in subs:
        try:
            proxies = config_builder.fetch_subscription(sub.url, use_proxy=use_proxy)
            config_builder.save_subscription_cache(sub.id, proxies)
            sub.node_count = len(proxies)
            sub.last_update = datetime.now(timezone.utc)
            sub.last_error = None
            ok += 1
        except Exception as e:
            sub.last_error = str(e)
            sub.last_update = datetime.now(timezone.utc)
            fail += 1
            logger.error("订阅 %s 更新失败: %s", sub.name, e, exc_info=True)
    db.commit()
    try:
        get_manager().reload(db)
    except Exception as e:
        logger.warning("订阅批量更新后 reload 失败（数据已保存）: %s", e)
    return MessageResponse(message=f"更新完成: 成功 {ok} 个, 失败 {fail} 个", detail=f"成功 {ok}, 失败 {fail}")
