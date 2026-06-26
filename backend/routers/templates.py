from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlmodel import Session

import crud
from database import get_session
from models import WorldTemplate
from schemas import TemplateCreate, TemplateUpdate

router = APIRouter()


@router.get("/templates")
def list_templates(db: Session = Depends(get_session)):
    return crud.list_records(db, WorldTemplate)


@router.post("/templates")
def create_template(payload: TemplateCreate, db: Session = Depends(get_session)):
    return crud.create_record(db, WorldTemplate, payload)


@router.patch("/templates/{template_id}")
def update_template(template_id: int, payload: TemplateUpdate, db: Session = Depends(get_session)):
    template = crud.get_or_404(db, WorldTemplate, template_id, "模板")
    return crud.update_record(db, template, payload)


@router.delete("/templates/{template_id}")
def delete_template(template_id: int, db: Session = Depends(get_session)):
    template = crud.get_or_404(db, WorldTemplate, template_id, "模板")
    return crud.delete_record(db, template)
