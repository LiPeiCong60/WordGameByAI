from __future__ import annotations

import json
import math
import re
from collections import Counter
from datetime import datetime
from typing import Any

from sqlmodel import Session, select

from json_utils import dump_json_field, parse_json_field
from models import Character, Game, RagMemory, TurnLog, WorldLore

VECTOR_SIZE = 256
MAX_MEMORY_CONTENT = 900


def _model_dump(record) -> dict:
    return record.model_dump() if hasattr(record, "model_dump") else record.dict()


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def _clip(text: str, limit: int = MAX_MEMORY_CONTENT) -> str:
    text = _normalize_text(text)
    return text if len(text) <= limit else text[: limit - 1] + "..."


def _tokens(text: str) -> list[str]:
    text = (text or "").lower()
    latin_tokens = re.findall(r"[a-z0-9_]+", text)
    cjk_chars = re.findall(r"[\u4e00-\u9fff]", text)
    cjk_bigrams = ["".join(cjk_chars[i : i + 2]) for i in range(max(0, len(cjk_chars) - 1))]
    return latin_tokens + cjk_chars + cjk_bigrams


def _vectorize(text: str) -> dict[str, float]:
    counts: Counter[int] = Counter()
    for token in _tokens(text):
        counts[hash(token) % VECTOR_SIZE] += 1
    norm = math.sqrt(sum(value * value for value in counts.values()))
    if not norm:
        return {}
    return {str(index): value / norm for index, value in counts.items()}


def _cosine(left: dict[str, float], right: dict[str, float]) -> float:
    if not left or not right:
        return 0.0
    if len(left) > len(right):
        left, right = right, left
    return sum(value * right.get(index, 0.0) for index, value in left.items())


def _memory_text(title: str, content: str, tags: str = "") -> str:
    return "\n".join(part for part in [title, tags, content] if part)


def _upsert_memory(
    db: Session,
    game_id: int,
    source_type: str,
    source_id: int | None,
    title: str,
    content: str,
    tags: str = "",
    importance: int = 5,
    extra_attrs: dict[str, Any] | None = None,
) -> RagMemory | None:
    content = _clip(content)
    if not content:
        return None
    query = select(RagMemory).where(RagMemory.game_id == game_id, RagMemory.source_type == source_type)
    if source_id is None:
        query = query.where(RagMemory.source_id.is_(None))
    else:
        query = query.where(RagMemory.source_id == source_id)
    memory = db.exec(query).first()
    if not memory:
        memory = RagMemory(game_id=game_id, source_type=source_type, source_id=source_id)
    memory.title = title
    memory.content = content
    memory.tags = tags
    memory.importance = max(1, min(10, int(importance or 5)))
    memory.embedding_json = dump_json_field(_vectorize(_memory_text(title, content, tags)))
    memory.extra_attrs = dump_json_field(extra_attrs or {})
    memory.updated_at = datetime.utcnow()
    db.add(memory)
    return memory


def sync_rag_memories(game_id: int, db: Session) -> dict[str, int]:
    game = db.get(Game, game_id)
    if not game:
        raise ValueError(f"找不到游戏: {game_id}")

    counts = {"world_lore": 0, "characters": 0}

    for lore in db.exec(select(WorldLore).where(WorldLore.game_id == game_id)).all():
        content = f"分类:{lore.category}\n权威级别:{lore.canon_level}\n设定:{lore.content}"
        if _upsert_memory(db, game_id, "world_lore", lore.id, lore.title, content, lore.category, lore.importance):
            counts["world_lore"] += 1

    for character in db.exec(select(Character).where(Character.game_id == game_id)).all():
        parts = [
            f"角色:{character.name}",
            f"身份:{character.role_type} {character.race_or_identity}".strip(),
            f"性格:{character.personality}",
            f"说话风格:{character.speech_style}",
            f"当前位置:{character.current_location}",
            f"状态:{character.status}",
            f"心情:{character.mood}",
            f"与玩家关系:{character.relationship_to_player}",
            f"关系分:{character.relationship_score}",
            f"好感度:{character.affection_score}",
            f"信任度:{character.trust_score}",
            f"张力:{character.tension_score}",
            f"当前目标:{character.current_goal}",
            f"隐藏目标:{character.hidden_goal}",
            f"长期记忆:{character.memory_summary}",
        ]
        tags = ",".join(filter(None, ["character", character.role_type, character.name]))
        if _upsert_memory(db, game_id, "character", character.id, character.name, "\n".join(parts), tags, 7):
            counts["characters"] += 1

    db.commit()
    return counts


def retrieve_related_memories(game_id: int, query: str, db: Session, top_k: int = 6) -> list[dict[str, Any]]:
    sync_rag_memories(game_id, db)
    query_vector = _vectorize(query)
    memories = db.exec(select(RagMemory).where(RagMemory.game_id == game_id)).all()
    scored: list[tuple[float, RagMemory]] = []
    query_terms = set(_tokens(query))
    for memory in memories:
        vector = parse_json_field(memory.embedding_json, default={})
        if not isinstance(vector, dict):
            vector = {}
        score = _cosine(query_vector, {str(k): float(v) for k, v in vector.items()})
        memory_terms = set(_tokens(_memory_text(memory.title, memory.content, memory.tags)))
        lexical_overlap = len(query_terms & memory_terms) / max(1, len(query_terms))
        score = score * 0.82 + lexical_overlap * 0.14 + (memory.importance / 10) * 0.04
        if score > 0:
            scored.append((score, memory))
    scored.sort(key=lambda item: item[0], reverse=True)
    return [
        {
            **_model_dump(memory),
            "score": round(score, 4),
        }
        for score, memory in scored[: max(1, min(top_k, 20))]
    ]


def attach_retrieved_memories(context: dict[str, Any], game_id: int, query: str, db: Session, top_k: int = 6) -> dict[str, Any]:
    memories = retrieve_related_memories(game_id, query, db, top_k=top_k)
    return {
        **context,
        "retrieved_memories": [
            {
                "source_type": item["source_type"],
                "source_id": item.get("source_id"),
                "title": item["title"],
                "content": item["content"],
                "tags": item.get("tags", ""),
                "importance": item.get("importance", 5),
                "score": item["score"],
            }
            for item in memories
        ],
    }


def _summarize_state_patch(state_patch: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    if state_patch.get("current_state_update"):
        lines.append(f"当前状态更新:{state_patch['current_state_update']}")
    for item in state_patch.get("updated_characters") or []:
        if isinstance(item, dict):
            changes = ", ".join(f"{key}={value}" for key, value in item.items() if key != "name")
            lines.append(f"角色变化:{item.get('name', '未知角色')} {changes}")
    return lines


def store_turn_memory(
    game_id: int,
    turn: TurnLog,
    visible_story: str,
    npc_reactions: dict[str, Any],
    state_patch: dict[str, Any],
    checker_result: dict[str, Any],
    db: Session,
) -> RagMemory | None:
    if checker_result and checker_result.get("ok") is False:
        return None
    patch_lines = _summarize_state_patch(state_patch)
    reaction_names = []
    for item in (npc_reactions or {}).get("reactions") or []:
        if isinstance(item, dict) and item.get("name"):
            reaction_names.append(str(item["name"]))
    content = "\n".join(
        [
            f"第 {turn.turn_number} 回合",
            f"玩家输入:{turn.user_input}",
            f"剧情摘要:{_clip(visible_story, 520)}",
            f"NPC:{', '.join(reaction_names)}" if reaction_names else "",
            *patch_lines,
        ]
    )
    tags = ",".join(filter(None, ["turn", f"turn:{turn.turn_number}", *reaction_names]))
    memory = _upsert_memory(
        db,
        game_id,
        "turn_summary",
        turn.id,
        f"第 {turn.turn_number} 回合记忆",
        content,
        tags,
        6,
        {"turn_number": turn.turn_number},
    )
    db.commit()
    if memory:
        db.refresh(memory)
    return memory


def rebuild_rag_memories(game_id: int, db: Session) -> dict[str, Any]:
    existing = db.exec(select(RagMemory).where(RagMemory.game_id == game_id)).all()
    for memory in existing:
        db.delete(memory)
    db.commit()
    counts = sync_rag_memories(game_id, db)
    turn_count = 0
    for turn in db.exec(select(TurnLog).where(TurnLog.game_id == game_id).order_by(TurnLog.turn_number)).all():
        memory = _upsert_memory(
            db,
            game_id,
            "turn_summary",
            turn.id,
            f"第 {turn.turn_number} 回合记忆",
            "\n".join([f"玩家输入:{turn.user_input}", f"剧情摘要:{_clip(turn.ai_response, 520)}"]),
            f"turn,turn:{turn.turn_number}",
            6,
            {"turn_number": turn.turn_number},
        )
        if memory:
            turn_count += 1
    db.commit()
    return {"ok": True, "synced": {**counts, "turn_summaries": turn_count}}
