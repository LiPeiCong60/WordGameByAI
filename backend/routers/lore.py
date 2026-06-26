from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlmodel import Session

import crud
from agents.lore_agent import run_lore_agent
from database import get_session
from models import Game, WorldLore
from schemas import LoreCreate, LoreOrganizeRequest, LoreUpdate

router = APIRouter()


@router.post("/games/{game_id}/lore")
def create_lore(game_id: int, payload: LoreCreate, db: Session = Depends(get_session)):
    crud.get_or_404(db, Game, game_id, "游戏")
    return crud.create_record(db, WorldLore, payload, extra={"game_id": game_id})


@router.get("/games/{game_id}/lore")
def list_lore(game_id: int, db: Session = Depends(get_session)):
    return crud.list_by_game(db, WorldLore, game_id)


@router.get("/lore/{lore_id}")
def get_lore(lore_id: int, db: Session = Depends(get_session)):
    return crud.get_or_404(db, WorldLore, lore_id, "世界观")


@router.patch("/lore/{lore_id}")
def update_lore(lore_id: int, payload: LoreUpdate, db: Session = Depends(get_session)):
    lore = crud.get_or_404(db, WorldLore, lore_id, "世界观")
    return crud.update_record(db, lore, payload)


@router.delete("/lore/{lore_id}")
def delete_lore(lore_id: int, db: Session = Depends(get_session)):
    lore = crud.get_or_404(db, WorldLore, lore_id, "世界观")
    return crud.delete_record(db, lore)


@router.post("/games/{game_id}/lore/organize")
def organize_lore(game_id: int, payload: LoreOrganizeRequest, db: Session = Depends(get_session)):
    crud.get_or_404(db, Game, game_id, "游戏")
    return run_lore_agent(payload.text)
