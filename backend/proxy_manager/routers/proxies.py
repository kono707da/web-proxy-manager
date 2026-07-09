from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import require_admin
from ..mihomo.client import MihomoAPIError
from ..mihomo.manager import get_manager
from ..schemas import DelayTestResponse, MessageResponse, ProxyGroupOut, ProxyOut, SelectProxyRequest

logger = logging.getLogger("proxy_manager")

router = APIRouter(prefix="/api/proxies", tags=["代理节点"])

_GROUP_TYPES = {"Selector", "URLTest", "Fallback", "LoadBalance", "Relay"}


def _ensure_running() -> None:
    mgr = get_manager()
    if not mgr.is_running():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="mihomo 未运行，请先在系统设置中启动")


@router.get("")
def list_proxies(db: Session = Depends(get_db)) -> dict:
    """列出全部代理节点与分组。"""
    _ensure_running()
    try:
        data = get_manager().client.get_proxies()
    except MihomoAPIError as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"获取代理列表失败: {e}")
    raw = data.get("proxies", {}) or {}
    proxies: list[ProxyOut] = []
    groups: list[ProxyGroupOut] = []
    for name, info in raw.items():
        if name in ("DIRECT", "REJECT", "PASS", "GLOBAL"):
            continue
        ptype = info.get("type", "")
        if ptype in _GROUP_TYPES:
            groups.append(ProxyGroupOut(
                name=name,
                type=ptype,
                now=info.get("now"),
                all=info.get("all", []) or [],
            ))
        else:
            proxies.append(ProxyOut(
                name=name,
                type=ptype,
                udp=info.get("udp", False),
                history=info.get("history", []) or [],
                alive=info.get("alive", False),
            ))
    return {"proxies": proxies, "groups": groups}


@router.get("/groups", response_model=list[ProxyGroupOut])
def list_groups(db: Session = Depends(get_db)) -> list[ProxyGroupOut]:
    """仅列出代理分组。"""
    _ensure_running()
    try:
        data = get_manager().client.get_proxies()
    except MihomoAPIError as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"获取分组失败: {e}")
    raw = data.get("proxies", {}) or {}
    groups: list[ProxyGroupOut] = []
    for name, info in raw.items():
        if info.get("type", "") in _GROUP_TYPES:
            groups.append(ProxyGroupOut(
                name=name,
                type=info.get("type"),
                now=info.get("now"),
                all=info.get("all", []) or [],
            ))
    return groups


@router.put("/{group}/select", response_model=MessageResponse)
def select_proxy(group: str, payload: SelectProxyRequest, _=Depends(require_admin)) -> MessageResponse:
    """在代理组中选择节点。"""
    _ensure_running()
    try:
        get_manager().client.select_proxy(group, payload.name)
        return MessageResponse(message=f"已切换 {group} -> {payload.name}")
    except MihomoAPIError as e:
        logger.error("切换节点失败 %s/%s: %s", group, payload.name, e, exc_info=True)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"切换节点失败: {e}")


@router.get("/{name}/delay", response_model=DelayTestResponse)
def test_delay(name: str, _=Depends(require_admin)) -> DelayTestResponse:
    """测试节点延迟。"""
    _ensure_running()
    delay = get_manager().client.test_delay(name)
    return DelayTestResponse(name=name, delay=delay)
