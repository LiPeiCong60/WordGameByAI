from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import datetime

from sqlalchemy import or_
from sqlmodel import Session, desc, func, select

from agents.checker_agent import run_checker_agent
from agents.narrator_agent import run_narrator_agent, run_narrator_stream_agent
from agents.npc_reaction_agent import run_npc_reaction_agent
from agents.opening_agent import run_opening_agent, run_opening_stream_agent
from agents.patch_agent import EMPTY_PATCH, run_patch_agent
from agents.protagonist_agent import run_protagonist_agent, run_protagonist_fallback
from export_import import export_game
from json_utils import dump_json_field, safe_json_loads
from llm_client import current_llm_user_id, reset_current_llm_user, set_current_llm_user
from models import Character, Game, StoryWorld, TurnLog, TurnSnapshot, WorldLore, WorldTemplate
from numeric_utils import as_int
from patch_applier import apply_state_patch, format_state_text
from rag_service import attach_retrieved_memories, store_turn_memory

STATE_SYNC_EXECUTOR = ThreadPoolExecutor(max_workers=2, thread_name_prefix="state-sync")
STATE_HINT_START = "<STATE_HINT>"
STATE_HINT_END = "</STATE_HINT>"
STATE_HINT_OPEN_RE = re.compile(r"<\s*(?:dummy_)?state[_-]?hint\s*>", re.IGNORECASE)
STATE_HINT_CLOSE_RE = re.compile(r"<\s*/\s*(?:dummy_)?state[_-]?hint\s*>", re.IGNORECASE)
STATE_HINT_BLOCK_RE = re.compile(
    r"<\s*(?:dummy_)?state[_-]?hint\s*>(.*?)<\s*/\s*(?:dummy_)?state[_-]?hint\s*>",
    re.IGNORECASE | re.DOTALL,
)
STATE_HINT_TAG_RE = re.compile(r"</?\s*(?:dummy_)?state[_-]?hint\s*>", re.IGNORECASE)
STREAM_TAG_KEEP_CHARS = 32


def _model_dump(record) -> dict:
    return record.model_dump() if hasattr(record, "model_dump") else record.dict()


def load_game_context(game_id: int, session: Session) -> dict:
    game = session.get(Game, game_id)
    if not game:
        raise ValueError(f"找不到游戏: {game_id}")
    current_story_world = session.get(StoryWorld, game.current_story_world_id) if game.current_story_world_id else None
    if current_story_world and current_story_world.game_id != game_id:
        current_story_world = None
    lore = session.exec(
        select(WorldLore).where(WorldLore.game_id == game_id).order_by(desc(WorldLore.importance))
    ).all()
    characters = session.exec(select(Character).where(Character.game_id == game_id)).all()
    recent_turns = session.exec(
        select(TurnLog).where(TurnLog.game_id == game_id).order_by(desc(TurnLog.id)).limit(5)
    ).all()
    template_query = select(WorldTemplate)
    if game.owner_user_id is not None:
        template_query = template_query.where(or_(WorldTemplate.owner_user_id == None, WorldTemplate.owner_user_id == game.owner_user_id))  # noqa: E711
    else:
        template_query = template_query.where(WorldTemplate.owner_user_id == None)  # noqa: E711
    templates = session.exec(template_query).all()
    protagonist = next((c for c in characters if c.role_type == "protagonist"), None)
    return {
        "game": _model_dump(game),
        "current_story_world": _model_dump(current_story_world) if current_story_world else None,
        "world_lore": [_model_dump(item) for item in lore],
        "characters": [_model_dump(item) for item in characters],
        "protagonist": _model_dump(protagonist) if protagonist else None,
        "npcs": [_model_dump(c) for c in characters if c.role_type != "protagonist"],
        "recent_turns": [_model_dump(item) for item in recent_turns],
        "templates": [_model_dump(item) for item in templates],
    }


def save_turn_and_snapshot(
    game_id: int,
    turn_number: int,
    user_input: str,
    visible_story: str,
    npc_reactions: dict,
    state_patch: dict,
    checker_result: dict,
    snapshot_before_turn: dict,
    session: Session,
) -> TurnLog:
    turn = TurnLog(
        game_id=game_id,
        turn_number=turn_number,
        user_input=user_input,
        ai_response=visible_story,
        npc_reactions=dump_json_field(npc_reactions),
        state_patch=dump_json_field(state_patch),
        checker_result=dump_json_field(checker_result),
    )
    session.add(turn)
    session.commit()
    session.refresh(turn)
    snapshot = TurnSnapshot(
        game_id=game_id,
        turn_id=turn.id,
        turn_number=turn.turn_number,
        snapshot_json=dump_json_field(snapshot_before_turn),
    )
    session.add(snapshot)
    session.commit()
    return turn


def _protagonist_visible_story(protagonist_turn: dict) -> str:
    return str(protagonist_turn.get("visible_story") or "").strip()


def _compose_visible_story(protagonist_turn: dict, narrator_story: str) -> str:
    protagonist_story = _protagonist_visible_story(protagonist_turn)
    narrator_story = (narrator_story or "").strip()
    if protagonist_story and narrator_story:
        if narrator_story.startswith(protagonist_story):
            return narrator_story
        return f"{protagonist_story}\n\n{narrator_story}"
    return protagonist_story or narrator_story


def _has_turn_logs(game_id: int, session: Session) -> bool:
    return session.exec(select(TurnLog).where(TurnLog.game_id == game_id).limit(1)).first() is not None


def _empty_state_patch() -> dict:
    return deepcopy(EMPTY_PATCH)


def _core_state_patch(patch: dict) -> dict:
    cleaned = {**_empty_state_patch(), **(patch or {})}
    return cleaned


def _clamp(value: int, minimum: int, maximum: int) -> int:
    return max(minimum, min(maximum, value))


def _bounded_delta(value) -> int:
    return _clamp(as_int(value, 0), -30, 30)


def _bounded_target(current: int, target, minimum: int, maximum: int) -> int:
    raw_target = _clamp(as_int(target, current), minimum, maximum)
    return _clamp(current + _clamp(raw_target - current, -30, 30), minimum, maximum)


def _normalize_state_hint(raw_hint) -> dict:
    if not isinstance(raw_hint, dict):
        return _empty_state_patch()
    characters = (
        raw_hint.get("updated_characters")
        or raw_hint.get("character_hints")
        or raw_hint.get("characters")
        or []
    )
    if not isinstance(characters, list):
        characters = []
    return {
        **_empty_state_patch(),
        "current_state_update": format_state_text(raw_hint.get("current_state_update")),
        "updated_characters": [item for item in characters if isinstance(item, dict)],
        "state_hint": True,
    }


def _apply_state_hint(game_id: int, raw_hint, session: Session) -> dict:
    hint = _normalize_state_hint(raw_hint)
    applied = _empty_state_patch()
    applied["state_hint"] = True
    applied_characters = []

    game = session.get(Game, game_id)
    if game and hint.get("current_state_update"):
        game.current_state = format_state_text(hint["current_state_update"])
        session.add(game)
        applied["current_state_update"] = game.current_state

    for item in hint.get("updated_characters") or []:
        character = None
        if item.get("id") or item.get("character_id"):
            character_id = as_int(item.get("id") or item.get("character_id"), 0)
            character = session.get(Character, character_id) if character_id else None
            if character and character.game_id != game_id:
                character = None
        if not character and item.get("name"):
            character = session.exec(
                select(Character).where(Character.game_id == game_id, Character.name == item["name"])
            ).first()
        if not character:
            continue

        applied_item = {"id": character.id, "name": character.name}
        for key in ["status", "mood", "relationship_to_player", "current_goal", "current_location", "memory_summary"]:
            value = item.get(key)
            if value not in (None, ""):
                text_value = format_state_text(value)
                setattr(character, key, text_value)
                applied_item[key] = text_value

        numeric_ranges = {
            "relationship_score": (-100, 100),
            "affection_score": (0, 100),
            "trust_score": (0, 100),
            "tension_score": (0, 100),
        }
        for key, (minimum, maximum) in numeric_ranges.items():
            if f"{key}_delta" in item:
                new_value = _clamp(getattr(character, key) + _bounded_delta(item.get(f"{key}_delta")), minimum, maximum)
            elif key in item:
                new_value = _bounded_target(getattr(character, key), item.get(key), minimum, maximum)
            else:
                continue
            setattr(character, key, new_value)
            applied_item[key] = new_value

        session.add(character)
        applied_characters.append(applied_item)

    if applied_characters or applied.get("current_state_update"):
        session.commit()
    applied["updated_characters"] = applied_characters
    return applied


def _parse_state_hint_text(text: str) -> dict:
    data = safe_json_loads((text or "").strip(), default={})
    return data if isinstance(data, dict) else {}


def _strip_internal_story_tags(text: str) -> str:
    if not text:
        return ""
    without_blocks = STATE_HINT_BLOCK_RE.sub("", text)
    return STATE_HINT_TAG_RE.sub("", without_blocks).strip()


def _split_visible_story_and_hint(text: str) -> tuple[str, dict]:
    if not text:
        return "", {}

    hints: list[dict] = []

    def remove_hint_block(match: re.Match) -> str:
        hint = _parse_state_hint_text(match.group(1))
        if hint:
            hints.append(hint)
        return ""

    visible = STATE_HINT_BLOCK_RE.sub(remove_hint_block, text)
    open_match = STATE_HINT_OPEN_RE.search(visible)
    if open_match:
        hint = _parse_state_hint_text(visible[open_match.end():])
        if hint:
            hints.append(hint)
        visible = visible[:open_match.start()]

    return _strip_internal_story_tags(visible), (hints[0] if hints else {})


def _clean_visible_chunk(text: str) -> str:
    return _strip_internal_story_tags(text)


def _iter_visible_chunks_with_hint(raw_chunks, hint_box: dict):
    buffer = ""
    hint_parts: list[str] = []
    in_hint = False
    for raw in raw_chunks:
        buffer += raw
        while buffer:
            if not in_hint:
                marker = STATE_HINT_OPEN_RE.search(buffer)
                if marker:
                    visible = _clean_visible_chunk(buffer[: marker.start()])
                    if visible:
                        yield visible
                    buffer = buffer[marker.end():]
                    in_hint = True
                    continue
                keep = STREAM_TAG_KEEP_CHARS
                if len(buffer) <= keep:
                    break
                visible = _clean_visible_chunk(buffer[:-keep])
                buffer = buffer[-keep:]
                if visible:
                    yield visible
                break

            end_marker = STATE_HINT_CLOSE_RE.search(buffer)
            if end_marker:
                hint_parts.append(buffer[: end_marker.start()])
                buffer = buffer[end_marker.end():]
                in_hint = False
                continue
            keep = STREAM_TAG_KEEP_CHARS
            if len(buffer) <= keep:
                break
            hint_parts.append(buffer[:-keep])
            buffer = buffer[-keep:]
            break

    if in_hint:
        hint_parts.append(buffer)
    elif buffer:
        visible = _clean_visible_chunk(buffer)
        if visible:
            yield visible
    hint_box["state_hint"] = _parse_state_hint_text("".join(hint_parts))


def _pending_checker_result() -> dict:
    return {
        "ok": True,
        "issues": [],
        "pending": True,
        "async_state_update": True,
        "queued_at": datetime.utcnow().isoformat(),
        "message": "状态整理已转入后台执行。",
    }


def _skipped_checker_result(message: str = "极速模式跳过完整状态整理。") -> dict:
    return {
        "ok": True,
        "issues": [],
        "skipped": True,
        "message": message,
    }


def _resolve_state_update(
    game_id: int,
    context: dict,
    user_input: str,
    npc_reactions: dict,
    visible_story: str,
    session: Session,
    skip_state_update: bool = False,
) -> tuple[dict, dict, dict | None]:
    if skip_state_update:
        return (
            _empty_state_patch(),
            _skipped_checker_result(),
            {"ok": True, "skipped": True, "warnings": ["极速模式跳过完整状态整理。"]},
        )

    state_patch = _core_state_patch(run_patch_agent(context, user_input, npc_reactions, visible_story))
    checker_result = run_checker_agent(context, visible_story, state_patch)

    apply_result = None
    if checker_result.get("ok"):
        apply_result = apply_state_patch(game_id, state_patch, session)
    return state_patch, checker_result, apply_result


def _mark_turn_state_sync_failed(turn: TurnLog, message: str, session: Session) -> dict:
    checker_result = {
        "ok": False,
        "issues": [{"message": message}],
        "pending": False,
        "async_state_update": True,
    }
    turn.checker_result = dump_json_field(checker_result)
    session.add(turn)
    session.commit()
    return checker_result


def _finalize_async_state_update(
    game_id: int,
    turn_id: int,
    context: dict,
    user_input: str,
    npc_reactions: dict,
    visible_story: str,
    session: Session,
) -> dict | None:
    turn = session.get(TurnLog, turn_id)
    if not turn or turn.game_id != game_id:
        return None

    later_turn = session.exec(
        select(TurnLog)
        .where(TurnLog.game_id == game_id, TurnLog.turn_number > turn.turn_number)
        .limit(1)
    ).first()
    if later_turn:
        return _mark_turn_state_sync_failed(
            turn,
            "后台状态同步已跳过：这轮之后已经存在新的剧情，不能再把旧补丁套到当前状态上。",
            session,
        )

    try:
        state_patch, checker_result, apply_result = _resolve_state_update(
            game_id,
            context,
            user_input,
            npc_reactions,
            visible_story,
            session,
        )
    except Exception as exc:
        return _mark_turn_state_sync_failed(turn, f"后台状态同步失败：{exc}", session)

    checker_result = {**checker_result, "pending": False, "async_state_update": True}
    turn.state_patch = dump_json_field(state_patch)
    turn.checker_result = dump_json_field(checker_result)
    session.add(turn)
    session.commit()
    store_turn_memory(game_id, turn, visible_story, npc_reactions, state_patch, checker_result, session)
    return {"state_patch": state_patch, "checker_result": checker_result, "apply_result": apply_result}


def _run_async_state_update_job(
    game_id: int,
    turn_id: int,
    context: dict,
    user_input: str,
    npc_reactions: dict,
    visible_story: str,
    user_id: int | None = None,
) -> None:
    from database import engine

    token = set_current_llm_user(user_id)
    with Session(engine) as session:
        try:
            _finalize_async_state_update(game_id, turn_id, context, user_input, npc_reactions, visible_story, session)
        finally:
            reset_current_llm_user(token)


def _schedule_async_state_update(
    game_id: int,
    turn_id: int,
    context: dict,
    user_input: str,
    npc_reactions: dict,
    visible_story: str,
) -> None:
    user_id = current_llm_user_id()
    STATE_SYNC_EXECUTOR.submit(
        _run_async_state_update_job,
        game_id,
        turn_id,
        context,
        user_input,
        npc_reactions,
        visible_story,
        user_id,
    )


def _save_opening_turn(game_id: int, visible_story: str, snapshot_before_turn: dict, context: dict, session: Session) -> dict:
    state_patch = _core_state_patch(run_patch_agent(context, "系统开场白", {"reactions": []}, visible_story))
    checker_result = run_checker_agent(context, visible_story, state_patch)
    apply_result = None
    if checker_result.get("ok"):
        apply_result = apply_state_patch(game_id, state_patch, session)

    turn = save_turn_and_snapshot(
        game_id=game_id,
        turn_number=1,
        user_input="",
        visible_story=visible_story,
        npc_reactions={"reactions": [], "opening": True},
        state_patch=state_patch,
        checker_result=checker_result,
        snapshot_before_turn=snapshot_before_turn,
        session=session,
    )
    rag_memory = store_turn_memory(
        game_id,
        turn,
        visible_story,
        {"reactions": [], "opening": True},
        state_patch,
        checker_result,
        session,
    )
    return {
        "visible_story": visible_story,
        "npc_reactions": {"reactions": [], "opening": True},
        "state_patch": state_patch,
        "checker_result": checker_result,
        "apply_result": apply_result,
        "turn_id": turn.id,
        "rag_memory_id": rag_memory.id if rag_memory else None,
    }


def run_opening_turn(game_id: int, session: Session) -> dict:
    if _has_turn_logs(game_id, session):
        return {"ok": True, "skipped": True, "message": "当前存档已经有剧情记录，不重复生成开场白。"}
    base_context = load_game_context(game_id, session)
    query = " ".join(
        str(base_context.get("game", {}).get(key) or "")
        for key in ["title", "genre", "world_type", "tone", "rules_summary"]
    )
    context = attach_retrieved_memories(base_context, game_id, query or "开场", session)
    snapshot_before_turn = export_game(game_id, session)
    story = run_opening_agent(context)
    visible_story = str(story.get("visible_story") or "").strip() or "开场白生成失败：模型没有返回内容。"
    result = _save_opening_turn(game_id, visible_story, snapshot_before_turn, context, session)
    return {"ok": True, "skipped": False, **result}


def run_opening_turn_stream(game_id: int, session: Session):
    if _has_turn_logs(game_id, session):
        yield {"type": "done", "skipped": True, "visible_story": "", "message": "当前存档已经有剧情记录，不重复生成开场白。"}
        return

    base_context = load_game_context(game_id, session)
    query = " ".join(
        str(base_context.get("game", {}).get(key) or "")
        for key in ["title", "genre", "world_type", "tone", "rules_summary"]
    )
    context = attach_retrieved_memories(base_context, game_id, query or "开场", session)
    snapshot_before_turn = export_game(game_id, session)

    yield {"type": "status", "message": "正在检索相关世界观和角色记忆..."}
    yield {"type": "status", "message": "正在结合模板生成开场白..."}
    chunks: list[str] = []
    for chunk in run_opening_stream_agent(context):
        chunks.append(chunk)
        yield {"type": "delta", "text": chunk}

    visible_story = "".join(chunks).strip() or "开场白生成失败：模型没有返回内容。"

    yield {"type": "status", "message": "正在保存开场状态..."}
    result = _save_opening_turn(game_id, visible_story, snapshot_before_turn, context, session)

    yield {"type": "done", "skipped": False, **result}


def run_game_turn(
    game_id: int,
    user_input: str,
    session: Session,
    fast_mode: bool = False,
    skip_state_update: bool = False,
    async_state_update: bool = False,
) -> dict:
    context = attach_retrieved_memories(load_game_context(game_id, session), game_id, user_input, session)
    max_turn_number = session.exec(select(func.max(TurnLog.turn_number)).where(TurnLog.game_id == game_id)).one()
    turn_number = int(max_turn_number or 0) + 1
    snapshot_before_turn = export_game(game_id, session)
    protagonist_turn = run_protagonist_fallback(context, user_input) if fast_mode else run_protagonist_agent(context, user_input)
    npc_reactions = (
        {"reactions": [], "selected_npcs": [], "omitted_npcs": [], "selection_reason": "快速模式跳过 NPC 独立反应推演。"}
        if fast_mode
        else run_npc_reaction_agent(context, user_input, protagonist_turn)
    )
    npc_reactions = {**npc_reactions, "protagonist_turn": protagonist_turn}
    story = run_narrator_agent(context, user_input, protagonist_turn, npc_reactions)
    clean_story, parsed_hint = _split_visible_story_and_hint(story.get("visible_story", ""))
    visible_story = _compose_visible_story(protagonist_turn, clean_story)
    should_async_update = async_state_update and not skip_state_update
    should_hint_update = skip_state_update or should_async_update
    if should_hint_update:
        state_patch = _apply_state_hint(game_id, story.get("state_hint") or parsed_hint, session)
        checker_result = _pending_checker_result() if should_async_update else _skipped_checker_result("极速模式已应用 Hint 软状态，跳过完整状态整理。")
        checker_result["state_hint_applied"] = bool(state_patch.get("updated_characters") or state_patch.get("current_state_update"))
        apply_result = (
            {"ok": True, "pending": True, "message": "状态整理已转入后台执行。"}
            if should_async_update
            else {"ok": True, "skipped": True, "message": "已应用 Hint 软状态，完整状态整理已跳过。"}
        )
    else:
        state_patch, checker_result, apply_result = _resolve_state_update(
            game_id,
            context,
            user_input,
            npc_reactions,
            visible_story,
            session,
            skip_state_update=skip_state_update,
        )

    turn = save_turn_and_snapshot(
        game_id=game_id,
        turn_number=turn_number,
        user_input=user_input,
        visible_story=visible_story,
        npc_reactions=npc_reactions,
        state_patch=state_patch,
        checker_result=checker_result,
        snapshot_before_turn=snapshot_before_turn,
        session=session,
    )
    rag_memory = store_turn_memory(game_id, turn, visible_story, npc_reactions, state_patch, checker_result, session)
    if should_async_update:
        _schedule_async_state_update(game_id, turn.id, context, user_input, npc_reactions, visible_story)

    return {
        "visible_story": visible_story,
        "npc_reactions": npc_reactions,
        "state_patch": state_patch,
        "checker_result": checker_result,
        "apply_result": apply_result,
        "turn_id": turn.id,
        "retrieved_memories": context.get("retrieved_memories", []),
        "rag_memory_id": rag_memory.id if rag_memory else None,
        "fast_mode": fast_mode,
        "skip_state_update": skip_state_update,
        "async_state_update": should_async_update,
    }


def run_game_turn_stream(
    game_id: int,
    user_input: str,
    session: Session,
    fast_mode: bool = False,
    skip_state_update: bool = False,
    async_state_update: bool = False,
):
    yield {"type": "status", "message": "正在检索相关世界观和角色记忆..."}
    context = attach_retrieved_memories(load_game_context(game_id, session), game_id, user_input, session)
    max_turn_number = session.exec(select(func.max(TurnLog.turn_number)).where(TurnLog.game_id == game_id)).one()
    turn_number = int(max_turn_number or 0) + 1
    snapshot_before_turn = export_game(game_id, session)

    if fast_mode:
        yield {"type": "status", "message": "快速模式：正在整理玩家行动..."}
        protagonist_turn = run_protagonist_fallback(context, user_input)
    else:
        yield {"type": "status", "message": "正在推演主角行动..."}
        protagonist_turn = run_protagonist_agent(context, user_input)
    protagonist_story = _protagonist_visible_story(protagonist_turn)
    chunks: list[str] = []
    if protagonist_story:
        first_chunk = f"{protagonist_story}\n\n"
        chunks.append(first_chunk)
        yield {"type": "delta", "text": first_chunk}

    if fast_mode:
        npc_reactions = {
            "reactions": [],
            "selected_npcs": [],
            "omitted_npcs": [],
            "selection_reason": "快速模式跳过 NPC 独立反应推演。",
        }
    else:
        yield {"type": "status", "message": "正在推演 NPC 反应..."}
        npc_reactions = run_npc_reaction_agent(context, user_input, protagonist_turn)
    npc_reactions = {**npc_reactions, "protagonist_turn": protagonist_turn}

    yield {"type": "status", "message": "正在生成剧情..."}
    hint_box: dict = {}
    for chunk in _iter_visible_chunks_with_hint(
        run_narrator_stream_agent(context, user_input, protagonist_turn, npc_reactions),
        hint_box,
    ):
        chunks.append(chunk)
        yield {"type": "delta", "text": chunk}

    visible_story = "".join(chunks).strip() or "剧情生成失败：模型没有返回内容。"
    visible_story, fallback_hint = _split_visible_story_and_hint(visible_story)
    state_hint = hint_box.get("state_hint") or fallback_hint

    should_async_update = async_state_update and not skip_state_update
    should_hint_update = skip_state_update or should_async_update
    if skip_state_update:
        yield {"type": "status", "message": "极速模式：正在应用 Hint 软状态并保存剧情..."}
    elif should_async_update:
        yield {"type": "status", "message": "剧情已完成，状态整理转入后台..."}
    else:
        yield {"type": "status", "message": "正在整理状态变化..."}
    if should_hint_update:
        state_patch = _apply_state_hint(game_id, state_hint, session)
        checker_result = _pending_checker_result() if should_async_update else _skipped_checker_result("极速模式已应用 Hint 软状态，跳过完整状态整理。")
        checker_result["state_hint_applied"] = bool(state_patch.get("updated_characters") or state_patch.get("current_state_update"))
        apply_result = (
            {"ok": True, "pending": True, "message": "状态整理已转入后台执行。"}
            if should_async_update
            else {"ok": True, "skipped": True, "message": "已应用 Hint 软状态，完整状态整理已跳过。"}
        )
    else:
        state_patch, checker_result, apply_result = _resolve_state_update(
            game_id,
            context,
            user_input,
            npc_reactions,
            visible_story,
            session,
            skip_state_update=skip_state_update,
        )

    turn = save_turn_and_snapshot(
        game_id=game_id,
        turn_number=turn_number,
        user_input=user_input,
        visible_story=visible_story,
        npc_reactions=npc_reactions,
        state_patch=state_patch,
        checker_result=checker_result,
        snapshot_before_turn=snapshot_before_turn,
        session=session,
    )
    rag_memory = store_turn_memory(game_id, turn, visible_story, npc_reactions, state_patch, checker_result, session)
    if should_async_update:
        _schedule_async_state_update(game_id, turn.id, context, user_input, npc_reactions, visible_story)

    yield {
        "type": "done",
        "visible_story": visible_story,
        "npc_reactions": npc_reactions,
        "state_patch": state_patch,
        "checker_result": checker_result,
        "apply_result": apply_result,
        "turn_id": turn.id,
        "retrieved_memories": context.get("retrieved_memories", []),
        "rag_memory_id": rag_memory.id if rag_memory else None,
        "fast_mode": fast_mode,
        "skip_state_update": skip_state_update,
        "async_state_update": should_async_update,
    }
