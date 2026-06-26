from __future__ import annotations

from typing import Iterator

from json_utils import safe_json_loads
from llm_client import call_llm, call_llm_stream
from prompt_builder import build_opening_messages, build_opening_stream_messages


def run_opening_agent(context: dict) -> dict:
    raw = call_llm(build_opening_messages(context), response_format={"type": "json_object"})
    data = safe_json_loads(raw, default={})
    if "error" in data:
        return {"visible_story": f"无法生成开场白：{data['error']}"}
    return data if "visible_story" in data else {"visible_story": "开场白生成失败：LLM 返回不是合法 JSON。"}


def run_opening_stream_agent(context: dict) -> Iterator[str]:
    yield from call_llm_stream(build_opening_stream_messages(context))
