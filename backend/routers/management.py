from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlmodel import Session

import crud
from database import get_session
from management_service import (
    apply_management_proposal,
    create_management_session,
    reject_management_proposal,
    run_management_chat,
)
from models import ManagementProposal, ManagementSession
from schemas import ManagementChatRequest, ManagementSessionCreate

router = APIRouter()


@router.post("/games/{game_id}/management/sessions")
def create_session(game_id: int, payload: ManagementSessionCreate, db: Session = Depends(get_session)):
    return create_management_session(game_id, db, payload.title)


@router.get("/games/{game_id}/management/sessions")
def list_sessions(game_id: int, db: Session = Depends(get_session)):
    return crud.list_by_game(db, ManagementSession, game_id)


@router.get("/management/sessions/{session_id}")
def get_session_record(session_id: int, db: Session = Depends(get_session)):
    return crud.get_or_404(db, ManagementSession, session_id, "管理会话")


@router.post("/management/sessions/{session_id}/chat")
def chat(session_id: int, payload: ManagementChatRequest, db: Session = Depends(get_session)):
    return run_management_chat(session_id, payload.message, db, payload.scope)


@router.get("/management/proposals/{proposal_id}")
def get_proposal(proposal_id: int, db: Session = Depends(get_session)):
    return crud.get_or_404(db, ManagementProposal, proposal_id, "修改方案")


@router.post("/management/proposals/{proposal_id}/apply")
def apply_proposal(proposal_id: int, db: Session = Depends(get_session)):
    return apply_management_proposal(proposal_id, db)


@router.post("/management/proposals/{proposal_id}/reject")
def reject_proposal(proposal_id: int, db: Session = Depends(get_session)):
    return reject_management_proposal(proposal_id, db)
