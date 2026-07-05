from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlmodel import Session

import crud
from agents.lore_agent import run_lore_agent
from auth_service import get_current_user, require_game_access, require_record_game_access
from database import get_session
from models import User, WorldLore
from schemas import LoreCreate, LoreOrganizeRequest, LoreUpdate

router = APIRouter()


@router.post("/games/{game_id}/lore")
def create_lore(game_id: int, payload: LoreCreate, db: Session = Depends(get_session), user: User = Depends(get_current_user)):
    require_game_access(db, game_id, user)
    return crud.create_record(db, WorldLore, payload, extra={"game_id": game_id})


@router.get("/games/{game_id}/lore")
def list_lore(game_id: int, db: Session = Depends(get_session), user: User = Depends(get_current_user)):
    require_game_access(db, game_id, user)
    return crud.list_by_game(db, WorldLore, game_id)


@router.get("/lore/{lore_id}")
def get_lore(lore_id: int, db: Session = Depends(get_session), user: User = Depends(get_current_user)):
    lore = crud.get_or_404(db, WorldLore, lore_id, "世界观")
    require_record_game_access(db, lore, user)
    return lore


@router.patch("/lore/{lore_id}")
def update_lore(lore_id: int, payload: LoreUpdate, db: Session = Depends(get_session), user: User = Depends(get_current_user)):
    lore = crud.get_or_404(db, WorldLore, lore_id, "世界观")
    require_record_game_access(db, lore, user)
    return crud.update_record(db, lore, payload)


@router.delete("/lore/{lore_id}")
def delete_lore(lore_id: int, db: Session = Depends(get_session), user: User = Depends(get_current_user)):
    lore = crud.get_or_404(db, WorldLore, lore_id, "世界观")
    require_record_game_access(db, lore, user)
    return crud.delete_record(db, lore)


@router.post("/games/{game_id}/lore/organize")
def organize_lore(game_id: int, payload: LoreOrganizeRequest, db: Session = Depends(get_session), user: User = Depends(get_current_user)):
    require_game_access(db, game_id, user)
    return run_lore_agent(payload.text)
