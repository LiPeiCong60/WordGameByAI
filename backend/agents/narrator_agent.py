from __future__ import annotations

from typing import Iterator

from json_utils import safe_json_loads
from llm_client import call_llm, call_llm_stream
from prompt_builder import build_narrator_messages, build_narrator_stream_messages


def run_narrator_agent(context: dict, user_input: str, protagonist_turn: dict, npc_reactions: dict) -> dict:
    raw = call_llm(
        build_narrator_messages(context, user_input, protagonist_turn, npc_reactions),
        response_format={"type": "json_object"},
        agent_name="NarratorAgent",
    )
    data = safe_json_loads(raw, default={})
    if "error" in data:
        return {"visible_story": "无法生成剧情：模型服务暂时不可用，请稍后重试。"}
    return data if "visible_story" in data else {"visible_story": "剧情生成失败：LLM 返回不是合法剧情 JSON。"}


def run_narrator_stream_agent(context: dict, user_input: str, protagonist_turn: dict, npc_reactions: dict) -> Iterator[str]:
    yield from call_llm_stream(
        build_narrator_stream_messages(context, user_input, protagonist_turn, npc_reactions),
        agent_name="NarratorStreamAgent",
    )
