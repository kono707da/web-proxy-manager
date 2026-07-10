from __future__ import annotations

import json
import logging
import os
import secrets
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel

logger = logging.getLogger("proxy_manager")

BASE_DIR = Path(__file__).resolve().parent.parent  # 指向 backend/
CONFIG_FILE = BASE_DIR / "config.yaml"
PERSIST_FILE = BASE_DIR / "data" / "settings.json"


class MihomoConfig(BaseModel):
    """mihomo 内核配置。"""

    binary: str = "mihomo"
    binary_version: str = "1.19.28"
    work_dir: str = "data/mihomo"
    api_port: int = 9090
    mixed_port: int = 7890
    allow_lan: bool = True
    log_level: str = "info"
    secret: str = ""
    enable_tun: bool = False


class TrafficConfig(BaseModel):
    """流量监控配置。"""

    poll_interval: int = 2
    quota_check_interval: int = 5
    cleanup_interval: int = 60


class DefaultAdminConfig(BaseModel):
    """首次启动默认管理员。"""

    username: str = "admin"
    password: str = "admin123"


class Settings(BaseModel):
    """应用配置。"""

    host: str = "0.0.0.0"
    port: int = 8000
    jwt_secret: str = ""
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440
    mihomo: MihomoConfig = MihomoConfig()
    traffic: TrafficConfig = TrafficConfig()
    default_admin: DefaultAdminConfig = DefaultAdminConfig()


def _load_yaml() -> dict[str, Any]:
    if not CONFIG_FILE.exists():
        return {}
    try:
        with CONFIG_FILE.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        if not isinstance(data, dict):
            return {}
        return data
    except Exception as e:
        logger.error("读取 config.yaml 失败: %s", e, exc_info=True)
        return {}


def _load_persisted() -> dict[str, Any]:
    if not PERSIST_FILE.exists():
        return {}
    try:
        with PERSIST_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f) or {}
        return data if isinstance(data, dict) else {}
    except Exception as e:
        logger.error("读取 settings.json 失败: %s", e, exc_info=True)
        return {}


def _save_settings_json(data: dict[str, Any]) -> None:
    PERSIST_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = PERSIST_FILE.with_suffix(".json.tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    tmp.replace(PERSIST_FILE)


def _ensure_secret(persisted: dict[str, Any], key: str) -> str:
    """从持久化文件读取 secret，不存在则生成并写回。"""
    existing = persisted.get(key)
    if existing and isinstance(existing, str) and existing.strip():
        return existing.strip()
    new_secret = secrets.token_urlsafe(32)
    persisted[key] = new_secret
    _save_settings_json(persisted)
    return new_secret


def load_settings() -> Settings:
    """三层加载：config.yaml → 环境变量(PROXY_MANAGER_ 前缀) → settings.json(仅敏感 secret)。"""
    yaml_data = _load_yaml()
    # 敏感项不入 yaml / 环境变量，统一由 settings.json 管理
    yaml_data.pop("jwt_secret", None)
    mihomo_section = yaml_data.get("mihomo") or {}
    if isinstance(mihomo_section, dict):
        mihomo_section.pop("secret", None)

    persisted = _load_persisted()

    env_overrides: dict[str, Any] = {}
    for key in Settings.model_fields:
        env_key = f"PROXY_MANAGER_{key.upper()}"
        if env_key in os.environ:
            env_overrides[key] = os.environ[env_key]

    merged: dict[str, Any] = {**yaml_data, **env_overrides}
    merged["jwt_secret"] = _ensure_secret(persisted, "jwt_secret")

    mihomo_data = dict(merged.get("mihomo") or {})
    mihomo_data["secret"] = _ensure_secret(persisted, "mihomo_secret")
    merged["mihomo"] = mihomo_data

    try:
        s = Settings(**merged)
    except Exception as e:
        logger.error("配置加载失败，回退默认值: %s", e, exc_info=True)
        s = Settings()
        s.jwt_secret = _ensure_secret(persisted, "jwt_secret")
    return s


settings = load_settings()
