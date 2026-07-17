from __future__ import annotations

from fastapi import APIRouter, Depends, Header
from sqlmodel import Session

from auth_service import (
    bearer_token_value,
    create_captcha,
    get_current_user,
    login_user,
    public_user,
    refresh_user_session,
    register_user,
    revoke_user_session,
)
from database import get_session
from models import User
from schemas import LoginRequest, LogoutRequest, RefreshTokenRequest, RegisterRequest

router = APIRouter()


@router.get("/auth/captcha")
def captcha(db: Session = Depends(get_session)):
    return create_captcha(db)


@router.post("/auth/register")
def register(payload: RegisterRequest, db: Session = Depends(get_session)):
    return register_user(
        db,
        payload.username,
        payload.password,
        payload.email,
        payload.captcha_id,
        payload.captcha_answer,
        payload.bootstrap_token,
    )


@router.post("/auth/login")
def login(payload: LoginRequest, db: Session = Depends(get_session)):
    return login_user(db, payload.username, payload.password, payload.captcha_id, payload.captcha_answer)


@router.get("/auth/me")
def me(user: User = Depends(get_current_user)):
    return public_user(user)


@router.post("/auth/refresh")
def refresh(payload: RefreshTokenRequest, db: Session = Depends(get_session)):
    return refresh_user_session(db, payload.refresh_token)


@router.post("/auth/logout")
def logout(
    payload: LogoutRequest | None = None,
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_session),
    _user: User = Depends(get_current_user),
):
    revoke_user_session(db, bearer_token_value(authorization), payload.refresh_token if payload else "")
    return {"ok": True}
