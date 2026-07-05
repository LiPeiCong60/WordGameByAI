from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_
from sqlmodel import Session, select

import crud
from auth_service import get_current_user
from database import get_session
from models import User, WorldTemplate
from schemas import TemplateCreate, TemplateUpdate

router = APIRouter()


@router.get("/templates")
def list_templates(db: Session = Depends(get_session), user: User = Depends(get_current_user)):
    query = select(WorldTemplate)
    if not user.is_admin:
        query = query.where(or_(WorldTemplate.owner_user_id == None, WorldTemplate.owner_user_id == user.id))  # noqa: E711
    return list(db.exec(query).all())


@router.post("/templates")
def create_template(payload: TemplateCreate, db: Session = Depends(get_session), user: User = Depends(get_current_user)):
    data = payload.model_dump()
    is_public = bool(data.pop("is_public", False)) if user.is_admin else False
    return crud.create_record(db, WorldTemplate, data, extra={"owner_user_id": None if is_public else user.id})


def require_template_write_access(template: WorldTemplate, user: User) -> None:
    if user.is_admin:
        return
    if template.owner_user_id == user.id:
        return
    if template.owner_user_id is None:
        raise HTTPException(status_code=403, detail="内置公共模板只能由管理员修改。")
    raise HTTPException(status_code=403, detail="无权修改其他用户的模板。")


@router.patch("/templates/{template_id}")
def update_template(template_id: int, payload: TemplateUpdate, db: Session = Depends(get_session), user: User = Depends(get_current_user)):
    template = crud.get_or_404(db, WorldTemplate, template_id, "模板")
    require_template_write_access(template, user)
    data = payload.model_dump(exclude_unset=True)
    is_public = data.pop("is_public", None)
    if user.is_admin and is_public is not None:
        template.owner_user_id = None if is_public else user.id
    return crud.update_record(db, template, data)


@router.delete("/templates/{template_id}")
def delete_template(template_id: int, db: Session = Depends(get_session), user: User = Depends(get_current_user)):
    template = crud.get_or_404(db, WorldTemplate, template_id, "模板")
    require_template_write_access(template, user)
    return crud.delete_record(db, template)
