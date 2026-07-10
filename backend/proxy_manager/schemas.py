from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel


# ---------- 认证 ----------
class LoginRequest(BaseModel):
    username: str
    password: str


class UserOut(BaseModel):
    id: int
    username: str
    is_admin: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ---------- 订阅 ----------
class SubscriptionCreate(BaseModel):
    name: str
    url: str
    enabled: bool = True
    auto_update: bool = True
    update_interval: int = 3600


class SubscriptionUpdate(BaseModel):
    name: Optional[str] = None
    url: Optional[str] = None
    enabled: Optional[bool] = None
    auto_update: Optional[bool] = None
    update_interval: Optional[int] = None


class SubscriptionOut(BaseModel):
    id: int
    name: str
    url: str
    enabled: bool
    auto_update: bool
    update_interval: int
    last_update: Optional[datetime] = None
    node_count: int
    last_error: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}


# ---------- 代理节点 ----------
class ProxyOut(BaseModel):
    name: str
    type: str
    udp: bool = False
    history: list[dict[str, Any]] = []
    alive: bool = False


class ProxyGroupOut(BaseModel):
    name: str
    type: str
    now: Optional[str] = None
    all: list[str] = []


class DelayTestResponse(BaseModel):
    name: str
    delay: int  # 毫秒，0 表示超时/失败


class SelectProxyRequest(BaseModel):
    name: str  # 选择的节点名


# ---------- 规则 ----------
class RuleCreate(BaseModel):
    name: str
    rule_type: str
    value: str
    target: str = "DIRECT"
    enabled: bool = True
    priority: int = 0


class RuleUpdate(BaseModel):
    name: Optional[str] = None
    rule_type: Optional[str] = None
    value: Optional[str] = None
    target: Optional[str] = None
    enabled: Optional[bool] = None
    priority: Optional[int] = None


class RuleOut(BaseModel):
    id: int
    name: str
    rule_type: str
    value: str
    target: str
    enabled: bool
    priority: int
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}


# ---------- 连接 ----------
class ConnectionOut(BaseModel):
    id: str
    metadata: dict[str, Any]
    upload: int
    download: int
    start: str
    chains: list[str] = []
    rule: str = ""
    rulePayload: str = ""
    downloadSpeed: int = 0
    uploadSpeed: int = 0


class ConnectionListResponse(BaseModel):
    downloadTotal: int
    uploadTotal: int
    connections: list[ConnectionOut] = []
    memory: int = 0


# ---------- 流量 ----------
class TrafficSnapshot(BaseModel):
    """实时流量快照（来自 mihomo /traffic）。"""

    up: int
    down: int


class TrafficStatOut(BaseModel):
    client_ip: str
    upload_total: int
    download_total: int
    total_bytes: int
    last_seen: datetime
    model_config = {"from_attributes": True}


class MemorySnapshot(BaseModel):
    inuse: int
    oslimit: int = 0


# ---------- 限速 ----------
class SpeedLimitCreate(BaseModel):
    name: str
    scope: str  # global / group / client
    target: str = ""
    download_limit: int = 0
    upload_limit: int = 0
    enabled: bool = True


class SpeedLimitUpdate(BaseModel):
    name: Optional[str] = None
    scope: Optional[str] = None
    target: Optional[str] = None
    download_limit: Optional[int] = None
    upload_limit: Optional[int] = None
    enabled: Optional[bool] = None


class SpeedLimitOut(BaseModel):
    id: int
    name: str
    scope: str
    target: str
    download_limit: int
    upload_limit: int
    enabled: bool
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}


# ---------- 配额 ----------
class QuotaCreate(BaseModel):
    name: str
    scope: str  # client / group
    target: str
    quota_bytes: int = 0
    period: str = "total"
    reset_day: int = 1
    enabled: bool = True


class QuotaUpdate(BaseModel):
    name: Optional[str] = None
    quota_bytes: Optional[int] = None
    period: Optional[str] = None
    reset_day: Optional[int] = None
    enabled: Optional[bool] = None
    used_bytes: Optional[int] = None
    blocked: Optional[bool] = None


class QuotaOut(BaseModel):
    id: int
    name: str
    scope: str
    target: str
    quota_bytes: int
    used_bytes: int
    period: str
    reset_day: int
    last_reset: Optional[datetime] = None
    blocked: bool
    enabled: bool
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}


# ---------- 设备管理 ----------
class DeviceCreate(BaseModel):
    name: str
    source_ip: str
    proxy_name: str = ""
    enabled: bool = True


class DeviceUpdate(BaseModel):
    name: Optional[str] = None
    source_ip: Optional[str] = None
    proxy_name: Optional[str] = None
    enabled: Optional[bool] = None


class DeviceOut(BaseModel):
    id: int
    name: str
    source_ip: str
    proxy_name: str
    enabled: bool
    last_seen: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}


class DiscoveredClient(BaseModel):
    """自动发现的未分配客户端。"""
    source_ip: str
    host: str = ""
    connections: int = 0


# ---------- 系统 ----------
class MihomoStatusResponse(BaseModel):
    running: bool
    pid: Optional[int] = None
    version: Optional[str] = None
    api_port: int
    mixed_port: int
    mode: Optional[str] = None
    log_level: str
    uptime: Optional[int] = None
    last_error: Optional[str] = None


class SystemInfoResponse(BaseModel):
    version: str
    mihomo: MihomoStatusResponse
    cpu_percent: float
    memory_mb: float
    disk_mb: float


class ModeUpdateRequest(BaseModel):
    mode: str  # rule / global / direct


class LogLevelUpdateRequest(BaseModel):
    level: str  # debug / info / warning / error / silent


class MessageResponse(BaseModel):
    message: str
    detail: Optional[str] = None
