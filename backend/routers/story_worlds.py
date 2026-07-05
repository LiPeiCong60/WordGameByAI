from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

import crud
from auth_service import get_current_user, require_game_access, require_record_game_access
from database import get_session
from models import Game, StoryWorld, User
from schemas import StoryWorldCreate, StoryWorldUpdate

router = APIRouter()


@router.post("/games/{game_id}/story-worlds")
def create_story_world(game_id: int, payload: StoryWorldCreate, db: Session = Depends(get_session), user: User = Depends(get_current_user)):
    require_game_access(db, game_id, user)
    world = crud.create_record(db, StoryWorld, payload, extra={"game_id": game_id})
    game = db.get(Game, game_id)
    if game and not game.current_story_world_id:
        game.current_story_world_id = world.id
        crud.update_record(db, game, {"current_story_world_id": world.id})
        db.refresh(world)
    return world


@router.get("/games/{game_id}/story-worlds")
def list_story_worlds(game_id: int, db: Session = Depends(get_session), user: User = Depends(get_current_user)):
    require_game_access(db, game_id, user)
    return crud.list_by_game(db, StoryWorld, game_id)


@router.get("/story-worlds/{world_id}")
def get_story_world(world_id: int, db: Session = Depends(get_session), user: User = Depends(get_current_user)):
    world = crud.get_or_404(db, StoryWorld, world_id, "世界")
    require_record_game_access(db, world, user)
    return world


@router.patch("/story-worlds/{world_id}")
def update_story_world(world_id: int, payload: StoryWorldUpdate, db: Session = Depends(get_session), user: User = Depends(get_current_user)):
    world = crud.get_or_404(db, StoryWorld, world_id, "世界")
    require_record_game_access(db, world, user)
    return crud.update_record(db, world, payload)


@router.delete("/story-worlds/{world_id}")
def delete_story_world(world_id: int, db: Session = Depends(get_session), user: User = Depends(get_current_user)):
    world = crud.get_or_404(db, StoryWorld, world_id, "世界")
    require_record_game_access(db, world, user)
    return crud.delete_record(db, world)


@router.post("/games/{game_id}/story-worlds/{world_id}/set-current")
def set_current_story_world(game_id: int, world_id: int, db: Session = Depends(get_session), user: User = Depends(get_current_user)):
    game = require_game_access(db, game_id, user)
    world = crud.get_or_404(db, StoryWorld, world_id, "世界")
    if world.game_id != game_id:
        raise HTTPException(status_code=400, detail="世界不属于该游戏。")
    return crud.update_record(db, game, {"current_story_world_id": world_id})
