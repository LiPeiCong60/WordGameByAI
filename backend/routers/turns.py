from __future__ import annotations

import contextvars
import json
import logging

from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import StreamingResponse
from sqlmodel import Session

from auth_service import get_current_user, require_game_access
from database import get_session
from game_engine import (
    find_turn_by_request_id,
    run_game_turn,
    run_game_turn_stream,
    run_opening_turn,
    run_opening_turn_stream,
    saved_turn_result,
)
from llm_client import reset_current_llm_user, set_current_llm_user
from message_quota_service import require_message_quota
from models import TurnLog, User
from schemas import TurnRequest
from turn_history_service import delete_turns_from, get_turn_for_action, regenerate_turn
from turn_concurrency_service import acquire_game_turn_lease, normalize_request_id, release_game_turn_lease

router = APIRouter()
logger = logging.getLogger(__name__)


class ContextPreservingIterator:
    def __init__(self, iterator):
        self.iterator = iterator
        self.context = contextvars.copy_context()

    def __iter__(self):
        return self

    def __next__(self):
        return self.context.run(next, self.iterator)


def _run_with_llm_user(user: User, fn):
    token = set_current_llm_user(user.id)
    try:
        return fn()
    finally:
        reset_current_llm_user(token)


def _stream_with_llm_user(user: User, events):
    def generator():
        token = set_current_llm_user(user.id)
        try:
            yield from events
        finally:
            reset_current_llm_user(token)
    return ContextPreservingIterator(generator())


def _leased_events(db: Session, game_id: int, request_id: str, events):
    try:
        yield from events
    finally:
        release_game_turn_lease(db, game_id, request_id)


def _acquire_lease_and_quota(db: Session, user: User, game_id: int, request_id: str) -> None:
    acquire_game_turn_lease(db, game_id, request_id)
    try:
        require_message_quota(db, user)
    except Exception:
        release_game_turn_lease(db, game_id, request_id)
        raise


@router.post("/games/{game_id}/turn")
def create_turn(game_id: int, payload: TurnRequest, db: Session = Depends(get_session), user: User = Depends(get_current_user)):
    require_game_access(db, game_id, user)
    request_id = normalize_request_id(payload.request_id)
    existing = find_turn_by_request_id(game_id, request_id, db)
    if existing:
        return saved_turn_result(existing)
    _acquire_lease_and_quota(db, user, game_id, request_id)
    try:
        return _run_with_llm_user(
            user,
            lambda: run_game_turn(
                game_id,
                payload.effective_user_input(),
                db,
                fast_mode=payload.fast_mode,
                skip_state_update=payload.skip_state_update,
                async_state_update=payload.async_state_update,
                request_id=request_id,
            ),
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    finally:
        release_game_turn_lease(db, game_id, request_id)


def _stream_json_events(events):
    try:
        for event in events:
            yield json.dumps(event, ensure_ascii=False, default=str) + "\n"
    except ValueError as exc:
        yield json.dumps({"type": "error", "code": "invalid_turn", "message": str(exc), "retryable": False}, ensure_ascii=False) + "\n"
    except Exception as exc:
        logger.exception("Turn stream failed")
        yield json.dumps(
            {"type": "error", "code": "stream_failed", "message": "流式生成失败，请稍后重试。", "retryable": True},
            ensure_ascii=False,
        ) + "\n"


@router.post("/games/{game_id}/turn/stream")
def create_turn_stream(game_id: int, payload: TurnRequest, db: Session = Depends(get_session), user: User = Depends(get_current_user)):
    require_game_access(db, game_id, user)
    request_id = normalize_request_id(payload.request_id)
    existing = find_turn_by_request_id(game_id, request_id, db)
    if existing:
        return StreamingResponse(
            _stream_json_events([{"type": "done", **saved_turn_result(existing)}]),
            media_type="application/x-ndjson",
        )
    _acquire_lease_and_quota(db, user, game_id, request_id)
    return StreamingResponse(
        _stream_json_events(
            _leased_events(
                db,
                game_id,
                request_id,
                _stream_with_llm_user(
                    user,
                    run_game_turn_stream(
                        game_id,
                        payload.effective_user_input(),
                        db,
                        fast_mode=payload.fast_mode,
                        skip_state_update=payload.skip_state_update,
                        async_state_update=payload.async_state_update,
                        request_id=request_id,
                    ),
                ),
            )
        ),
        media_type="application/x-ndjson",
    )


@router.post("/games/{game_id}/opening")
def create_opening(
    game_id: int,
    x_request_id: str | None = Header(default=None),
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    require_game_access(db, game_id, user)
    request_id = normalize_request_id(x_request_id)
    existing = find_turn_by_request_id(game_id, request_id, db)
    if existing:
        return {"ok": True, **saved_turn_result(existing)}
    _acquire_lease_and_quota(db, user, game_id, request_id)
    try:
        return _run_with_llm_user(user, lambda: run_opening_turn(game_id, db, request_id=request_id))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    finally:
        release_game_turn_lease(db, game_id, request_id)


@router.post("/games/{game_id}/opening/stream")
def create_opening_stream(
    game_id: int,
    x_request_id: str | None = Header(default=None),
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    require_game_access(db, game_id, user)
    request_id = normalize_request_id(x_request_id)
    existing = find_turn_by_request_id(game_id, request_id, db)
    if existing:
        return StreamingResponse(
            _stream_json_events([{"type": "done", **saved_turn_result(existing)}]),
            media_type="application/x-ndjson",
        )
    _acquire_lease_and_quota(db, user, game_id, request_id)
    return StreamingResponse(
        _stream_json_events(
            _leased_events(
                db,
                game_id,
                request_id,
                _stream_with_llm_user(user, run_opening_turn_stream(game_id, db, request_id=request_id)),
            )
        ),
        media_type="application/x-ndjson",
    )


@router.delete("/turns/{turn_id}/from-here")
def delete_from_turn(
    turn_id: int,
    game_id: int | None = None,
    turn_number: int | None = None,
    x_request_id: str | None = Header(default=None),
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    turn = get_turn_for_action(turn_id, db, game_id=game_id, turn_number=turn_number)
    require_game_access(db, turn.game_id, user)
    request_id = normalize_request_id(x_request_id)
    acquire_game_turn_lease(db, turn.game_id, request_id)
    try:
        return delete_turns_from(turn_id, db, game_id=game_id, turn_number=turn_number)
    finally:
        release_game_turn_lease(db, turn.game_id, request_id)


@router.post("/turns/{turn_id}/regenerate")
def regenerate_existing_turn(
    turn_id: int,
    game_id: int | None = None,
    turn_number: int | None = None,
    x_request_id: str | None = Header(default=None),
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    turn = get_turn_for_action(turn_id, db, game_id=game_id, turn_number=turn_number)
    require_game_access(db, turn.game_id, user)
    request_id = normalize_request_id(x_request_id)
    existing = find_turn_by_request_id(turn.game_id, request_id, db)
    if existing:
        return {"ok": True, "replayed": True, "result": saved_turn_result(existing)}
    _acquire_lease_and_quota(db, user, turn.game_id, request_id)
    try:
        return _run_with_llm_user(
            user,
            lambda: regenerate_turn(
                turn_id,
                db,
                game_id=game_id,
                turn_number=turn_number,
                request_id=request_id,
            ),
        )
    finally:
        release_game_turn_lease(db, turn.game_id, request_id)


@router.post("/turns/{turn_id}/regenerate/stream")
def regenerate_existing_turn_stream(
    turn_id: int,
    game_id: int | None = None,
    turn_number: int | None = None,
    x_request_id: str | None = Header(default=None),
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    turn = get_turn_for_action(turn_id, db, game_id=game_id, turn_number=turn_number)
    require_game_access(db, turn.game_id, user)
    game_id = turn.game_id
    request_id = normalize_request_id(x_request_id)
    existing = find_turn_by_request_id(game_id, request_id, db)
    if existing:
        return StreamingResponse(
            _stream_json_events([{"type": "done", **saved_turn_result(existing)}]),
            media_type="application/x-ndjson",
        )
    _acquire_lease_and_quota(db, user, game_id, request_id)
    user_input = turn.user_input

    def events():
        yield {"type": "status", "message": "正在回到这一轮之前..."}
        delete_turns_from(turn.id, db)
        if user_input:
            yield from run_game_turn_stream(game_id, user_input, db, request_id=request_id)
        else:
            yield from run_opening_turn_stream(game_id, db, request_id=request_id)

    return StreamingResponse(
        _stream_json_events(
            _leased_events(db, game_id, request_id, _stream_with_llm_user(user, events()))
        ),
        media_type="application/x-ndjson",
    )
