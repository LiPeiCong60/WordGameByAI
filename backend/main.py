from __future__ import annotations

import os
from pathlib import Path

from fastapi import APIRouter, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlmodel import Session
from sqlalchemy import text

from database import engine, init_db
from game_delete_service import delete_orphaned_game_records
from game_engine import recover_pending_state_jobs
from routers import admin, auth, characters, games, lore, management, mobile, rag, saves, story_worlds, templates, turns

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

# Versioned API for native/mobile clients. Legacy /api routes remain available
# so the existing Vue deployment continues to work during migration.
v1 = APIRouter(prefix="/api/v1")
v1.include_router(auth.router, tags=["v1-auth"])
v1.include_router(admin.router, tags=["v1-admin"])
v1.include_router(games.router, tags=["v1-games"])
v1.include_router(templates.router, tags=["v1-templates"])
v1.include_router(story_worlds.router, tags=["v1-story-worlds"])
v1.include_router(lore.router, tags=["v1-lore"])
v1.include_router(characters.router, tags=["v1-characters"])
v1.include_router(turns.router, tags=["v1-turns"])
v1.include_router(management.router, tags=["v1-management"])
v1.include_router(rag.router, tags=["v1-rag"])
v1.include_router(saves.router, tags=["v1-saves"])
v1.include_router(mobile.router, tags=["v1-mobile"])
app.include_router(v1)


@app.on_event("startup")
def on_startup() -> None:
    init_db()
    with Session(engine) as session:
        delete_orphaned_game_records(session)
    recover_pending_state_jobs()


@app.get("/api/health")
@app.get("/api/v1/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/ready")
@app.get("/api/v1/ready")
def readiness() -> dict[str, str]:
    try:
        with Session(engine) as session:
            session.exec(text("SELECT 1")).one()
    except Exception as exc:
        raise HTTPException(status_code=503, detail="database_unavailable") from exc
    return {"status": "ready"}
