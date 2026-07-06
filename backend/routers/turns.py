from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlmodel import Session

from auth_service import get_current_user, require_game_access
from database import get_session
from game_engine import run_game_turn, run_game_turn_stream, run_opening_turn, run_opening_turn_stream
from llm_client import reset_current_llm_user, set_current_llm_user
from message_quota_service import require_message_quota
from models import TurnLog, User
from schemas import TurnRequest
from turn_history_service import delete_turns_from, get_turn_for_action, regenerate_turn

router = APIRouter()


def _run_with_llm_user(user: User, fn):
    token = set_current_llm_user(user.id)
    try:
        return fn()
    finally:
        reset_current_llm_user(token)


def _stream_with_llm_user(user: User, events):
    token = set_current_llm_user(user.id)
    try:
        yield from events
    finally:
        reset_current_llm_user(token)


@router.post("/games/{game_id}/turn")
def create_turn(game_id: int, payload: TurnRequest, db: Session = Depends(get_session), user: User = Depends(get_current_user)):
    require_game_access(db, game_id, user)
    require_message_quota(db, user)
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
            ),
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


def _stream_json_events(events):
    try:
        for event in events:
            yield json.dumps(event, ensure_ascii=False, default=str) + "\n"
    except ValueError as exc:
        yield json.dumps({"type": "error", "message": str(exc)}, ensure_ascii=False) + "\n"
    except Exception as exc:
        yield json.dumps({"type": "error", "message": f"流式生成失败：{exc}"}, ensure_ascii=False) + "\n"


@router.post("/games/{game_id}/turn/stream")
def create_turn_stream(game_id: int, payload: TurnRequest, db: Session = Depends(get_session), user: User = Depends(get_current_user)):
    require_game_access(db, game_id, user)
    require_message_quota(db, user)
    return StreamingResponse(
        _stream_json_events(
            _stream_with_llm_user(
                user,
                run_game_turn_stream(
                    game_id,
                    payload.effective_user_input(),
                    db,
                    fast_mode=payload.fast_mode,
                    skip_state_update=payload.skip_state_update,
                    async_state_update=payload.async_state_update,
                ),
            )
        ),
        media_type="application/x-ndjson",
    )


@router.post("/games/{game_id}/opening")
def create_opening(game_id: int, db: Session = Depends(get_session), user: User = Depends(get_current_user)):
    require_game_access(db, game_id, user)
    require_message_quota(db, user)
    try:
        return _run_with_llm_user(user, lambda: run_opening_turn(game_id, db))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/games/{game_id}/opening/stream")
def create_opening_stream(game_id: int, db: Session = Depends(get_session), user: User = Depends(get_current_user)):
    require_game_access(db, game_id, user)
    require_message_quota(db, user)
    return StreamingResponse(
        _stream_json_events(_stream_with_llm_user(user, run_opening_turn_stream(game_id, db))),
        media_type="application/x-ndjson",
    )


@router.delete("/turns/{turn_id}/from-here")
def delete_from_turn(
    turn_id: int,
    game_id: int | None = None,
    turn_number: int | None = None,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    turn = get_turn_for_action(turn_id, db, game_id=game_id, turn_number=turn_number)
    require_game_access(db, turn.game_id, user)
    return delete_turns_from(turn_id, db, game_id=game_id, turn_number=turn_number)


@router.post("/turns/{turn_id}/regenerate")
def regenerate_existing_turn(
    turn_id: int,
    game_id: int | None = None,
    turn_number: int | None = None,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    turn = get_turn_for_action(turn_id, db, game_id=game_id, turn_number=turn_number)
    require_game_access(db, turn.game_id, user)
    require_message_quota(db, user)
    return _run_with_llm_user(user, lambda: regenerate_turn(turn_id, db, game_id=game_id, turn_number=turn_number))


@router.post("/turns/{turn_id}/regenerate/stream")
def regenerate_existing_turn_stream(
    turn_id: int,
    game_id: int | None = None,
    turn_number: int | None = None,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    turn = get_turn_for_action(turn_id, db, game_id=game_id, turn_number=turn_number)
    require_game_access(db, turn.game_id, user)
    require_message_quota(db, user)
    game_id = turn.game_id
    user_input = turn.user_input

    def events():
        yield {"type": "status", "message": "正在回到这一轮之前..."}
        delete_turns_from(turn.id, db)
        if user_input:
            yield from run_game_turn_stream(game_id, user_input, db)
        else:
            yield from run_opening_turn_stream(game_id, db)

    return StreamingResponse(_stream_json_events(_stream_with_llm_user(user, events())), media_type="application/x-ndjson")
