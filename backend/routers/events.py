from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlmodel import Session

import crud
from database import get_session
from models import Game, WorldEvent
from schemas import EventCreate, EventUpdate

router = APIRouter()


@router.post("/games/{game_id}/events")
def create_event(game_id: int, payload: EventCreate, db: Session = Depends(get_session)):
    crud.get_or_404(db, Game, game_id, "游戏")
    return crud.create_record(db, WorldEvent, payload, extra={"game_id": game_id})


@router.get("/games/{game_id}/events")
def list_events(game_id: int, db: Session = Depends(get_session)):
    return crud.list_by_game(db, WorldEvent, game_id)


@router.get("/events/{event_id}")
def get_event(event_id: int, db: Session = Depends(get_session)):
    return crud.get_or_404(db, WorldEvent, event_id, "事件")


@router.patch("/events/{event_id}")
def update_event(event_id: int, payload: EventUpdate, db: Session = Depends(get_session)):
    event = crud.get_or_404(db, WorldEvent, event_id, "事件")
    return crud.update_record(db, event, payload)


@router.delete("/events/{event_id}")
def delete_event(event_id: int, db: Session = Depends(get_session)):
    event = crud.get_or_404(db, WorldEvent, event_id, "事件")
    return crud.delete_record(db, event)
