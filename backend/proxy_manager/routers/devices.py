from __future__ import annotations

import logging
import re
from collections import defaultdict
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import require_admin
from ..mihomo.client import MihomoAPIError
from ..mihomo.manager import get_manager
from ..models import Device
from ..schemas import DeviceCreate, DeviceOut, DeviceUpdate, DiscoveredClient, MessageResponse

logger = logging.getLogger("proxy_manager")

router = APIRouter(prefix="/api/devices", tags=["设备管理"])

_IP_RE = re.compile(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$")


def _valid_ip(ip: str) -> bool:
    if not _IP_RE.match(ip):
        return False
    parts = ip.split(".")
    return all(0 <= int(p) <= 255 for p in parts)


@router.get("", response_model=list[DeviceOut])
def list_devices(db: Session = Depends(get_db)) -> list[Device]:
    """列出全部设备。"""
    return db.query(Device).order_by(Device.id.asc()).all()


@router.post("", response_model=DeviceOut)
def create_device(payload: DeviceCreate, db: Session = Depends(get_db), _=Depends(require_admin)) -> Device:
    """新增设备。"""
    if not _valid_ip(payload.source_ip):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"IP 地址格式无效: {payload.source_ip}")
    existing = db.query(Device).filter(Device.source_ip == payload.source_ip).one_or_none()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"IP {payload.source_ip} 已被设备「{existing.name}」占用")
    dev = Device(
        name=payload.name,
        source_ip=payload.source_ip,
        proxy_name=payload.proxy_name,
        enabled=payload.enabled,
    )
    db.add(dev)
    db.commit()
    db.refresh(dev)
    get_manager().reload(db)
    logger.info("新增设备: %s (ip=%s, node=%s)", dev.name, dev.source_ip, dev.proxy_name)
    return dev


@router.put("/{dev_id}", response_model=DeviceOut)
def update_device(dev_id: int, payload: DeviceUpdate, db: Session = Depends(get_db), _=Depends(require_admin)) -> Device:
    """更新设备。"""
    dev = db.query(Device).filter(Device.id == dev_id).one_or_none()
    if dev is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"设备不存在: id={dev_id}")
    data = payload.model_dump(exclude_unset=True)
    if "source_ip" in data:
        if not _valid_ip(data["source_ip"]):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"IP 地址格式无效: {data['source_ip']}")
        dup = db.query(Device).filter(Device.source_ip == data["source_ip"], Device.id != dev_id).one_or_none()
        if dup:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"IP {data['source_ip']} 已被设备「{dup.name}」占用")
    for k, v in data.items():
        setattr(dev, k, v)
    db.commit()
    db.refresh(dev)
    get_manager().reload(db)
    logger.info("更新设备: %s (ip=%s, node=%s)", dev.name, dev.source_ip, dev.proxy_name)
    return dev


@router.delete("/{dev_id}", response_model=MessageResponse)
def delete_device(dev_id: int, db: Session = Depends(get_db), _=Depends(require_admin)) -> MessageResponse:
    """删除设备。"""
    dev = db.query(Device).filter(Device.id == dev_id).one_or_none()
    if dev is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"设备不存在: id={dev_id}")
    db.delete(dev)
    db.commit()
    get_manager().reload(db)
    logger.info("删除设备: %s (ip=%s)", dev.name, dev.source_ip)
    return MessageResponse(message="设备已删除")


@router.get("/discover", response_model=list[DiscoveredClient])
def discover_clients(db: Session = Depends(get_db), _=Depends(require_admin)) -> list[DiscoveredClient]:
    """自动发现当前连接到 mihomo 的未分配客户端 IP。

    从 mihomo /connections API 提取来源 IP，排除已注册设备的 IP，
    返回每个未分配 IP 的连接数和最近访问的目标域名。
    """
    mgr = get_manager()
    if not mgr.is_running():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="mihomo 未运行，无法发现客户端")
    try:
        data = mgr.client.get_connections()
    except MihomoAPIError as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"获取连接列表失败: {e}")

    conns = data.get("connections", []) or []
    # 已注册的 IP 集合
    assigned_ips = {d.source_ip for d in db.query(Device).all()}
    # 统计每个未分配 IP 的连接数和访问域名
    ip_conns: dict[str, int] = defaultdict(int)
    ip_hosts: dict[str, str] = {}
    for c in conns:
        meta = c.get("metadata", {}) or {}
        src_ip = meta.get("sourceIP", "")
        if not src_ip or src_ip in assigned_ips:
            continue
        # 排除本机回环和内网网关
        if src_ip.startswith("127.") or src_ip == "::1":
            continue
        ip_conns[src_ip] += 1
        host = meta.get("host") or meta.get("destinationIP") or ""
        if host and src_ip not in ip_hosts:
            ip_hosts[src_ip] = host

    # 更新已注册设备的 last_seen
    now = datetime.now(timezone.utc)
    for dev in db.query(Device).all():
        if dev.source_ip in ip_conns or any(
            (c.get("metadata", {}) or {}).get("sourceIP") == dev.source_ip for c in conns
        ):
            dev.last_seen = now
    db.commit()

    result = [
        DiscoveredClient(source_ip=ip, host=ip_hosts.get(ip, ""), connections=cnt)
        for ip, cnt in sorted(ip_conns.items(), key=lambda x: -x[1])
    ]
    return result
