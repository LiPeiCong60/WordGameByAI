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
            "reply": "当前无法调用 ManagementAgent：模型服务暂时不可用。",
            "proposed_actions": [],
            "requires_confirmation": False,
            "error": "ManagementAgent unavailable.",
        }
    data.setdefault("reply", "我已整理出修改建议。")
    data.setdefault("proposed_actions", [])
    data.setdefault("requires_confirmation", bool(data["proposed_actions"]))
    return data
