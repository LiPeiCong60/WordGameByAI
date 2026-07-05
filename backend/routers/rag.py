from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

import crud
from auth_service import get_current_user, require_game_access
from database import get_session
from models import RagMemory, User
from rag_service import rebuild_rag_memories, retrieve_related_memories, sync_rag_memories
from schemas import RagSearchRequest

router = APIRouter()


@router.get("/games/{game_id}/rag/memories")
def list_rag_memories(game_id: int, db: Session = Depends(get_session), user: User = Depends(get_current_user)):
    require_game_access(db, game_id, user)
    sync_rag_memories(game_id, db)
    return list(db.exec(select(RagMemory).where(RagMemory.game_id == game_id).order_by(RagMemory.updated_at.desc())).all())


@router.post("/games/{game_id}/rag/search")
def search_rag_memories(game_id: int, payload: RagSearchRequest, db: Session = Depends(get_session), user: User = Depends(get_current_user)):
    require_game_access(db, game_id, user)
    try:
        return {"items": retrieve_related_memories(game_id, payload.query, db, payload.top_k)}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/games/{game_id}/rag/rebuild")
def rebuild_game_rag(game_id: int, db: Session = Depends(get_session), user: User = Depends(get_current_user)):
    require_game_access(db, game_id, user)
    try:
        return rebuild_rag_memories(game_id, db)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
