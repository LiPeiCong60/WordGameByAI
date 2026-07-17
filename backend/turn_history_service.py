from __future__ import annotations

from datetime import datetime

from fastapi import HTTPException
from sqlmodel import Session, select

from game_engine import run_game_turn, run_opening_turn
from json_utils import parse_json_field
from models import (
    Character,
    Game,
    RagMemory,
    StoryWorld,
    TurnLog,
    TurnSnapshot,
    WorldLore,
)

SNAPSHOT_MODELS = [
    (StoryWorld, "story_worlds"),
    (WorldLore, "world_lore"),
    (Character, "characters"),
    (TurnLog, "turn_logs"),
    (RagMemory, "rag_memories"),
]


def _strip_runtime_fields(row: dict) -> dict:
    data = dict(row)
    for key in ["created_at", "updated_at", "applied_at"]:
        value = data.get(key)
        if isinstance(value, str):
            try:
                data[key] = datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                data.pop(key, None)
    return data


def _get_turn(db: Session, turn_id: int, game_id: int | None = None, turn_number: int | None = None) -> TurnLog:
    turn = db.get(TurnLog, turn_id)
    if turn:
        return turn
    if game_id and turn_number:
        turn = db.exec(
            select(TurnLog).where(TurnLog.game_id == game_id, TurnLog.turn_number == turn_number)
        ).first()
    if not turn:
        fallback = f"，game_id={game_id}, turn_number={turn_number}" if game_id and turn_number else ""
        raise HTTPException(status_code=404, detail=f"找不到剧情记录: {turn_id}{fallback}")
    return turn


def _get_snapshot(db: Session, turn: TurnLog) -> TurnSnapshot | None:
    if turn.id is not None:
        snapshot = db.exec(
            select(TurnSnapshot).where(TurnSnapshot.turn_id == turn.id).order_by(TurnSnapshot.id.desc())
        ).first()
        if snapshot:
            return snapshot
    return db.exec(
        select(TurnSnapshot)
        .where(TurnSnapshot.game_id == turn.game_id, TurnSnapshot.turn_number == turn.turn_number)
        .order_by(TurnSnapshot.id.desc())
    ).first()


def restore_game_snapshot(game_id: int, snapshot_payload: dict, db: Session) -> None:
    game = db.get(Game, game_id)
    if not game:
        raise HTTPException(status_code=404, detail=f"找不到游戏: {game_id}")

    game_data = snapshot_payload.get("game") or {}
    for key in [
        "title",
        "genre",
        "world_type",
        "tone",
        "narrative_perspective",
        "style_guide",
        "rules_summary",
        "current_state",
        "current_story_world_id",
    ]:
        if key in game_data:
            setattr(game, key, game_data[key])
    db.add(game)

    for model, _key in reversed(SNAPSHOT_MODELS):
        for record in db.exec(select(model).where(model.game_id == game_id)).all():
            db.delete(record)
    db.commit()

    for model, key in SNAPSHOT_MODELS:
        for row in snapshot_payload.get(key, []) or []:
            data = _strip_runtime_fields(row)
            data["game_id"] = game_id
            db.add(model(**data))
    db.commit()


def get_turn_for_action(
    turn_id: int,
    db: Session,
    game_id: int | None = None,
    turn_number: int | None = None,
) -> TurnLog:
    return _get_turn(db, turn_id, game_id=game_id, turn_number=turn_number)


def delete_turns_from(
    turn_id: int,
    db: Session,
    game_id: int | None = None,
    turn_number: int | None = None,
) -> dict:
    turn = _get_turn(db, turn_id, game_id=game_id, turn_number=turn_number)
    snapshot = _get_snapshot(db, turn)
    if snapshot:
        payload = parse_json_field(snapshot.snapshot_json, default={})
        restore_game_snapshot(turn.game_id, payload, db)
        return {
            "ok": True,
            "game_id": turn.game_id,
            "deleted_from_turn": turn.turn_number,
            "restored_snapshot": True,
            "message": "已恢复到该轮剧情之前，并删除该轮及之后的剧情。",
        }

    later_turns = db.exec(
        select(TurnLog).where(TurnLog.game_id == turn.game_id, TurnLog.turn_number >= turn.turn_number)
    ).all()
    for record in later_turns:
        db.delete(record)
    db.commit()
    return {
        "ok": True,
        "game_id": turn.game_id,
        "deleted_from_turn": turn.turn_number,
        "restored_snapshot": False,
        "message": "旧剧情没有回滚快照，已删除该轮及之后的剧情文本；世界状态未自动回滚。",
    }


def regenerate_turn(
    turn_id: int,
    db: Session,
    game_id: int | None = None,
    turn_number: int | None = None,
    request_id: str | None = None,
) -> dict:
    turn = _get_turn(db, turn_id, game_id=game_id, turn_number=turn_number)
    user_input = turn.user_input
    rollback_result = delete_turns_from(turn.id, db)
    result = (
        run_game_turn(turn.game_id, user_input, db, request_id=request_id)
        if user_input
        else run_opening_turn(turn.game_id, db, request_id=request_id)
    )
    return {
        "ok": True,
        "rollback": rollback_result,
        "result": result,
    }
