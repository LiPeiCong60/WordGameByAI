from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc
from sqlmodel import Session, select

import crud
from auth_service import get_current_user, require_game_access, require_record_game_access
from database import get_session
from llm_client import reset_current_llm_user, set_current_llm_user
from message_quota_service import require_message_quota
from management_service import (
    apply_management_proposal,
    create_management_session,
    list_management_messages,
    reject_management_proposal,
    run_management_chat,
)
from models import ManagementProposal, ManagementSession, User
from schemas import ManagementChatRequest, ManagementSessionCreate

router = APIRouter()


def require_management_access(game_id: int, user: User, db: Session) -> None:
    if game_id == 0:
        return
    require_game_access(db, game_id, user)


def require_management_record_access(record, user: User, db: Session) -> None:
    game_id = getattr(record, "game_id", None)
    if game_id == 0:
        if user.is_admin or getattr(record, "owner_user_id", None) == user.id:
            return
        raise HTTPException(status_code=403, detail="无权访问其他用户的模板智能体会话。")
        return
    require_record_game_access(db, record, user)


@router.post("/games/{game_id}/management/sessions")
def create_session(game_id: int, payload: ManagementSessionCreate, db: Session = Depends(get_session), user: User = Depends(get_current_user)):
    require_management_access(game_id, user, db)
    return create_management_session(game_id, db, payload.title, owner_user_id=user.id if game_id == 0 else None)


@router.get("/games/{game_id}/management/sessions")
def list_sessions(game_id: int, db: Session = Depends(get_session), user: User = Depends(get_current_user)):
    require_management_access(game_id, user, db)
    if game_id == 0:
        query = select(ManagementSession).where(
            ManagementSession.game_id == 0,
            ManagementSession.owner_user_id == user.id,
        )
    else:
        query = select(ManagementSession).where(ManagementSession.game_id == game_id)
    return list(db.exec(query.order_by(desc(ManagementSession.updated_at), desc(ManagementSession.id))).all())


@router.get("/management/sessions/{session_id}")
def get_session_record(session_id: int, db: Session = Depends(get_session), user: User = Depends(get_current_user)):
    session = crud.get_or_404(db, ManagementSession, session_id, "管理会话")
    require_management_record_access(session, user, db)
    return session


@router.get("/management/sessions/{session_id}/messages")
def get_session_messages(session_id: int, db: Session = Depends(get_session), user: User = Depends(get_current_user)):
    session = crud.get_or_404(db, ManagementSession, session_id, "管理会话")
    require_management_record_access(session, user, db)
    return list_management_messages(db, session_id)


@router.post("/management/sessions/{session_id}/chat")
def chat(session_id: int, payload: ManagementChatRequest, db: Session = Depends(get_session), user: User = Depends(get_current_user)):
    session = crud.get_or_404(db, ManagementSession, session_id, "管理会话")
    require_management_record_access(session, user, db)
    require_message_quota(db, user)
    token = set_current_llm_user(user.id)
    try:
        return run_management_chat(session_id, payload.message, db, payload.scope, user)
    finally:
        reset_current_llm_user(token)


@router.get("/management/proposals/{proposal_id}")
def get_proposal(proposal_id: int, db: Session = Depends(get_session), user: User = Depends(get_current_user)):
    proposal = crud.get_or_404(db, ManagementProposal, proposal_id, "修改方案")
    require_management_record_access(proposal, user, db)
    return proposal


@router.post("/management/proposals/{proposal_id}/apply")
def apply_proposal(proposal_id: int, db: Session = Depends(get_session), user: User = Depends(get_current_user)):
    proposal = crud.get_or_404(db, ManagementProposal, proposal_id, "修改方案")
    require_management_record_access(proposal, user, db)
    return apply_management_proposal(proposal_id, db, user)


@router.post("/management/proposals/{proposal_id}/reject")
def reject_proposal(proposal_id: int, db: Session = Depends(get_session), user: User = Depends(get_current_user)):
    proposal = crud.get_or_404(db, ManagementProposal, proposal_id, "修改方案")
    require_management_record_access(proposal, user, db)
    return reject_management_proposal(proposal_id, db)
