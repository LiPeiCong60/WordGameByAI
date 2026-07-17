from __future__ import annotations

import os
from datetime import date, datetime, timedelta

from fastapi import HTTPException
from sqlalchemy import update
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from models import MessageRateBucket, MessageUsage, User
from time_utils import utc_from_timestamp, utc_now

DEFAULT_NON_MEMBER_DAILY_LIMIT = int(os.getenv("NON_MEMBER_DAILY_MESSAGE_LIMIT", "20"))
RATE_LIMIT_WINDOW_SECONDS = int(os.getenv("MESSAGE_RATE_LIMIT_WINDOW_SECONDS", "60"))
RATE_LIMIT_MAX_REQUESTS = int(os.getenv("MESSAGE_RATE_LIMIT_MAX_REQUESTS", "10"))

# Kept as a compatibility shim for older tests/callers. Rate limits are now
# persisted in the database and therefore work across multiple workers.
_recent_requests: dict = {}


def effective_daily_message_limit(user: User) -> int | None:
    if user.is_admin:
        return None
    configured = int(getattr(user, "daily_message_limit", DEFAULT_NON_MEMBER_DAILY_LIMIT) or 0)
    if getattr(user, "is_member", False):
        return configured if configured > 0 else None
    return min(max(configured, 0), DEFAULT_NON_MEMBER_DAILY_LIMIT)


def get_today_message_usage(db: Session, user: User) -> dict:
    limit = effective_daily_message_limit(user)
    today = date.today().isoformat()
    usage = db.exec(select(MessageUsage).where(MessageUsage.user_id == user.id, MessageUsage.usage_date == today)).first()
    used = int(usage.message_count) if usage else 0
    return {
        "used": used,
        "limit": limit,
        "remaining": None if limit is None else max(limit - used, 0),
    }


def _get_or_create_rate_bucket(db: Session, user_id: int, window_start: str, expires_at: datetime) -> None:
    bucket = db.exec(
        select(MessageRateBucket)
        .where(MessageRateBucket.user_id == user_id, MessageRateBucket.window_start == window_start)
        .with_for_update()
    ).first()
    if bucket:
        return
    try:
        bucket = MessageRateBucket(user_id=user_id, window_start=window_start, expires_at=expires_at)
        db.add(bucket)
        db.commit()
    except IntegrityError:
        db.rollback()
    db.exec(
        select(MessageRateBucket)
        .where(MessageRateBucket.user_id == user_id, MessageRateBucket.window_start == window_start)
    ).one()


def _check_short_window(db: Session, user: User) -> None:
    if user.is_admin:
        return
    now = utc_now()
    window_epoch = int(now.timestamp()) // max(1, RATE_LIMIT_WINDOW_SECONDS) * max(1, RATE_LIMIT_WINDOW_SECONDS)
    window_start = utc_from_timestamp(window_epoch).isoformat()
    expires_at = utc_from_timestamp(window_epoch) + timedelta(seconds=RATE_LIMIT_WINDOW_SECONDS * 2)
    user_id = int(user.id or 0)
    _get_or_create_rate_bucket(db, user_id, window_start, expires_at)
    result = db.exec(
        update(MessageRateBucket)
        .where(
            MessageRateBucket.user_id == user_id,
            MessageRateBucket.window_start == window_start,
            MessageRateBucket.request_count < RATE_LIMIT_MAX_REQUESTS,
        )
        .values(request_count=MessageRateBucket.request_count + 1)
    )
    db.commit()
    if not result.rowcount:
        raise HTTPException(status_code=429, detail="请求过于频繁，请稍后再试。")


def require_message_quota(db: Session, user: User) -> dict:
    _check_short_window(db, user)
    limit = effective_daily_message_limit(user)
    if limit is None:
        return {"ok": True, "limit": None, "remaining": None}

    today = date.today().isoformat()
    usage = db.exec(select(MessageUsage).where(MessageUsage.user_id == user.id, MessageUsage.usage_date == today)).first()
    if not usage:
        try:
            usage = MessageUsage(user_id=int(user.id), usage_date=today, message_count=0)
            db.add(usage)
            db.commit()
        except IntegrityError:
            db.rollback()
        usage = db.exec(select(MessageUsage).where(MessageUsage.user_id == user.id, MessageUsage.usage_date == today)).one()
    result = db.exec(
        update(MessageUsage)
        .where(
            MessageUsage.id == usage.id,
            MessageUsage.message_count < limit,
        )
        .values(message_count=MessageUsage.message_count + 1, updated_at=utc_now())
    )
    db.commit()
    db.refresh(usage)
    if not result.rowcount:
        raise HTTPException(status_code=429, detail=f"今日消息额度已用完（{usage.message_count}/{limit}）。")
    return {"ok": True, "limit": limit, "remaining": max(limit - usage.message_count, 0)}
