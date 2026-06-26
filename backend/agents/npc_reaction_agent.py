from __future__ import annotations

from json_utils import safe_json_loads
from llm_client import call_llm
from prompt_builder import build_npc_reaction_messages


def run_npc_reaction_agent(context: dict, user_input: str, protagonist_turn: dict | None = None) -> dict:
    enabled_npcs = [npc for npc in context.get("npcs", []) if npc.get("agent_enabled", True)]
    disabled_npcs = [npc for npc in context.get("npcs", []) if not npc.get("agent_enabled", True)]
    if not enabled_npcs:
        return {
            "reactions": [],
            "agent_enabled_npcs": [],
            "agent_disabled_npcs": [npc.get("name") for npc in disabled_npcs if npc.get("name")],
            "note": "当前没有启用 NPC 子 Agent 的角色；旁白仍可根据存档正常描写这些 NPC。",
        }

    agent_context = {
        **context,
        "npcs": enabled_npcs,
        "agent_disabled_npcs": disabled_npcs,
        "npc_agent_policy": "只为 agent_enabled=true 的 NPC 做独立反应推演；关闭子 Agent 的 NPC 由 NarratorAgent 普通描写。",
    }
    raw = call_llm(
        build_npc_reaction_messages(agent_context, user_input, protagonist_turn),
        response_format={"type": "json_object"},
    )
    data = safe_json_loads(raw, default={})
    if "error" in data:
        return {"reactions": [], "error": data["error"]}
    if "reactions" not in data:
        data = {"reactions": []}
    data.setdefault("agent_enabled_npcs", [npc.get("name") for npc in enabled_npcs if npc.get("name")])
    data.setdefault("agent_disabled_npcs", [npc.get("name") for npc in disabled_npcs if npc.get("name")])
    data.setdefault("selected_npcs", [])
    data.setdefault("omitted_npcs", [npc.get("name") for npc in enabled_npcs if npc.get("name")])
    data.setdefault("selection_reason", "模型未返回选择理由。")
    return data
