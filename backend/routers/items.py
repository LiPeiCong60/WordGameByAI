from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlmodel import Session

import crud
from database import get_session
from models import Game, Item
from schemas import ItemCreate, ItemUpdate

router = APIRouter()


@router.post("/games/{game_id}/items")
def create_item(game_id: int, payload: ItemCreate, db: Session = Depends(get_session)):
    crud.get_or_404(db, Game, game_id, "游戏")
    return crud.create_record(db, Item, payload, extra={"game_id": game_id})


@router.get("/games/{game_id}/items")
def list_items(game_id: int, db: Session = Depends(get_session)):
    return crud.list_by_game(db, Item, game_id)


@router.get("/items/{item_id}")
def get_item(item_id: int, db: Session = Depends(get_session)):
    return crud.get_or_404(db, Item, item_id, "物品")


@router.patch("/items/{item_id}")
def update_item(item_id: int, payload: ItemUpdate, db: Session = Depends(get_session)):
    item = crud.get_or_404(db, Item, item_id, "物品")
    return crud.update_record(db, item, payload)


@router.delete("/items/{item_id}")
def delete_item(item_id: int, db: Session = Depends(get_session)):
    item = crud.get_or_404(db, Item, item_id, "物品")
    return crud.delete_record(db, item)
