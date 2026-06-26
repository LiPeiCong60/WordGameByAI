from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlmodel import Session

import crud
from database import get_session
from game_delete_service import delete_game_cascade, delete_game_related_records
from models import Game
from schemas import GameCreate, GameUpdate
from starter_character_service import ensure_starter_characters

router = APIRouter()


@router.post("/games")
def create_game(payload: GameCreate, db: Session = Depends(get_session)):
    data = crud.to_data(payload)
    template_id = data.pop("template_id", None)
    game = crud.create_record(db, Game, data)
    # SQLite can reuse deleted integer IDs. Clear old orphaned save data for this
    # ID so a newly created save never inherits content from a previously deleted one.
    delete_game_related_records(db, game.id)
    db.refresh(game)
    ensure_starter_characters(db, game, template_id)
    db.refresh(game)
    return game


@router.get("/games")
def list_games(db: Session = Depends(get_session)):
    return crud.list_records(db, Game)


@router.get("/games/{game_id}")
def get_game(game_id: int, db: Session = Depends(get_session)):
    return crud.get_or_404(db, Game, game_id, "游戏")


@router.patch("/games/{game_id}")
def update_game(game_id: int, payload: GameUpdate, db: Session = Depends(get_session)):
    game = crud.get_or_404(db, Game, game_id, "游戏")
    return crud.update_record(db, game, payload)


@router.delete("/games/{game_id}")
def delete_game(game_id: int, db: Session = Depends(get_session)):
    return delete_game_cascade(db, game_id)
