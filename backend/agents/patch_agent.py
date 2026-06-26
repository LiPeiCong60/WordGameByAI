from __future__ import annotations

from json_utils import safe_json_loads
from llm_client import call_llm
from prompt_builder import build_patch_messages


EMPTY_PATCH = {
    "current_state_update": "",
    "new_events": [],
    "new_characters": [],
    "ambient_characters": [],
    "updated_characters": [],
    "new_items": [],
    "updated_items": [],
    "inventory_updates": [],
    "updated_story_world": {},
    "player_choices": [],
}


def run_patch_agent(context: dict, user_input: str, npc_reactions: dict, visible_story: str) -> dict:
    raw = call_llm(
        build_patch_messages(context, user_input, npc_reactions, visible_story),
        response_format={"type": "json_object"},
    )
    data = safe_json_loads(raw, default={})
    if "error" in data:
        return {**EMPTY_PATCH, "error": data["error"]}
    patch = {**EMPTY_PATCH, **data}
    return patch
