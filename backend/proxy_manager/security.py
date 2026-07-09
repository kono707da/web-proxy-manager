from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import jwt
from passlib.context import CryptContext

from .config import settings

logger = logging.getLogger("proxy_manager")

ALGORITHM = settings.jwt_algorithm
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password[:72].encode("utf-8"))


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return pwd_context.verify(plain[:72].encode("utf-8"), hashed)
    except Exception as e:
        logger.error("密码校验异常: %s", e, exc_info=True)
        return False


def create_access_token(subject: str | int, extra: dict[str, Any] | None = None) -> str:
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=settings.jwt_expire_minutes)
    payload: dict[str, Any] = {
        "sub": str(subject),
        "exp": expire,
        "iat": now,
        "type": "access",
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)


def decode_token(token: str) -> dict[str, Any] | None:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])
        if payload.get("type") != "access":
            return None
        return payload
    except Exception as e:
        logger.warning("token 解析失败: %s", e)
        return None
