from __future__ import annotations

from json_utils import safe_json_loads
from llm_client import call_llm
from prompt_builder import build_protagonist_messages


def run_protagonist_agent(context: dict, user_input: str) -> dict:
    raw = call_llm(
        build_protagonist_messages(context, user_input),
        response_format={"type": "json_object"},
        agent_name="ProtagonistAgent",
    )
    data = safe_json_loads(raw, default={})
    if "error" in data:
        fallback = _fallback_protagonist_turn(context, user_input)
        return {**fallback, "error": data["error"]}
    if "visible_story" not in data:
        return _fallback_protagonist_turn(context, user_input)
    data.setdefault("intent_summary", user_input)
    return data


def run_protagonist_fallback(context: dict, user_input: str) -> dict:
    return _fallback_protagonist_turn(context, user_input)


def _fallback_protagonist_turn(context: dict, user_input: str) -> dict:
    protagonist = context.get("protagonist") or {}
    protagonist_name = protagonist.get("name") or "你"
    structured = _parse_structured_input(user_input)
    if structured:
        return _structured_fallback_turn(protagonist_name, structured)

    text = user_input.strip()
    if not text:
        visible_story = f"[{protagonist_name}停在原地，暂时没有新的动作。]"
    elif _looks_like_dialogue(text):
        visible_story = f"{protagonist_name}：{text}"
    else:
        visible_story = f"[{protagonist_name}{_normalize_action_text(text)}]"
    return {"visible_story": visible_story, "intent_summary": text}


def _parse_structured_input(user_input: str) -> dict | None:
    text = user_input.strip()
    if "【玩家回合输入】" not in text:
        return None

    data = {"action": "", "dialogue": "", "auto_complete": True}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if line.startswith("行动/背景/希望响应："):
            value = line.split("：", 1)[1].strip()
            data["action"] = "" if value.startswith("<留空") else value
        elif line.startswith("主角台词："):
            value = line.split("：", 1)[1].strip()
            data["dialogue"] = "" if value.startswith("<留空") else value
        elif line.startswith("空白补全："):
            data["auto_complete"] = "开启" in line
    return data


def _structured_fallback_turn(protagonist_name: str, data: dict) -> dict:
    action = str(data.get("action") or "").strip()
    dialogue = str(data.get("dialogue") or "").strip()
    auto_complete = bool(data.get("auto_complete", True))
    parts: list[str] = []

    if action:
        parts.append(f"[{protagonist_name}{_normalize_action_text(action)}]")
    elif dialogue and auto_complete:
        parts.append(f"[{protagonist_name}顺着当前局势，把注意力放回眼前的人和事。]")

    if dialogue:
        parts.append(f"{protagonist_name}：{dialogue}")
    elif not action:
        parts.append(f"[{protagonist_name}暂时保持沉默，等待局势继续变化。]")

    visible_story = "\n\n".join(parts)
    intent_parts = []
    if action:
        intent_parts.append(f"行动：{action}")
    if dialogue:
        intent_parts.append(f"台词：{dialogue}")
    if not intent_parts:
        intent_parts.append("无主动动作或台词")
    if not dialogue and not auto_complete:
        intent_parts.append("主角明确不说话")
    return {"visible_story": visible_story, "intent_summary": "；".join(intent_parts)}


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
