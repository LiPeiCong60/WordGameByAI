from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlmodel import Session

from database import get_session
from game_engine import run_game_turn, run_game_turn_stream, run_opening_turn, run_opening_turn_stream
from models import TurnLog
from schemas import TurnRequest
from turn_history_service import delete_turns_from, regenerate_turn

router = APIRouter()


@router.post("/games/{game_id}/turn")
def create_turn(game_id: int, payload: TurnRequest, db: Session = Depends(get_session)):
    try:
        return run_game_turn(game_id, payload.user_input, db)
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
def create_turn_stream(game_id: int, payload: TurnRequest, db: Session = Depends(get_session)):
    return StreamingResponse(
        _stream_json_events(run_game_turn_stream(game_id, payload.user_input, db)),
        media_type="application/x-ndjson",
    )


@router.post("/games/{game_id}/opening")
def create_opening(game_id: int, db: Session = Depends(get_session)):
    try:
        return run_opening_turn(game_id, db)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/games/{game_id}/opening/stream")
def create_opening_stream(game_id: int, db: Session = Depends(get_session)):
    return StreamingResponse(
        _stream_json_events(run_opening_turn_stream(game_id, db)),
        media_type="application/x-ndjson",
    )


@router.delete("/turns/{turn_id}/from-here")
def delete_from_turn(turn_id: int, db: Session = Depends(get_session)):
    return delete_turns_from(turn_id, db)


@router.post("/turns/{turn_id}/regenerate")
def regenerate_existing_turn(turn_id: int, db: Session = Depends(get_session)):
    return regenerate_turn(turn_id, db)


@router.post("/turns/{turn_id}/regenerate/stream")
def regenerate_existing_turn_stream(turn_id: int, db: Session = Depends(get_session)):
    turn = db.get(TurnLog, turn_id)
    if not turn:
        raise HTTPException(status_code=404, detail=f"找不到剧情记录: {turn_id}")
    game_id = turn.game_id
    user_input = turn.user_input

    def events():
        yield {"type": "status", "message": "正在回到这一轮之前..."}
        delete_turns_from(turn_id, db)
        if user_input:
            yield from run_game_turn_stream(game_id, user_input, db)
        else:
            yield from run_opening_turn_stream(game_id, db)

    return StreamingResponse(_stream_json_events(events()), media_type="application/x-ndjson")
