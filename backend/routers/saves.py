from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from auth_service import get_current_user, require_game_access
from database import get_session
from export_import import export_game, import_game
from models import User
from schemas import ImportPayload

router = APIRouter()


@router.get("/games/{game_id}/export")
def export_save(game_id: int, db: Session = Depends(get_session), user: User = Depends(get_current_user)):
    require_game_access(db, game_id, user)
    try:
        return export_game(game_id, db)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/games/import")
def import_save(payload: ImportPayload, db: Session = Depends(get_session), user: User = Depends(get_current_user)):
    game = import_game(payload.model_dump(), db, owner_user_id=user.id)
    return {"ok": True, "game": game}
