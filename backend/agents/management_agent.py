from __future__ import annotations

from json_utils import safe_json_loads
from llm_client import call_llm
from prompt_builder import build_management_messages


def run_management_agent(context: dict, message: str, scope: str = "") -> dict:
    raw = call_llm(
        build_management_messages(context, message, scope),
        response_format={"type": "json_object"},
        agent_name="ManagementAgent",
    )
    data = safe_json_loads(raw, default={})
    if "error" in data:
        return {
            "reply": f"当前无法调用 ManagementAgent：{data['error']}",
            "proposed_actions": [],
            "requires_confirmation": False,
            "error": data["error"],
        }
    data.setdefault("reply", "我已整理出修改建议。")
    data.setdefault("proposed_actions", [])
    data.setdefault("requires_confirmation", bool(data["proposed_actions"]))
    return data
