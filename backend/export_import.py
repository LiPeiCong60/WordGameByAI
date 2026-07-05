from __future__ import annotations

from sqlmodel import Session, select

from models import (
    Character,
    Game,
    ManagementProposal,
    ManagementSession,
    RagMemory,
    StoryWorld,
    TurnLog,
    WorldLore,
)


def _dump(record) -> dict:
    return record.model_dump() if hasattr(record, "model_dump") else record.dict()


def export_game(game_id: int, db: Session) -> dict:
    game = db.get(Game, game_id)
    if not game:
        raise ValueError(f"找不到游戏: {game_id}")
    return {
        "game": _dump(game),
        "story_worlds": [_dump(x) for x in db.exec(select(StoryWorld).where(StoryWorld.game_id == game_id)).all()],
        "world_lore": [_dump(x) for x in db.exec(select(WorldLore).where(WorldLore.game_id == game_id)).all()],
        "characters": [_dump(x) for x in db.exec(select(Character).where(Character.game_id == game_id)).all()],
        "turn_logs": [_dump(x) for x in db.exec(select(TurnLog).where(TurnLog.game_id == game_id)).all()],
        "rag_memories": [_dump(x) for x in db.exec(select(RagMemory).where(RagMemory.game_id == game_id)).all()],
        "management_sessions": [_dump(x) for x in db.exec(select(ManagementSession).where(ManagementSession.game_id == game_id)).all()],
        "management_proposals": [_dump(x) for x in db.exec(select(ManagementProposal).where(ManagementProposal.game_id == game_id)).all()],
    }


def _strip_system_fields(data: dict, keep: set[str] | None = None) -> dict:
    keep = keep or set()
    system_fields = {"id", "game_id", "created_at", "updated_at", "applied_at"}
    return {k: v for k, v in data.items() if k not in system_fields or k in keep}


def import_game(payload: dict, db: Session, owner_user_id: int | None = None) -> Game:
    game_data = _strip_system_fields(payload["game"])
    old_game_id = payload["game"].get("id")
    old_current_world_id = payload["game"].get("current_story_world_id")
    game_data["current_story_world_id"] = None
    game_data["owner_user_id"] = owner_user_id
    game = Game(**game_data)
    db.add(game)
    db.commit()
    db.refresh(game)

    world_map: dict[int, int] = {}
    char_map: dict[int, int] = {}
    session_map: dict[int, int] = {}

    for row in payload.get("story_worlds", []):
        old_id = row.get("id")
        record = StoryWorld(**_strip_system_fields(row), game_id=game.id)
        db.add(record)
        db.commit()
        db.refresh(record)
        if old_id:
            world_map[old_id] = record.id

    if old_current_world_id in world_map:
        game.current_story_world_id = world_map[old_current_world_id]
        db.add(game)
        db.commit()
        db.refresh(game)

    for row in payload.get("world_lore", []):
        db.add(WorldLore(**_strip_system_fields(row), game_id=game.id))
    db.commit()

    for row in payload.get("characters", []):
        old_id = row.get("id")
        record = Character(**_strip_system_fields(row), game_id=game.id)
        db.add(record)
        db.commit()
        db.refresh(record)
        if old_id:
            char_map[old_id] = record.id

    for row in payload.get("turn_logs", []):
        db.add(TurnLog(**_strip_system_fields(row), game_id=game.id))
    db.commit()

    for row in payload.get("rag_memories", []):
        db.add(RagMemory(**_strip_system_fields(row), game_id=game.id))
    db.commit()

    for row in payload.get("management_sessions", []):
        old_id = row.get("id")
        record = ManagementSession(**_strip_system_fields(row), game_id=game.id)
        db.add(record)
        db.commit()
        db.refresh(record)
        if old_id:
            session_map[old_id] = record.id

    for row in payload.get("management_proposals", []):
        data = _strip_system_fields(row)
        data["game_id"] = game.id
        if data.get("session_id") in session_map:
            data["session_id"] = session_map[data["session_id"]]
        db.add(ManagementProposal(**data))
    db.commit()
    db.refresh(game)
    return game
