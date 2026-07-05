from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlmodel import Session

from auth_service import create_captcha, get_current_user, login_user, public_user, register_user
from database import get_session
from models import User
from schemas import LoginRequest, RegisterRequest

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
    )


@router.post("/auth/login")
def login(payload: LoginRequest, db: Session = Depends(get_session)):
    return login_user(db, payload.username, payload.password)


@router.get("/auth/me")
def me(user: User = Depends(get_current_user)):
    return public_user(user)
