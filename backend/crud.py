from __future__ import annotations

from typing import Any, Type

from fastapi import HTTPException
from sqlmodel import Session, SQLModel, select
from time_utils import utc_now


def to_data(payload: Any, exclude_unset: bool = False) -> dict[str, Any]:
    if payload is None:
        return {}
    if isinstance(payload, dict):
        return {k: v for k, v in payload.items() if not exclude_unset or v is not None}
    if hasattr(payload, "model_dump"):
        return payload.model_dump(exclude_unset=exclude_unset)
    if hasattr(payload, "dict"):
        return payload.dict(exclude_unset=exclude_unset)
    raise TypeError(f"Unsupported payload type: {type(payload)!r}")


def get_by_id(session: Session, model: Type[SQLModel], record_id: int) -> SQLModel | None:
    return session.get(model, record_id)


def get_or_404(session: Session, model: Type[SQLModel], record_id: int, label: str = "record") -> SQLModel:
    record = get_by_id(session, model, record_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"找不到{label}: {record_id}")
    return record


def list_records(session: Session, model: Type[SQLModel]) -> list[SQLModel]:
    return list(session.exec(select(model)).all())


def list_by_game(session: Session, model: Type[SQLModel], game_id: int) -> list[SQLModel]:
    return list(session.exec(select(model).where(model.game_id == game_id)).all())


def create_record(
    session: Session,
    model: Type[SQLModel],
    payload: Any,
    extra: dict[str, Any] | None = None,
    *,
    commit: bool = True,
) -> SQLModel:
    data = to_data(payload)
    if extra:
        data.update(extra)
    record = model(**data)
    session.add(record)
    if commit:
        session.commit()
        session.refresh(record)
    else:
        session.flush()
    return record


def update_record(session: Session, record: SQLModel, payload: Any, *, commit: bool = True) -> SQLModel:
    data = to_data(payload, exclude_unset=True)
    for key, value in data.items():
        if hasattr(record, key):
            setattr(record, key, value)
    if hasattr(record, "updated_at"):
        setattr(record, "updated_at", utc_now())
    session.add(record)
    if commit:
        session.commit()
        session.refresh(record)
    else:
        session.flush()
    return record


def delete_record(session: Session, record: SQLModel, *, commit: bool = True) -> dict[str, bool]:
    session.delete(record)
    if commit:
        session.commit()
    else:
        session.flush()
    return {"ok": True}
