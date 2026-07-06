from __future__ import annotations

from json_utils import safe_json_loads
from llm_client import call_llm
from prompt_builder import build_checker_messages


def run_checker_agent(context: dict, visible_story: str, state_patch: dict) -> dict:
    raw = call_llm(
        build_checker_messages(context, visible_story, state_patch),
        response_format={"type": "json_object"},
        agent_name="CheckerAgent",
    )
    data = safe_json_loads(raw, default={})
    if "error" in data:
        return {"ok": False, "issues": [{"type": "llm_unavailable", "message": "CheckerAgent 不可用，已阻止自动落库。"}]}
    if "ok" not in data:
        return {"ok": False, "issues": [{"type": "invalid_checker_output", "message": "CheckerAgent 返回不是合法 JSON。"}]}
    return data
