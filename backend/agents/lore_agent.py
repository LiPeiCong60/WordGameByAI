from __future__ import annotations

from json_utils import safe_json_loads
from llm_client import call_llm
from prompt_builder import build_lore_messages


def run_lore_agent(text: str) -> dict:
    raw = call_llm(build_lore_messages(text), response_format={"type": "json_object"}, agent_name="LoreAgent")
    data = safe_json_loads(raw, default={})
    if "error" in data:
        return {
            "title": "LLM 未配置",
            "category": "其他",
            "content": text,
            "canon_level": "soft_canon",
            "importance": 5,
            "error": "LoreAgent unavailable.",
        }
    return data
