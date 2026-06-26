from __future__ import annotations

from fastapi import HTTPException
from sqlmodel import Session, SQLModel, select

from models import (
    Character,
    Game,
    InventoryRecord,
    Item,
    ManagementProposal,
    ManagementSession,
    StoryWorld,
    TurnLog,
    TurnSnapshot,
    WorldEvent,
    WorldLore,
)


RELATED_GAME_MODELS: tuple[type[SQLModel], ...] = (
    InventoryRecord,
    TurnSnapshot,
    TurnLog,
    ManagementProposal,
    ManagementSession,
    Character,
    Item,
    StoryWorld,
    WorldLore,
    WorldEvent,
)


def delete_game_related_records(session: Session, game_id: int) -> dict[str, int]:
    """Delete records owned by one save without deleting global templates."""
    deleted: dict[str, int] = {}
    for model in RELATED_GAME_MODELS:
        records = list(session.exec(select(model).where(model.game_id == game_id)).all())
        deleted[model.__name__] = len(records)
        for record in records:
            session.delete(record)
    session.commit()
    return deleted


def delete_orphaned_game_records(session: Session) -> dict[str, int]:
    game_ids = {game.id for game in session.exec(select(Game)).all() if game.id is not None}
    deleted: dict[str, int] = {}
    for model in RELATED_GAME_MODELS:
        records = [record for record in session.exec(select(model)).all() if record.game_id not in game_ids]
        deleted[model.__name__] = len(records)
        for record in records:
            session.delete(record)
    session.commit()
    return deleted


def delete_game_cascade(session: Session, game_id: int) -> dict:
    game = session.get(Game, game_id)
    if game is None:
        raise HTTPException(status_code=404, detail=f"找不到游戏: {game_id}")

    deleted = delete_game_related_records(session, game_id)
    session.delete(game)
    session.commit()
    deleted["Game"] = 1
    return {"ok": True, "deleted": deleted}
