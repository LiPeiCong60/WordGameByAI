from __future__ import annotations

from datetime import datetime

from fastapi import HTTPException
from sqlmodel import Session, select

import crud
from agents.management_agent import run_management_agent
from game_engine import load_game_context
from inventory_service import equip_item, transfer_item, unequip_item, use_item
from json_utils import dump_json_field, parse_json_field
from models import (
    Character,
    Game,
    InventoryRecord,
    Item,
    ManagementProposal,
    ManagementSession,
    StoryWorld,
    WorldEvent,
    WorldLore,
    WorldTemplate,
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
    "create_item",
    "update_item",
    "delete_item",
    "create_inventory_record",
    "update_inventory_record",
    "delete_inventory_record",
    "transfer_item",
    "use_item",
    "equip_item",
    "unequip_item",
    "create_event",
    "update_event",
    "delete_event",
    "create_template",
    "update_template",
    "delete_template",
}

MODEL_BY_ACTION = {
    "story_world": StoryWorld,
    "lore": WorldLore,
    "character": Character,
    "item": Item,
    "inventory_record": InventoryRecord,
    "event": WorldEvent,
    "template": WorldTemplate,
}

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
        "current_goal",
        "hidden_goal",
        "memory_summary",
        "agent_enabled",
        "extra_attrs",
    },
    Item: {
        "name",
        "item_type",
        "description",
        "status",
        "rarity",
        "quantity_limit",
        "is_stackable",
        "is_equippable",
        "is_consumable",
        "is_key_item",
        "is_tradeable",
        "is_unique",
        "usable_condition",
        "effect_description",
        "current_location",
        "importance",
        "extra_attrs",
    },
    InventoryRecord: {"item_id", "owner_type", "owner_id", "owner_name", "quantity", "equipped", "storage_location", "item_state", "note"},
    WorldEvent: {"title", "event_type", "arc_name", "related_world", "summary", "location", "participants", "consequence", "status", "importance", "extra_attrs"},
    WorldTemplate: {"name", "genre", "world_type", "tone", "description", "default_style_guide", "default_rules", "default_character_fields"},
}


def _load_global_template_context(db: Session) -> dict:
    templates = db.exec(select(WorldTemplate)).all()
    return {
        "game": None,
        "scope": "模板",
        "templates": [template.model_dump() if hasattr(template, "model_dump") else template.dict() for template in templates],
        "note": "这是全局模板管理上下文，不属于任何单个存档。",
    }


def create_management_session(game_id: int, session: Session, title: str = "管理对话") -> ManagementSession:
    if game_id != 0 and not session.get(Game, game_id):
        raise HTTPException(status_code=404, detail=f"找不到游戏: {game_id}")
    record = ManagementSession(game_id=game_id, title=title)
    session.add(record)
    session.commit()
    session.refresh(record)
    return record


def create_management_proposal(
    game_id: int, session_id: int, user_request: str, agent_response: str, proposed_actions: list, db: Session
) -> ManagementProposal:
    proposal = ManagementProposal(
        game_id=game_id,
        session_id=session_id,
        user_request=user_request,
        agent_response=agent_response,
        proposed_actions=dump_json_field(proposed_actions),
        status="pending_confirmation" if proposed_actions else "draft",
    )
    db.add(proposal)
    db.commit()
    db.refresh(proposal)
    return proposal


def run_management_chat(session_id: int, message: str, db: Session, scope: str = "") -> dict:
    session_record = db.get(ManagementSession, session_id)
    if not session_record:
        raise HTTPException(status_code=404, detail=f"找不到管理会话: {session_id}")
    context = _load_global_template_context(db) if session_record.game_id == 0 else load_game_context(session_record.game_id, db)
    result = run_management_agent(context, message, scope)
    proposal = create_management_proposal(
        session_record.game_id,
        session_id,
        message,
        result.get("reply", ""),
        result.get("proposed_actions", []),
        db,
    )
    return {
        "reply": result.get("reply", ""),
        "proposal_id": proposal.id,
        "proposed_actions": result.get("proposed_actions", []),
        "requires_confirmation": bool(result.get("proposed_actions")),
    }


def _find_by_name_or_id(db: Session, model, game_id: int, action: dict):
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
            return db.exec(select(model).where(model.name == target_name)).first()
        return None
    if target_name and hasattr(model, "name"):
        return db.exec(select(model).where(model.game_id == game_id, model.name == target_name)).first()
    if target_name and hasattr(model, "title"):
        return db.exec(select(model).where(model.game_id == game_id, model.title == target_name)).first()
    return None


def _clean_fields(model, fields: dict) -> dict:
    allowed = ALLOWED_FIELDS[model]
    illegal = [key for key in fields if key not in allowed]
    if illegal:
        raise HTTPException(status_code=400, detail=f"字段不允许修改: {', '.join(illegal)}")
    return {key: value for key, value in fields.items() if key in allowed}


def validate_management_action(action: dict, db: Session) -> tuple[bool, str | None]:
    action_name = action.get("action")
    if action_name not in ACTION_WHITELIST:
        return False, f"非法 action: {action_name}"
    if "sql" in action or action_name == "sql":
        return False, "禁止执行任意 SQL。"
    return True, None


def _apply_create(db: Session, model, game_id: int, action: dict):
    fields = _clean_fields(model, action.get("fields", action))
    fields.pop("id", None)
    if model is WorldTemplate:
        return crud.create_record(db, model, fields)
    return crud.create_record(db, model, fields, extra={"game_id": game_id})


def _apply_update(db: Session, model, game_id: int, action: dict):
    target = _find_by_name_or_id(db, model, game_id, action)
    if not target:
        raise HTTPException(status_code=404, detail="找不到要修改的目标。")
    fields = _clean_fields(model, action.get("fields", {}))
    return crud.update_record(db, target, fields)


def _apply_delete(db: Session, model, game_id: int, action: dict):
    target = _find_by_name_or_id(db, model, game_id, action)
    if not target:
        raise HTTPException(status_code=404, detail="找不到要删除的目标。")
    return crud.delete_record(db, target)


def apply_management_proposal(proposal_id: int, db: Session) -> dict:
    proposal = db.get(ManagementProposal, proposal_id)
    if not proposal:
        raise HTTPException(status_code=404, detail=f"找不到修改方案: {proposal_id}")
    if proposal.status != "pending_confirmation":
        raise HTTPException(status_code=400, detail="ManagementProposal 未处于待确认状态，不能执行。")

    actions = parse_json_field(proposal.proposed_actions, default=[])
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
                results.append(_apply_create(db, model, proposal.game_id, action))
            elif name.startswith("update_"):
                key = name.removeprefix("update_")
                model = MODEL_BY_ACTION.get(key)
                if not model:
                    raise HTTPException(status_code=400, detail=f"暂不支持更新 action: {name}")
                results.append(_apply_update(db, model, proposal.game_id, action))
            elif name.startswith("delete_"):
                key = name.removeprefix("delete_")
                model = MODEL_BY_ACTION.get(key)
                if not model:
                    raise HTTPException(status_code=400, detail=f"暂不支持删除 action: {name}")
                results.append(_apply_delete(db, model, proposal.game_id, action))
            elif name == "transfer_item":
                results.append(transfer_item(db, proposal.game_id, **{k: v for k, v in action.items() if k != "action"}))
            elif name == "use_item":
                results.append(use_item(db, proposal.game_id, action["character_id"], action["item_id"], action.get("quantity", 1), action.get("context")))
            elif name == "equip_item":
                results.append(equip_item(db, proposal.game_id, action["character_id"], action["item_id"]))
            elif name == "unequip_item":
                results.append(unequip_item(db, proposal.game_id, action["character_id"], action["item_id"]))
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
