from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field
from sqlmodel import Session, desc, select

from auth_service import get_current_user, require_game_access
from database import get_session
from json_utils import safe_json_loads
from message_quota_service import get_today_message_usage
from models import Character, StoryWorld, TurnLog, TurnStateJob, User
from turn_concurrency_service import active_game_turn_lease


router = APIRouter()


class MobileConfigResponse(BaseModel):
    api_version: str = "v1"
    api_base_url: str
    media_base_url: str
    streaming_protocol: str = "ndjson"


class TurnPageResponse(BaseModel):
    items: list[dict[str, Any]] = Field(default_factory=list)
    next_cursor: int | None = None
    has_more: bool = False


class GameBootstrapResponse(BaseModel):
    game: dict[str, Any]
    current_world: dict[str, Any] | None = None
    characters: list[dict[str, Any]] = Field(default_factory=list)
    turns: TurnPageResponse
    message_usage: dict[str, Any]
    state_sync: dict[str, Any]


def _dump(record) -> dict[str, Any]:
    return record.model_dump() if hasattr(record, "model_dump") else record.dict()


def _absolute_media_url(request: Request, value: str) -> str:
    if not value or value.startswith(("http://", "https://")):
        return value
    return f"{str(request.base_url).rstrip('/')}/{value.lstrip('/')}"


def _turn_payload(turn: TurnLog) -> dict[str, Any]:
    return {
        "id": turn.id,
        "game_id": turn.game_id,
        "turn_number": turn.turn_number,
        "user_input": turn.user_input,
        "ai_response": turn.ai_response,
        "npc_reactions": safe_json_loads(turn.npc_reactions, default={}),
        "state_patch": safe_json_loads(turn.state_patch, default={}),
        "checker_result": safe_json_loads(turn.checker_result, default={}),
        "request_id": turn.client_request_id or "",
        "created_at": turn.created_at,
    }


def _turn_page(db: Session, game_id: int, limit: int, before_id: int | None) -> TurnPageResponse:
    query = select(TurnLog).where(TurnLog.game_id == game_id)
    if before_id:
        query = query.where(TurnLog.id < before_id)
    rows = list(db.exec(query.order_by(desc(TurnLog.id)).limit(limit + 1)).all())
    has_more = len(rows) > limit
    rows = rows[:limit]
    next_cursor = int(rows[-1].id) if has_more and rows and rows[-1].id is not None else None
    return TurnPageResponse(items=[_turn_payload(turn) for turn in reversed(rows)], next_cursor=next_cursor, has_more=has_more)


def _state_sync_payload(db: Session, game_id: int) -> dict[str, Any]:
    job = db.exec(
        select(TurnStateJob).where(TurnStateJob.game_id == game_id).order_by(desc(TurnStateJob.id)).limit(1)
    ).first()
    lease = active_game_turn_lease(db, game_id)
    job_payload = None
    if job:
        job_payload = {
            "id": job.id,
            "turn_id": job.turn_id,
            "status": job.status,
            "attempts": job.attempts,
            "has_error": bool(job.last_error),
            "created_at": job.created_at,
            "updated_at": job.updated_at,
        }
    return {
        "job": job_payload,
        "turn_in_progress": bool(lease),
        "active_request_id": lease.request_id if lease else "",
    }


@router.get("/mobile/config", response_model=MobileConfigResponse)
def mobile_config(request: Request):
    origin = str(request.base_url).rstrip("/")
    return MobileConfigResponse(
        api_base_url=f"{origin}/api/v1",
        media_base_url=origin,
    )


@router.get("/games/{game_id}/turns", response_model=TurnPageResponse)
def list_game_turns(
    game_id: int,
    limit: int = Query(default=20, ge=1, le=100),
    before_id: int | None = Query(default=None, ge=1),
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    require_game_access(db, game_id, user)
    return _turn_page(db, game_id, limit, before_id)


@router.get("/games/{game_id}/state-sync")
def game_state_sync(
    game_id: int,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    require_game_access(db, game_id, user)
    return _state_sync_payload(db, game_id)


@router.get("/games/{game_id}/bootstrap", response_model=GameBootstrapResponse)
def game_bootstrap(
    game_id: int,
    request: Request,
    turn_limit: int = Query(default=20, ge=1, le=50),
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    game = require_game_access(db, game_id, user)
    worlds = list(db.exec(select(StoryWorld).where(StoryWorld.game_id == game_id)).all())
    current_world = next((item for item in worlds if item.id == game.current_story_world_id), worlds[0] if worlds else None)
    characters = []
    for character in db.exec(select(Character).where(Character.game_id == game_id)).all():
        data = _dump(character)
        data["avatar_url"] = _absolute_media_url(request, character.avatar_url)
        characters.append(data)
    return GameBootstrapResponse(
        game=_dump(game),
        current_world=_dump(current_world) if current_world else None,
        characters=characters,
        turns=_turn_page(db, game_id, turn_limit, None),
        message_usage=get_today_message_usage(db, user),
        state_sync=_state_sync_payload(db, game_id),
    )
