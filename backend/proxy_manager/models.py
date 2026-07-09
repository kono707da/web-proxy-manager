from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import BigInteger, Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    """系统用户。"""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(256), nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now, nullable=False)


class Subscription(Base):
    """代理订阅源。"""

    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    auto_update: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    update_interval: Mapped[int] = mapped_column(Integer, default=3600, nullable=False)  # 秒
    last_update: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    node_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_error: Mapped[str | None] = mapped_column(Text, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now, nullable=False)


class Rule(Base):
    """自定义分流规则。"""

    __tablename__ = "rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    rule_type: Mapped[str] = mapped_column(String(64), nullable=False)  # DOMAIN-SUFFIX / DOMAIN-KEYWORD / IP-CIDR / GEOIP / PROCESS-NAME 等
    value: Mapped[str] = mapped_column(Text, nullable=False)
    target: Mapped[str] = mapped_column(String(128), nullable=False, default="DIRECT")  # 策略组名或 DIRECT/REJECT
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now, nullable=False)


class SpeedLimit(Base):
    """限速规则。scope: global/group/client。"""

    __tablename__ = "speed_limits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    scope: Mapped[str] = mapped_column(String(32), nullable=False)  # global / group / client
    target: Mapped[str] = mapped_column(String(256), default="")  # group 名或 client IP，global 时为空
    download_limit: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # B/s，0=不限
    upload_limit: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # B/s，0=不限
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now, nullable=False)


class TrafficQuota(Base):
    """流量配额。scope: client/group。"""

    __tablename__ = "traffic_quotas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    scope: Mapped[str] = mapped_column(String(32), nullable=False)  # client / group
    target: Mapped[str] = mapped_column(String(256), nullable=False)  # client IP 或 group 名
    quota_bytes: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)  # 0=不限
    used_bytes: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    period: Mapped[str] = mapped_column(String(16), default="total", nullable=False)  # total / daily / monthly
    reset_day: Mapped[int] = mapped_column(Integer, default=1, nullable=False)  # 月配额重置日
    last_reset: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    blocked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now, nullable=False)


class TrafficStat(Base):
    """按客户端 IP 累计的流量统计。"""

    __tablename__ = "traffic_stats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    client_ip: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    upload_total: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    download_total: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    total_bytes: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    last_seen: Mapped[datetime] = mapped_column(DateTime, default=_now, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now, nullable=False)
