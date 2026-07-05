from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlmodel import Session

from database import engine, init_db
from game_delete_service import delete_orphaned_game_records
from routers import admin, auth, characters, games, lore, management, rag, saves, story_worlds, templates, turns

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
(UPLOAD_DIR / "characters").mkdir(parents=True, exist_ok=True)

app = FastAPI(title="NarrativeAgent Demo", version="0.1.0")
allowed_origins = [
    origin.strip()
    for origin in os.getenv("CORS_ALLOW_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173,http://127.0.0.1:5175").split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")

app.include_router(auth.router, prefix="/api", tags=["auth"])
app.include_router(admin.router, prefix="/api", tags=["admin"])
app.include_router(games.router, prefix="/api", tags=["games"])
app.include_router(templates.router, prefix="/api", tags=["templates"])
app.include_router(story_worlds.router, prefix="/api", tags=["story-worlds"])
app.include_router(lore.router, prefix="/api", tags=["lore"])
app.include_router(characters.router, prefix="/api", tags=["characters"])
app.include_router(turns.router, prefix="/api", tags=["turns"])
app.include_router(management.router, prefix="/api", tags=["management"])
app.include_router(rag.router, prefix="/api", tags=["rag"])
app.include_router(saves.router, prefix="/api", tags=["saves"])


@app.on_event("startup")
def on_startup() -> None:
    init_db()
    with Session(engine) as session:
        delete_orphaned_game_records(session)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
