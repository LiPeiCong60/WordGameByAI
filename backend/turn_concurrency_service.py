from __future__ import annotations

from datetime import timedelta
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session

from models import GameTurnLease
from time_utils import utc_now


LEASE_TTL = timedelta(minutes=15)


def normalize_request_id(value: str | None) -> str:
    value = (value or "").strip()
    if not value:
        return uuid4().hex
    if len(value) > 100 or not all(char.isalnum() or char in "_-." for char in value):
        raise HTTPException(status_code=400, detail={"code": "invalid_request_id", "message": "request_id 格式无效。"})
    return value


def acquire_game_turn_lease(db: Session, game_id: int, request_id: str) -> None:
    bind = db.get_bind()
    now = utc_now()
    try:
        with Session(bind=bind) as lease_db:
            existing = lease_db.get(GameTurnLease, game_id)
            if existing and existing.expires_at <= now:
                lease_db.delete(existing)
                lease_db.commit()
                existing = None
            if existing:
                raise HTTPException(
                    status_code=409,
                    detail={
                        "code": "game_turn_in_progress",
                        "message": "当前存档已有剧情正在生成，请等待完成后再试。",
                        "request_id": existing.request_id,
                    },
                )
            lease_db.add(
                GameTurnLease(
                    game_id=game_id,
                    request_id=request_id,
                    expires_at=now + LEASE_TTL,
                )
            )
            lease_db.commit()
    except IntegrityError as exc:
        raise HTTPException(
            status_code=409,
            detail={"code": "game_turn_in_progress", "message": "当前存档已有剧情正在生成，请稍后重试。"},
        ) from exc


def release_game_turn_lease(db: Session, game_id: int, request_id: str) -> None:
    bind = db.get_bind()
    with Session(bind=bind) as lease_db:
        existing = lease_db.get(GameTurnLease, game_id)
        if existing and existing.request_id == request_id:
            lease_db.delete(existing)
            lease_db.commit()


def active_game_turn_lease(db: Session, game_id: int) -> GameTurnLease | None:
    lease = db.get(GameTurnLease, game_id)
    if lease and lease.expires_at <= utc_now():
        db.delete(lease)
        db.commit()
        return None
    return lease
