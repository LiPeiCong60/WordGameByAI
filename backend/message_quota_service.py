from __future__ import annotations

import os
import threading
from collections import defaultdict, deque
from datetime import date, datetime, timedelta

from fastapi import HTTPException
from sqlmodel import Session, select

from models import MessageUsage, User

DEFAULT_NON_MEMBER_DAILY_LIMIT = int(os.getenv("NON_MEMBER_DAILY_MESSAGE_LIMIT", "20"))
RATE_LIMIT_WINDOW_SECONDS = int(os.getenv("MESSAGE_RATE_LIMIT_WINDOW_SECONDS", "60"))
RATE_LIMIT_MAX_REQUESTS = int(os.getenv("MESSAGE_RATE_LIMIT_MAX_REQUESTS", "10"))

_rate_lock = threading.Lock()
_recent_requests: dict[int, deque[datetime]] = defaultdict(deque)


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


def _check_short_window(user: User) -> None:
    if user.is_admin:
        return
    now = datetime.utcnow()
    cutoff = now - timedelta(seconds=RATE_LIMIT_WINDOW_SECONDS)
    with _rate_lock:
        bucket = _recent_requests[int(user.id or 0)]
        while bucket and bucket[0] < cutoff:
            bucket.popleft()
        if len(bucket) >= RATE_LIMIT_MAX_REQUESTS:
            raise HTTPException(status_code=429, detail=f"请求过于频繁，请稍后再试。")
        bucket.append(now)


def require_message_quota(db: Session, user: User) -> dict:
    _check_short_window(user)
    limit = effective_daily_message_limit(user)
    if limit is None:
        return {"ok": True, "limit": None, "remaining": None}

    today = date.today().isoformat()
    usage = db.exec(select(MessageUsage).where(MessageUsage.user_id == user.id, MessageUsage.usage_date == today)).first()
    if not usage:
        usage = MessageUsage(user_id=int(user.id), usage_date=today, message_count=0)
    if usage.message_count >= limit:
        raise HTTPException(status_code=429, detail=f"今日消息额度已用完（{usage.message_count}/{limit}）。")

    usage.message_count += 1
    usage.updated_at = datetime.utcnow()
    db.add(usage)
    db.commit()
    return {"ok": True, "limit": limit, "remaining": max(limit - usage.message_count, 0)}
