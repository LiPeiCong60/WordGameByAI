from __future__ import annotations

from sqlmodel import Session, desc, select

from agents.checker_agent import run_checker_agent
from agents.narrator_agent import run_narrator_agent, run_narrator_stream_agent
from agents.npc_reaction_agent import run_npc_reaction_agent
from agents.opening_agent import run_opening_agent, run_opening_stream_agent
from agents.patch_agent import run_patch_agent
from agents.protagonist_agent import run_protagonist_agent, run_protagonist_fallback
from export_import import export_game
from json_utils import dump_json_field
from models import Character, Game, InventoryRecord, Item, StoryWorld, TurnLog, TurnSnapshot, WorldEvent, WorldLore, WorldTemplate
from patch_applier import apply_state_patch
from rag_service import attach_retrieved_memories, store_turn_memory


def _model_dump(record) -> dict:
    return record.model_dump() if hasattr(record, "model_dump") else record.dict()


def load_game_context(game_id: int, session: Session) -> dict:
    game = session.get(Game, game_id)
    if not game:
        raise ValueError(f"找不到游戏: {game_id}")
    current_story_world = session.get(StoryWorld, game.current_story_world_id) if game.current_story_world_id else None
    lore = session.exec(
        select(WorldLore).where(WorldLore.game_id == game_id).order_by(desc(WorldLore.importance))
    ).all()
    characters = session.exec(select(Character).where(Character.game_id == game_id)).all()
    items = session.exec(select(Item).where(Item.game_id == game_id)).all()
    inventory = session.exec(select(InventoryRecord).where(InventoryRecord.game_id == game_id)).all()
    events = session.exec(
        select(WorldEvent).where(WorldEvent.game_id == game_id).order_by(desc(WorldEvent.importance), desc(WorldEvent.id))
    ).all()
    recent_turns = session.exec(
        select(TurnLog).where(TurnLog.game_id == game_id).order_by(desc(TurnLog.id)).limit(5)
    ).all()
    templates = session.exec(select(WorldTemplate)).all()
    protagonist = next((c for c in characters if c.role_type == "protagonist"), None)
    return {
        "game": _model_dump(game),
        "current_story_world": _model_dump(current_story_world) if current_story_world else None,
        "world_lore": [_model_dump(item) for item in lore],
        "characters": [_model_dump(item) for item in characters],
        "protagonist": _model_dump(protagonist) if protagonist else None,
        "npcs": [_model_dump(c) for c in characters if c.role_type != "protagonist"],
        "items": [_model_dump(item) for item in items],
        "inventory_records": [_model_dump(item) for item in inventory],
        "world_events": [_model_dump(item) for item in events],
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


def _save_opening_turn(game_id: int, visible_story: str, snapshot_before_turn: dict, context: dict, session: Session) -> dict:
    state_patch = run_patch_agent(context, "系统开场白", {"reactions": []}, visible_story)
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


def run_game_turn(game_id: int, user_input: str, session: Session, fast_mode: bool = False) -> dict:
    context = attach_retrieved_memories(load_game_context(game_id, session), game_id, user_input, session)
    existing_turns = session.exec(select(TurnLog).where(TurnLog.game_id == game_id)).all()
    turn_number = len(existing_turns) + 1
    snapshot_before_turn = export_game(game_id, session)
    protagonist_turn = run_protagonist_fallback(context, user_input) if fast_mode else run_protagonist_agent(context, user_input)
    npc_reactions = (
        {"reactions": [], "selected_npcs": [], "omitted_npcs": [], "selection_reason": "快速模式跳过 NPC 独立反应推演。"}
        if fast_mode
        else run_npc_reaction_agent(context, user_input, protagonist_turn)
    )
    npc_reactions = {**npc_reactions, "protagonist_turn": protagonist_turn}
    story = run_narrator_agent(context, user_input, protagonist_turn, npc_reactions)
    visible_story = _compose_visible_story(protagonist_turn, story.get("visible_story", ""))
    state_patch = run_patch_agent(context, user_input, npc_reactions, visible_story)
    checker_result = run_checker_agent(context, visible_story, state_patch)

    apply_result = None
    if checker_result.get("ok"):
        apply_result = apply_state_patch(game_id, state_patch, session)

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
    }


def run_game_turn_stream(game_id: int, user_input: str, session: Session, fast_mode: bool = False):
    yield {"type": "status", "message": "正在检索相关世界观和角色记忆..."}
    context = attach_retrieved_memories(load_game_context(game_id, session), game_id, user_input, session)
    existing_turns = session.exec(select(TurnLog).where(TurnLog.game_id == game_id)).all()
    turn_number = len(existing_turns) + 1
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
    for chunk in run_narrator_stream_agent(context, user_input, protagonist_turn, npc_reactions):
        chunks.append(chunk)
        yield {"type": "delta", "text": chunk}

    visible_story = "".join(chunks).strip() or "剧情生成失败：模型没有返回内容。"

    yield {"type": "status", "message": "正在整理状态变化..."}
    state_patch = run_patch_agent(context, user_input, npc_reactions, visible_story)
    checker_result = run_checker_agent(context, visible_story, state_patch)

    apply_result = None
    if checker_result.get("ok"):
        apply_result = apply_state_patch(game_id, state_patch, session)

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
    }
