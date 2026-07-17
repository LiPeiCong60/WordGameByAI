from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlmodel import Session

import crud
from auth_service import get_current_user, require_game_access, require_record_game_access
from database import get_session
from models import Character, User
from schemas import CharacterCreate, CharacterUpdate

router = APIRouter()
UPLOAD_DIR = Path(__file__).resolve().parents[1] / "uploads" / "characters"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
MAX_AVATAR_BYTES = 2 * 1024 * 1024
ALLOWED_AVATAR_TYPES = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/webp": ".webp",
}


def _valid_image_signature(content_type: str, content: bytes) -> bool:
    if content_type == "image/png":
        return content.startswith(b"\x89PNG\r\n\x1a\n")
    if content_type == "image/jpeg":
        return content.startswith(b"\xff\xd8\xff")
    if content_type == "image/webp":
        return len(content) >= 12 and content.startswith(b"RIFF") and content[8:12] == b"WEBP"
    return False


def _delete_local_avatar(avatar_url: str) -> None:
    prefix = "/uploads/characters/"
    if not avatar_url.startswith(prefix):
        return
    candidate = (UPLOAD_DIR / avatar_url.removeprefix(prefix)).resolve()
    if candidate.parent == UPLOAD_DIR.resolve():
        candidate.unlink(missing_ok=True)


@router.post("/games/{game_id}/characters")
def create_character(game_id: int, payload: CharacterCreate, db: Session = Depends(get_session), user: User = Depends(get_current_user)):
    require_game_access(db, game_id, user)
    return crud.create_record(db, Character, payload, extra={"game_id": game_id})


@router.get("/games/{game_id}/characters")
def list_characters(game_id: int, db: Session = Depends(get_session), user: User = Depends(get_current_user)):
    require_game_access(db, game_id, user)
    return crud.list_by_game(db, Character, game_id)


@router.get("/characters/{character_id}")
def get_character(character_id: int, db: Session = Depends(get_session), user: User = Depends(get_current_user)):
    character = crud.get_or_404(db, Character, character_id, "角色")
    require_record_game_access(db, character, user)
    return character


@router.patch("/characters/{character_id}")
def update_character(character_id: int, payload: CharacterUpdate, db: Session = Depends(get_session), user: User = Depends(get_current_user)):
    character = crud.get_or_404(db, Character, character_id, "角色")
    require_record_game_access(db, character, user)
    return crud.update_record(db, character, payload)


@router.delete("/characters/{character_id}")
def delete_character(character_id: int, db: Session = Depends(get_session), user: User = Depends(get_current_user)):
    character = crud.get_or_404(db, Character, character_id, "角色")
    require_record_game_access(db, character, user)
    avatar_url = character.avatar_url
    result = crud.delete_record(db, character)
    _delete_local_avatar(avatar_url)
    return result


@router.post("/characters/{character_id}/avatar")
async def upload_avatar(character_id: int, file: UploadFile = File(...), db: Session = Depends(get_session), user: User = Depends(get_current_user)):
    character = crud.get_or_404(db, Character, character_id, "角色")
    require_record_game_access(db, character, user)
    content_type = (file.content_type or "").lower()
    if content_type not in ALLOWED_AVATAR_TYPES:
        raise HTTPException(status_code=400, detail="只允许上传 PNG/JPEG/WebP 图片。")
    suffix = ALLOWED_AVATAR_TYPES[content_type]
    filename = f"{character_id}-{uuid4().hex}{suffix}"
    target = UPLOAD_DIR / filename
    content = await file.read(MAX_AVATAR_BYTES + 1)
    if len(content) > MAX_AVATAR_BYTES:
        raise HTTPException(status_code=413, detail="头像不能超过 2MB。")
    if not _valid_image_signature(content_type, content):
        raise HTTPException(status_code=400, detail="图片内容与声明的格式不一致。")
    old_avatar_url = character.avatar_url
    target.write_bytes(content)
    avatar_url = f"/uploads/characters/{filename}"
    crud.update_record(db, character, {"avatar_url": avatar_url})
    if old_avatar_url != avatar_url:
        _delete_local_avatar(old_avatar_url)
    return {"avatar_url": avatar_url}


@router.delete("/characters/{character_id}/avatar")
def delete_avatar(character_id: int, db: Session = Depends(get_session), user: User = Depends(get_current_user)):
    character = crud.get_or_404(db, Character, character_id, "角色")
    require_record_game_access(db, character, user)
    old_avatar_url = character.avatar_url
    crud.update_record(db, character, {"avatar_url": ""})
    _delete_local_avatar(old_avatar_url)
    return {"avatar_url": ""}
