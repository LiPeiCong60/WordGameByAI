from __future__ import annotations

from sqlmodel import Session, select

from json_utils import dump_json_field, merge_json_field, parse_json_field
from models import Character, Game, StoryWorld
from numeric_utils import as_int
from time_utils import utc_now


def _touch(record) -> None:
    if hasattr(record, "updated_at"):
        record.updated_at = utc_now()


AMBIENT_NAME_MARKERS = ("一群", "路人", "群众", "人群", "军人们", "士兵们", "猎户们", "守卫们", "店员们", "围观者")
STATE_LABELS = {
    "time": "当前时间",
    "date": "日期",
    "weather": "天气",
    "location": "当前位置",
    "place": "当前位置",
    "status": "当前状况",
    "extra": "当前状况",
    "scene": "场景",
    "phase": "阶段",
}


def _truthy(value, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        return value.lower() in {"1", "true", "yes", "是", "启用", "重要"}
    return bool(value)


def _as_int(value, default: int = 0) -> int:
    return as_int(value, default)


def format_state_text(value) -> str:
    if value in (None, ""):
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict):
        parts = []
        for key, item in value.items():
            text = format_state_text(item)
            if text:
                parts.append(f"{STATE_LABELS.get(str(key), str(key))}:{text}")
        return "；".join(parts)
    if isinstance(value, list):
        return "；".join(text for item in value if (text := format_state_text(item)))
    return str(value).strip()


def _looks_ambient_name(name: str) -> bool:
    return any(marker in name for marker in AMBIENT_NAME_MARKERS)


def _find_character(db: Session, game_id: int, name: str | None = None, character_id: int | None = None) -> Character | None:
    if character_id:
        character = db.get(Character, _as_int(character_id))
        return character if character and character.game_id == game_id else None
    if not name:
        return None
    return db.exec(select(Character).where(Character.game_id == game_id, Character.name == name)).first()


def apply_state_patch(game_id: int, state_patch: dict, db: Session, *, commit: bool = True) -> dict:
    warnings: list[str] = []
    game = db.get(Game, game_id)
    if not game:
        return {"ok": False, "warnings": [f"找不到游戏: {game_id}"]}

    current_state_update = format_state_text(state_patch.get("current_state_update"))
    if current_state_update:
        game.current_state = current_state_update
        _touch(game)
        db.add(game)

    for character_patch in state_patch.get("new_characters") or []:
        if not isinstance(character_patch, dict):
            continue
        name = (character_patch.get("name") or "").strip()
        if not name:
            continue
        if _looks_ambient_name(name):
            warnings.append(f"疑似背景群体，未创建为可管理 NPC: {name}")
            continue
        if db.exec(select(Character).where(Character.game_id == game_id, Character.name == name)).first():
            continue
        importance = _as_int(character_patch.get("importance"), 7)
        extra_attrs = parse_json_field(character_patch.get("extra_attrs"), default={})
        if not isinstance(extra_attrs, dict):
            extra_attrs = {}
        extra_attrs.update(
            {
                "自动发现": True,
                "重要度": importance,
                "加入原因": character_patch.get("management_reason", ""),
            }
        )
        db.add(
            Character(
                game_id=game_id,
                name=name,
                role_type=character_patch.get("role_type", "npc"),
                gender=character_patch.get("gender", ""),
                age=character_patch.get("age", ""),
                race_or_identity=character_patch.get("race_or_identity", ""),
                appearance=character_patch.get("appearance", ""),
                personality=character_patch.get("personality", ""),
                speech_style=character_patch.get("speech_style", ""),
                abilities=character_patch.get("abilities", ""),
                current_location=character_patch.get("current_location", ""),
                status=character_patch.get("status", "normal"),
                mood=character_patch.get("mood", ""),
                relationship_to_player=character_patch.get("relationship_to_player", ""),
                relationship_score=_as_int(character_patch.get("relationship_score"), 0),
                affection_score=_as_int(character_patch.get("affection_score"), 0),
                trust_score=_as_int(character_patch.get("trust_score"), 0),
                tension_score=_as_int(character_patch.get("tension_score"), 0),
                current_goal=character_patch.get("current_goal", ""),
                hidden_goal=character_patch.get("hidden_goal", ""),
                memory_summary=character_patch.get("memory_summary", ""),
                agent_enabled=_truthy(character_patch.get("agent_enabled"), True),
                extra_attrs=dump_json_field(extra_attrs),
            )
        )

    for item in state_patch.get("updated_characters") or []:
        if not isinstance(item, dict):
            continue
        name = item.get("name")
        character = _find_character(db, game_id, name, item.get("id") or item.get("character_id"))
        if not character:
            warnings.append(f"找不到角色，未应用更新: {name or item.get('id') or item.get('character_id')}")
            continue
        for key in [
            "status",
            "mood",
            "relationship_to_player",
            "current_goal",
            "current_location",
            "memory_summary",
        ]:
            if key in item:
                setattr(character, key, format_state_text(item[key]))
        if "relationship_score" in item:
            character.relationship_score = _as_int(item.get("relationship_score"), character.relationship_score)
        if "affection_score" in item:
            character.affection_score = _as_int(item.get("affection_score"), character.affection_score)
        if "trust_score" in item:
            character.trust_score = _as_int(item.get("trust_score"), character.trust_score)
        if "tension_score" in item:
            character.tension_score = _as_int(item.get("tension_score"), character.tension_score)
        if "extra_attrs" in item:
            character.extra_attrs = merge_json_field(character.extra_attrs, item["extra_attrs"])
        _touch(character)
        db.add(character)

    story_world_patch = state_patch.get("updated_story_world") or {}
    if isinstance(story_world_patch, dict) and story_world_patch:
        world = None
        if story_world_patch.get("id"):
            candidate = db.get(StoryWorld, story_world_patch["id"])
            world = candidate if candidate and candidate.game_id == game_id else None
        elif story_world_patch.get("name"):
            world = db.exec(
                select(StoryWorld).where(StoryWorld.game_id == game_id, StoryWorld.name == story_world_patch["name"])
            ).first()
        if world:
            for key in [
                "name",
                "world_type",
                "summary",
                "current_status",
                "mission_objective",
                "completion_condition",
                "failure_condition",
            ]:
                if key in story_world_patch:
                    setattr(world, key, format_state_text(story_world_patch[key]))
            if "plot_deviation" in story_world_patch:
                world.plot_deviation = _as_int(story_world_patch.get("plot_deviation"), world.plot_deviation)
            _touch(world)
            db.add(world)
        else:
            warnings.append("找不到 StoryWorld，未应用 updated_story_world。")

    if commit:
        db.commit()
    else:
        db.flush()
    return {"ok": True, "warnings": warnings}
