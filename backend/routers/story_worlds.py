from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlmodel import Session

import crud
from database import get_session
from models import Game, StoryWorld
from schemas import StoryWorldCreate, StoryWorldUpdate

router = APIRouter()


@router.post("/games/{game_id}/story-worlds")
def create_story_world(game_id: int, payload: StoryWorldCreate, db: Session = Depends(get_session)):
    crud.get_or_404(db, Game, game_id, "游戏")
    world = crud.create_record(db, StoryWorld, payload, extra={"game_id": game_id})
    game = db.get(Game, game_id)
    if game and not game.current_story_world_id:
        game.current_story_world_id = world.id
        crud.update_record(db, game, {"current_story_world_id": world.id})
        db.refresh(world)
    return world


@router.get("/games/{game_id}/story-worlds")
def list_story_worlds(game_id: int, db: Session = Depends(get_session)):
    return crud.list_by_game(db, StoryWorld, game_id)


@router.get("/story-worlds/{world_id}")
def get_story_world(world_id: int, db: Session = Depends(get_session)):
    return crud.get_or_404(db, StoryWorld, world_id, "世界")


@router.patch("/story-worlds/{world_id}")
def update_story_world(world_id: int, payload: StoryWorldUpdate, db: Session = Depends(get_session)):
    world = crud.get_or_404(db, StoryWorld, world_id, "世界")
    return crud.update_record(db, world, payload)


@router.delete("/story-worlds/{world_id}")
def delete_story_world(world_id: int, db: Session = Depends(get_session)):
    world = crud.get_or_404(db, StoryWorld, world_id, "世界")
    return crud.delete_record(db, world)


@router.post("/games/{game_id}/story-worlds/{world_id}/set-current")
def set_current_story_world(game_id: int, world_id: int, db: Session = Depends(get_session)):
    game = crud.get_or_404(db, Game, game_id, "游戏")
    crud.get_or_404(db, StoryWorld, world_id, "世界")
    return crud.update_record(db, game, {"current_story_world_id": world_id})
