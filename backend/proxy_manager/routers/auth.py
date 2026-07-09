from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user_dependency
from ..models import User
from ..schemas import LoginRequest, TokenResponse, UserOut
from ..security import create_access_token, verify_password

logger = logging.getLogger("proxy_manager")

router = APIRouter(prefix="/api/auth", tags=["认证"])


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    """用户名密码登录，返回 JWT。"""
    user = db.query(User).filter(User.username == payload.username).first()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="用户已被禁用，请联系管理员")
    token = create_access_token(subject=user.id, extra={"username": user.username, "is_admin": user.is_admin})
    logger.info("用户登录成功: %s", user.username)
    return TokenResponse(access_token=token, user=UserOut.model_validate(user))


@router.post("/refresh", response_model=TokenResponse)
def refresh(user: User = Depends(get_current_user_dependency)) -> TokenResponse:
    """刷新 token。"""
    token = create_access_token(subject=user.id, extra={"username": user.username, "is_admin": user.is_admin})
    return TokenResponse(access_token=token, user=UserOut.model_validate(user))


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user_dependency)) -> User:
    """获取当前登录用户信息。"""
    return user
