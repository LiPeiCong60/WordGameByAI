from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, func, select

from auth_service import require_admin
from database import get_session
from message_quota_service import DEFAULT_NON_MEMBER_DAILY_LIMIT, effective_daily_message_limit
from models import Game, ManagementProposal, TurnLog, User
from schemas import AdminUserUpdate

router = APIRouter()


@router.get("/admin/summary")
def admin_summary(_admin: User = Depends(require_admin), db: Session = Depends(get_session)):
    return {
        "users": db.exec(select(func.count()).select_from(User)).one(),
        "games": db.exec(select(func.count()).select_from(Game)).one(),
        "turns": db.exec(select(func.count()).select_from(TurnLog)).one(),
        "pending_proposals": db.exec(
            select(func.count()).select_from(ManagementProposal).where(ManagementProposal.status == "pending_confirmation")
        ).one(),
    }


@router.get("/admin/users")
def list_users(_admin: User = Depends(require_admin), db: Session = Depends(get_session)):
    users = db.exec(select(User).order_by(User.id.desc())).all()
    return [
        {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "is_admin": user.is_admin,
            "is_member": user.is_member,
            "daily_message_limit": user.daily_message_limit,
            "effective_daily_message_limit": effective_daily_message_limit(user),
            "is_active": user.is_active,
            "created_at": user.created_at,
            "last_login_at": user.last_login_at,
        }
        for user in users
    ]


@router.patch("/admin/users/{user_id}")
def update_user(user_id: int, payload: AdminUserUpdate, admin: User = Depends(require_admin), db: Session = Depends(get_session)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail=f"找不到用户: {user_id}")
    if user.id == admin.id and payload.is_active is False:
        raise HTTPException(status_code=400, detail="不能停用当前登录的管理员账号。")
    if user.id == admin.id and payload.is_admin is False:
        raise HTTPException(status_code=400, detail="不能取消当前登录账号的管理员权限。")

    if payload.is_active is not None:
        user.is_active = payload.is_active
    if payload.is_admin is not None:
        user.is_admin = payload.is_admin
    if payload.is_member is not None:
        user.is_member = payload.is_member
    if payload.daily_message_limit is not None:
        if payload.daily_message_limit < 0:
            raise HTTPException(status_code=400, detail="每日消息上限不能小于 0。")
        if not user.is_member and payload.daily_message_limit > DEFAULT_NON_MEMBER_DAILY_LIMIT:
            raise HTTPException(status_code=400, detail=f"非会员每日消息上限不能超过 {DEFAULT_NON_MEMBER_DAILY_LIMIT}。")
        user.daily_message_limit = payload.daily_message_limit
    db.add(user)
    db.commit()
    db.refresh(user)
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "is_admin": user.is_admin,
        "is_member": user.is_member,
        "daily_message_limit": user.daily_message_limit,
        "effective_daily_message_limit": effective_daily_message_limit(user),
        "is_active": user.is_active,
        "created_at": user.created_at,
        "last_login_at": user.last_login_at,
    }


@router.get("/admin/games")
def list_all_games(_admin: User = Depends(require_admin), db: Session = Depends(get_session)):
    games = db.exec(select(Game).order_by(Game.id.desc())).all()
    users = {user.id: user.username for user in db.exec(select(User)).all()}
    return [
        {
            "id": game.id,
            "title": game.title,
            "genre": game.genre,
            "owner_user_id": game.owner_user_id,
            "owner_username": users.get(game.owner_user_id, "未归属"),
            "created_at": game.created_at,
            "updated_at": game.updated_at,
        }
        for game in games
    ]
