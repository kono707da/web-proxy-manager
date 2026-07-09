from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from .config import BASE_DIR, settings

logger = logging.getLogger("proxy_manager")

DB_PATH = BASE_DIR / "data" / "proxy_manager.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

engine = create_engine(
    f"sqlite:///{DB_PATH.as_posix()}",
    connect_args={"check_same_thread": False},
    echo=False,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """创建所有表，并初始化默认管理员。"""
    from . import models  # noqa: F401  延迟导入避免循环

    Base.metadata.create_all(bind=engine)
    _ensure_default_admin()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _ensure_default_admin() -> None:
    """首次启动、数据库无管理员时创建默认管理员。"""
    from .models import User
    from .security import hash_password

    db = SessionLocal()
    try:
        has_admin = db.query(User).filter(User.is_admin.is_(True)).first()
        if has_admin:
            return
        cfg = settings.default_admin
        existing = db.query(User).filter(User.username == cfg.username).first()
        if existing:
            existing.is_admin = True
            existing.is_active = True
        else:
            user = User(
                username=cfg.username,
                password_hash=hash_password(cfg.password),
                is_admin=True,
                is_active=True,
            )
            db.add(user)
        db.commit()
        logger.info("已创建默认管理员: %s", cfg.username)
    except Exception as e:
        logger.error("创建默认管理员失败: %s", e, exc_info=True)
        db.rollback()
    finally:
        db.close()
