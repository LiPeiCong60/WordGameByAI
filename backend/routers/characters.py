from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, UploadFile
from sqlmodel import Session

import crud
from database import get_session
from models import Character, Game
from schemas import CharacterCreate, CharacterUpdate

router = APIRouter()
UPLOAD_DIR = Path(__file__).resolve().parents[1] / "uploads" / "characters"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@router.post("/games/{game_id}/characters")
def create_character(game_id: int, payload: CharacterCreate, db: Session = Depends(get_session)):
    crud.get_or_404(db, Game, game_id, "游戏")
    return crud.create_record(db, Character, payload, extra={"game_id": game_id})


@router.get("/games/{game_id}/characters")
def list_characters(game_id: int, db: Session = Depends(get_session)):
    return crud.list_by_game(db, Character, game_id)


@router.get("/characters/{character_id}")
def get_character(character_id: int, db: Session = Depends(get_session)):
    return crud.get_or_404(db, Character, character_id, "角色")


@router.patch("/characters/{character_id}")
def update_character(character_id: int, payload: CharacterUpdate, db: Session = Depends(get_session)):
    character = crud.get_or_404(db, Character, character_id, "角色")
    return crud.update_record(db, character, payload)


@router.delete("/characters/{character_id}")
def delete_character(character_id: int, db: Session = Depends(get_session)):
    character = crud.get_or_404(db, Character, character_id, "角色")
    return crud.delete_record(db, character)


@router.post("/characters/{character_id}/avatar")
async def upload_avatar(character_id: int, file: UploadFile = File(...), db: Session = Depends(get_session)):
    character = crud.get_or_404(db, Character, character_id, "角色")
    suffix = Path(file.filename or "avatar.png").suffix or ".png"
    filename = f"{character_id}-{uuid4().hex}{suffix}"
    target = UPLOAD_DIR / filename
    content = await file.read()
    target.write_bytes(content)
    avatar_url = f"/uploads/characters/{filename}"
    crud.update_record(db, character, {"avatar_url": avatar_url})
    return {"avatar_url": avatar_url}
