from __future__ import annotations

from json_utils import safe_json_loads
from llm_client import call_llm
from prompt_builder import build_protagonist_messages


def run_protagonist_agent(context: dict, user_input: str) -> dict:
    raw = call_llm(build_protagonist_messages(context, user_input), response_format={"type": "json_object"})
    data = safe_json_loads(raw, default={})
    if "error" in data:
        fallback = _fallback_protagonist_turn(context, user_input)
        return {**fallback, "error": data["error"]}
    if "visible_story" not in data:
        return _fallback_protagonist_turn(context, user_input)
    data.setdefault("intent_summary", user_input)
    return data


def _fallback_protagonist_turn(context: dict, user_input: str) -> dict:
    protagonist = context.get("protagonist") or {}
    protagonist_name = protagonist.get("name") or "你"
    text = user_input.strip()
    if not text:
        visible_story = f"[{protagonist_name}停在原地，暂时没有新的动作。]"
    elif _looks_like_dialogue(text):
        visible_story = f"{protagonist_name}：{text}"
    else:
        visible_story = f"[{protagonist_name}{_normalize_action_text(text)}]"
    return {"visible_story": visible_story, "intent_summary": text}


def _looks_like_dialogue(text: str) -> bool:
    dialogue_markers = ("吗", "呢", "？", "?", "怎么样", "为什么", "怎么", "你好", "还不错", "我想", "我觉得")
    action_markers = ("走", "拿", "看", "打开", "关闭", "推", "拉", "点", "抽", "穿", "坐", "站", "进入", "离开")
    if any(marker in text for marker in dialogue_markers):
        return True
    return not any(marker in text for marker in action_markers) and len(text) <= 18


def _normalize_action_text(text: str) -> str:
    if text.startswith(("，", "。", "、", "：", ":", " ")):
        return text
    return f" {text}"
