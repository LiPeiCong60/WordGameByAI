from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, func, select

from auth_service import require_admin
from database import get_session
from message_quota_service import DEFAULT_NON_MEMBER_DAILY_LIMIT, get_today_message_usage
from model_config_service import (
    delete_level,
    delete_model,
    public_model_config,
    set_default_level,
    set_default_model,
    set_user_level,
    upsert_level,
    upsert_model,
    user_level_id,
)
from models import Game, ManagementProposal, TokenUsageLog, TurnLog, User
from schemas import (
    AdminDefaultLevelUpdate,
    AdminDefaultModelUpdate,
    AdminModelConfigUpsert,
    AdminModelLevelUpsert,
    AdminUserModelLevelUpdate,
    AdminUserUpdate,
)

router = APIRouter()


def admin_user_payload(user: User, db: Session) -> dict:
    usage = get_today_message_usage(db, user)
    token_stats = db.exec(
        select(
            func.sum(TokenUsageLog.total_tokens),
            func.count(TokenUsageLog.id)
        )
        .where(TokenUsageLog.user_id == user.id)
    ).first()
    total_tokens = token_stats[0] if token_stats and token_stats[0] is not None else 0
    total_calls = token_stats[1] if token_stats and token_stats[1] is not None else 0

    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "is_admin": user.is_admin,
        "is_member": user.is_member,
        "daily_message_limit": user.daily_message_limit,
        "effective_daily_message_limit": usage["limit"],
        "today_message_count": usage["used"],
        "remaining_message_count": usage["remaining"],
        "model_level_id": user_level_id(user.id),
        "is_active": user.is_active,
        "created_at": user.created_at,
        "last_login_at": user.last_login_at,
        "total_tokens": total_tokens,
        "total_calls": total_calls,
    }


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
    return [admin_user_payload(user, db) for user in users]


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
    return admin_user_payload(user, db)


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


@router.get("/admin/model-config")
def get_model_config(_admin: User = Depends(require_admin)):
    return public_model_config()


@router.put("/admin/model-config/models")
def save_model_config(payload: AdminModelConfigUpsert, _admin: User = Depends(require_admin)):
    try:
        return upsert_model(payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/admin/model-config/models/{model_id}")
def remove_model_config(model_id: str, _admin: User = Depends(require_admin)):
    try:
        return delete_model(model_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"找不到模型配置: {model_id}") from exc


@router.patch("/admin/model-config/default-model")
def update_default_model(payload: AdminDefaultModelUpdate, _admin: User = Depends(require_admin)):
    try:
        return set_default_model(payload.model_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"找不到模型配置: {payload.model_id}") from exc


@router.put("/admin/model-config/levels")
def save_model_level(payload: AdminModelLevelUpsert, _admin: User = Depends(require_admin)):
    try:
        return upsert_level(payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"找不到模型配置: {exc.args[0]}") from exc


@router.delete("/admin/model-config/levels/{level_id}")
def remove_model_level(level_id: str, _admin: User = Depends(require_admin)):
    try:
        return delete_level(level_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"找不到模型等级: {level_id}") from exc


@router.patch("/admin/model-config/default-level")
def update_default_level(payload: AdminDefaultLevelUpdate, _admin: User = Depends(require_admin)):
    try:
        return set_default_level(payload.level_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"找不到模型等级: {payload.level_id}") from exc


@router.patch("/admin/users/{user_id}/model-level")
def update_user_model_level(
    user_id: int,
    payload: AdminUserModelLevelUpdate,
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_session),
):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail=f"找不到用户: {user_id}")
    try:
        set_user_level(user_id, payload.level_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"找不到模型等级: {payload.level_id}") from exc
    return admin_user_payload(user, db)


@router.get("/admin/users/{user_id}/token-usage")
def get_user_token_usage(user_id: int, _admin: User = Depends(require_admin), db: Session = Depends(get_session)):
    results = db.exec(
        select(
            TokenUsageLog.model_name,
            func.count(TokenUsageLog.id).label("calls"),
            func.sum(TokenUsageLog.prompt_tokens).label("prompt"),
            func.sum(TokenUsageLog.completion_tokens).label("completion"),
            func.sum(TokenUsageLog.total_tokens).label("total")
        )
        .where(TokenUsageLog.user_id == user_id)
        .group_by(TokenUsageLog.model_name)
    ).all()
    return [
        {
            "model_name": row[0],
            "calls": row[1],
            "prompt_tokens": row[2] or 0,
            "completion_tokens": row[3] or 0,
            "total_tokens": row[4] or 0
        }
        for row in results
    ]


@router.get("/admin/token-usage/summary")
def get_global_token_usage(_admin: User = Depends(require_admin), db: Session = Depends(get_session)):
    results = db.exec(
        select(
            TokenUsageLog.model_name,
            func.count(TokenUsageLog.id).label("calls"),
            func.sum(TokenUsageLog.prompt_tokens).label("prompt"),
            func.sum(TokenUsageLog.completion_tokens).label("completion"),
            func.sum(TokenUsageLog.total_tokens).label("total")
        )
        .group_by(TokenUsageLog.model_name)
    ).all()
    return [
        {
            "model_name": row[0],
            "calls": row[1],
            "prompt_tokens": row[2] or 0,
            "completion_tokens": row[3] or 0,
            "total_tokens": row[4] or 0
        }
        for row in results
    ]
