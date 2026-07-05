from __future__ import annotations

import re
from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import or_
from sqlmodel import Session, select

import crud
from agents.management_agent import run_management_agent
from game_engine import load_game_context
from json_utils import dump_json_field, parse_json_field
from models import (
    Character,
    Game,
    ManagementProposal,
    ManagementSession,
    StoryWorld,
    WorldLore,
    WorldTemplate,
    User,
)

ACTION_WHITELIST = {
    "update_game",
    "create_story_world",
    "update_story_world",
    "delete_story_world",
    "create_lore",
    "update_lore",
    "delete_lore",
    "create_character",
    "update_character",
    "delete_character",
    "create_template",
    "update_template",
    "delete_template",
}

MODEL_BY_ACTION = {
    "story_world": StoryWorld,
    "lore": WorldLore,
    "character": Character,
    "template": WorldTemplate,
}

ACTION_CONTROL_FIELDS = {"id", "target_id", "target_name"}

ALLOWED_FIELDS = {
    Game: {"title", "genre", "world_type", "tone", "narrative_perspective", "style_guide", "rules_summary", "current_state", "current_story_world_id"},
    StoryWorld: {"name", "world_type", "summary", "current_status", "mission_objective", "completion_condition", "failure_condition", "plot_deviation"},
    WorldLore: {"title", "category", "content", "canon_level", "importance"},
    Character: {
        "name",
        "role_type",
        "avatar_url",
        "gender",
        "age",
        "race_or_identity",
        "appearance",
        "personality",
        "speech_style",
        "abilities",
        "current_location",
        "status",
        "mood",
        "relationship_to_player",
        "relationship_score",
        "affection_score",
        "trust_score",
        "tension_score",
        "current_goal",
        "hidden_goal",
        "memory_summary",
        "agent_enabled",
        "extra_attrs",
    },
    WorldTemplate: {"name", "genre", "world_type", "tone", "description", "default_style_guide", "default_rules", "default_character_fields"},
}


def _load_global_template_context(db: Session, user: User | None = None) -> dict:
    query = select(WorldTemplate)
    if user and not user.is_admin:
        query = query.where(or_(WorldTemplate.owner_user_id == None, WorldTemplate.owner_user_id == user.id))  # noqa: E711
    templates = db.exec(query).all()
    return {
        "game": None,
        "scope": "模板",
        "templates": [template.model_dump() if hasattr(template, "model_dump") else template.dict() for template in templates],
        "note": "这是全局模板管理上下文，不属于任何单个存档。",
    }


def create_management_session(game_id: int, session: Session, title: str = "管理对话", owner_user_id: int | None = None) -> ManagementSession:
    if game_id != 0 and not session.get(Game, game_id):
        raise HTTPException(status_code=404, detail=f"找不到游戏: {game_id}")
    record = ManagementSession(game_id=game_id, title=title, owner_user_id=owner_user_id)
    session.add(record)
    session.commit()
    session.refresh(record)
    return record


def _normalize_management_actions(value) -> list[dict]:
    parsed = parse_json_field(value, default=value) if isinstance(value, str) else value
    if isinstance(parsed, dict):
        parsed = parsed.get("proposed_actions") or parsed.get("actions") or [parsed]
    if not isinstance(parsed, list):
        return []

    actions: list[dict] = []
    for item in parsed:
        if isinstance(item, str):
            item = parse_json_field(item, default={})
        if isinstance(item, dict):
            actions.append(item)
    return actions


def _normalize_template_action(action: dict) -> dict:
    fields = action.get("fields")
    if isinstance(fields, dict):
        fields = dict(fields)
        for key in ACTION_CONTROL_FIELDS:
            if key in fields and key not in action:
                action[key] = fields[key]
            fields.pop(key, None)
        action["fields"] = fields
    fields = action.get("fields")
    target = fields if isinstance(fields, dict) else action
    if isinstance(target, dict) and isinstance(target.get("default_character_fields"), (dict, list)):
        target["default_character_fields"] = dump_json_field(target["default_character_fields"])
    return action


def _normalize_action(action: dict) -> dict:
    params = action.get("params")
    if isinstance(params, dict):
        action = {key: value for key, value in action.items() if key != "params"}
        for key, value in params.items():
            if key not in action or key in {"fields", "target_id", "target_name", "id", "name"}:
                action[key] = value
    name = action.get("action", "")
    if name.endswith("_template"):
        return _normalize_template_action(action)
    return action


def _extract_current_template_id(text: str) -> int | None:
    if not text:
        return None
    match = re.search(r'"current_template_id"\s*:\s*(\d+)', text)
    if not match:
        return None
    return int(match.group(1))


def _with_context_target(action: dict, current_template_id: int | None) -> dict:
    if (
        current_template_id
        and action.get("action") in {"update_template", "delete_template"}
        and not (action.get("target_id") or action.get("id") or action.get("target_name"))
    ):
        return {**action, "target_id": current_template_id}
    return action


def create_management_proposal(
    game_id: int,
    session_id: int,
    owner_user_id: int | None,
    user_request: str,
    agent_response: str,
    proposed_actions,
    db: Session,
) -> ManagementProposal:
    current_template_id = _extract_current_template_id(user_request)
    actions = [
        _with_context_target(_normalize_action(action), current_template_id)
        for action in _normalize_management_actions(proposed_actions)
    ]
    proposal = ManagementProposal(
        game_id=game_id,
        session_id=session_id,
        owner_user_id=owner_user_id,
        user_request=user_request,
        agent_response=agent_response,
        proposed_actions=dump_json_field(actions),
        status="pending_confirmation" if actions else "draft",
    )
    db.add(proposal)
    db.commit()
    db.refresh(proposal)
    return proposal


def run_management_chat(session_id: int, message: str, db: Session, scope: str = "", user: User | None = None) -> dict:
    session_record = db.get(ManagementSession, session_id)
    if not session_record:
        raise HTTPException(status_code=404, detail=f"找不到管理会话: {session_id}")
    context = _load_global_template_context(db, user) if session_record.game_id == 0 else load_game_context(session_record.game_id, db)
    result = run_management_agent(context, message, scope)
    current_template_id = _extract_current_template_id(message)
    actions = [
        _with_context_target(_normalize_action(action), current_template_id)
        for action in _normalize_management_actions(result.get("proposed_actions", []))
    ]
    proposal = create_management_proposal(
        session_record.game_id,
        session_id,
        session_record.owner_user_id if session_record.game_id == 0 else None,
        message,
        result.get("reply", ""),
        actions,
        db,
    )
    return {
        "reply": result.get("reply", ""),
        "proposal_id": proposal.id,
        "proposed_actions": actions,
        "requires_confirmation": bool(actions),
    }


def _find_by_name_or_id(db: Session, model, game_id: int, action: dict, user: User | None = None):
    target_id = action.get("target_id") or action.get("id")
    if target_id:
        return db.get(model, target_id)
    target_name = action.get("target_name") or action.get("name")
    fields = action.get("fields") or {}
    target_name = target_name or fields.get("name") or fields.get("title")
    if model is WorldTemplate:
        if target_id:
            return db.get(model, target_id)
        if target_name:
            if user and not user.is_admin:
                own = db.exec(select(model).where(model.name == target_name, model.owner_user_id == user.id)).first()
                if own:
                    return own
            return db.exec(select(model).where(model.name == target_name)).first()
        return None
    if target_name and hasattr(model, "name"):
        return db.exec(select(model).where(model.game_id == game_id, model.name == target_name)).first()
    if target_name and hasattr(model, "title"):
        return db.exec(select(model).where(model.game_id == game_id, model.title == target_name)).first()
    return None


def _clean_fields(model, fields: dict) -> dict:
    allowed = ALLOWED_FIELDS[model]
    fields = {key: value for key, value in fields.items() if key not in ACTION_CONTROL_FIELDS}
    illegal = [key for key in fields if key not in allowed]
    if illegal:
        raise HTTPException(status_code=400, detail=f"字段不允许修改: {', '.join(illegal)}")
    return {key: value for key, value in fields.items() if key in allowed}


def _action_fields(model, action: dict) -> dict:
    fields = action.get("fields")
    if isinstance(fields, dict):
        return _clean_fields(model, fields)
    params = action.get("params")
    if isinstance(params, dict):
        nested_fields = params.get("fields")
        if isinstance(nested_fields, dict):
            return _clean_fields(model, nested_fields)
        return _clean_fields(model, {key: value for key, value in params.items() if key in ALLOWED_FIELDS[model]})
    return _clean_fields(model, {key: value for key, value in action.items() if key in ALLOWED_FIELDS[model]})


def validate_management_action(action: dict, db: Session) -> tuple[bool, str | None]:
    action_name = action.get("action")
    if action_name not in ACTION_WHITELIST:
        return False, f"非法 action: {action_name}"
    if "sql" in action or action_name == "sql":
        return False, "禁止执行任意 SQL。"
    return True, None


def _ensure_template_write_access(template: WorldTemplate, user: User | None) -> None:
    if user and user.is_admin:
        return
    if user and template.owner_user_id == user.id:
        return
    if template.owner_user_id is None:
        raise HTTPException(status_code=403, detail="公共模板只能由管理员修改。")
    raise HTTPException(status_code=403, detail="无权修改其他用户的模板。")


def _apply_create(db: Session, model, game_id: int, action: dict, user: User | None = None):
    fields = _action_fields(model, action)
    fields.pop("id", None)
    if model is WorldTemplate:
        is_public = bool(fields.pop("is_public", False)) if user and user.is_admin else False
        return crud.create_record(db, model, fields, extra={"owner_user_id": None if is_public else getattr(user, "id", None)})
    return crud.create_record(db, model, fields, extra={"game_id": game_id})


def _apply_update(db: Session, model, game_id: int, action: dict, user: User | None = None):
    target = _find_by_name_or_id(db, model, game_id, action, user)
    if not target:
        raise HTTPException(status_code=404, detail="找不到要修改的目标。")
    if model is WorldTemplate:
        _ensure_template_write_access(target, user)
    fields = _action_fields(model, action)
    if model is WorldTemplate:
        is_public = fields.pop("is_public", None)
        if user and user.is_admin and is_public is not None:
            target.owner_user_id = None if is_public else user.id
    return crud.update_record(db, target, fields)


def _apply_delete(db: Session, model, game_id: int, action: dict, user: User | None = None):
    target = _find_by_name_or_id(db, model, game_id, action, user)
    if not target:
        raise HTTPException(status_code=404, detail="找不到要删除的目标。")
    if model is WorldTemplate:
        _ensure_template_write_access(target, user)
    return crud.delete_record(db, target)


def apply_management_proposal(proposal_id: int, db: Session, user: User | None = None) -> dict:
    proposal = db.get(ManagementProposal, proposal_id)
    if not proposal:
        raise HTTPException(status_code=404, detail=f"找不到修改方案: {proposal_id}")
    current_template_id = _extract_current_template_id(proposal.user_request)
    actions = [
        _with_context_target(_normalize_action(action), current_template_id)
        for action in _normalize_management_actions(proposal.proposed_actions)
    ]
    if proposal.status != "pending_confirmation":
        if proposal.status in {"draft", "failed"} and actions:
            proposal.status = "pending_confirmation"
            proposal.proposed_actions = dump_json_field(actions)
            proposal.updated_at = datetime.utcnow()
            db.add(proposal)
            db.commit()
        else:
            raise HTTPException(status_code=400, detail="ManagementProposal 未处于待确认状态，不能执行。")
    results = []
    try:
        for action in actions:
            ok, reason = validate_management_action(action, db)
            if not ok:
                raise HTTPException(status_code=400, detail=reason)
            name = action["action"]
            if proposal.game_id == 0 and not name.endswith("_template"):
                raise HTTPException(status_code=400, detail="全局模板会话只能修改模板。")
            if name == "update_game":
                game = db.get(Game, proposal.game_id)
                if not game:
                    raise HTTPException(status_code=404, detail="找不到游戏。")
                results.append(crud.update_record(db, game, _clean_fields(Game, action.get("fields", {}))))
            elif name.startswith("create_"):
                key = name.removeprefix("create_")
                model = MODEL_BY_ACTION.get(key)
                if not model:
                    raise HTTPException(status_code=400, detail=f"暂不支持创建 action: {name}")
                results.append(_apply_create(db, model, proposal.game_id, action, user))
            elif name.startswith("update_"):
                key = name.removeprefix("update_")
                model = MODEL_BY_ACTION.get(key)
                if not model:
                    raise HTTPException(status_code=400, detail=f"暂不支持更新 action: {name}")
                results.append(_apply_update(db, model, proposal.game_id, action, user))
            elif name.startswith("delete_"):
                key = name.removeprefix("delete_")
                model = MODEL_BY_ACTION.get(key)
                if not model:
                    raise HTTPException(status_code=400, detail=f"暂不支持删除 action: {name}")
                results.append(_apply_delete(db, model, proposal.game_id, action, user))
        proposal.status = "applied"
        proposal.applied_at = datetime.utcnow()
        proposal.updated_at = datetime.utcnow()
        db.add(proposal)
        db.commit()
        return {"ok": True, "status": proposal.status, "results": [str(getattr(item, "id", item)) for item in results]}
    except HTTPException:
        proposal.status = "failed"
        proposal.updated_at = datetime.utcnow()
        db.add(proposal)
        db.commit()
        raise


def reject_management_proposal(proposal_id: int, db: Session) -> dict:
    proposal = db.get(ManagementProposal, proposal_id)
    if not proposal:
        raise HTTPException(status_code=404, detail=f"找不到修改方案: {proposal_id}")
    proposal.status = "rejected"
    proposal.updated_at = datetime.utcnow()
    db.add(proposal)
    db.commit()
    return {"ok": True, "status": proposal.status}
