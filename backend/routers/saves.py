from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from database import get_session
from export_import import export_game, import_game
from schemas import ImportPayload

router = APIRouter()


@router.get("/games/{game_id}/export")
def export_save(game_id: int, db: Session = Depends(get_session)):
    try:
        return export_game(game_id, db)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/games/import")
def import_save(payload: ImportPayload, db: Session = Depends(get_session)):
    game = import_game(payload.model_dump(), db)
    return {"ok": True, "game": game}
