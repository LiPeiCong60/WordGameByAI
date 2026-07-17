from __future__ import annotations

import re
from collections import Counter
from typing import Any


INTERNAL_TAG_RE = re.compile(r"<\s*/?\s*(?:dummy_)?state[_-]?hint\b", re.IGNORECASE)
JSON_WRAPPER_RE = re.compile(r"^\s*\{.*(?:visible_story|state_hint).*\}\s*$", re.DOTALL)
SPEAKER_RE = re.compile(r"^[\u4e00-\u9fa5A-Za-z0-9_·・]{1,20}[：:].+")
SPEAKER_ANY_RE = re.compile(r"[\u4e00-\u9fa5A-Za-z0-9_·・]{1,20}[：:]")
GLUED_BLOCK_RE = re.compile(
    r"[\]】)）]\s*(?=[\[【(（]|[\u4e00-\u9fa5A-Za-z0-9_·・]{1,20}[：:])"
)


def _paragraphs(text: str) -> list[str]:
    return [part.strip() for part in re.split(r"\n+", text or "") if part.strip()]


def _is_formatted_paragraph(paragraph: str) -> bool:
    if paragraph.startswith("[") and paragraph.endswith("]"):
        return True
    if paragraph.startswith("(") and paragraph.endswith(")"):
        return True
    if paragraph.startswith("【") and paragraph.endswith("】"):
        return True
    if paragraph.startswith("（") and paragraph.endswith("）"):
        return True
    return bool(SPEAKER_RE.match(paragraph))


def analyze_story_quality(
    visible_story: str,
    *,
    user_input: str = "",
    recent_turns: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    text = (visible_story or "").strip()
    paragraphs = _paragraphs(text)
    format_issues: list[dict[str, str]] = []
    content_issues: list[dict[str, str]] = []

    if not text:
        format_issues.append({"code": "empty_story", "message": "模型没有返回可见剧情。"})
    if INTERNAL_TAG_RE.search(text):
        format_issues.append({"code": "internal_tag_leak", "message": "输出包含内部状态标签。"})
    if JSON_WRAPPER_RE.match(text):
        format_issues.append({"code": "json_wrapper", "message": "模型把剧情包在 JSON 中返回。"})
    glued_dialogue = any(len(SPEAKER_ANY_RE.findall(part)) > 1 for part in paragraphs)
    if GLUED_BLOCK_RE.search(text) or glued_dialogue:
        format_issues.append(
            {
                "code": "glued_segments",
                "message": "动作、心理或多个角色对白粘在同一段，移动端需要容错拆分。",
            }
        )

    bare = [part for part in paragraphs if not _is_formatted_paragraph(part)]
    if paragraphs and len(bare) / len(paragraphs) > 0.35:
        format_issues.append(
            {
                "code": "format_drift",
                "message": f"{len(bare)}/{len(paragraphs)} 个段落不符合动作、心理或角色台词格式。",
            }
        )

    if 0 < len(text) < 80:
        content_issues.append({"code": "too_short", "message": "剧情过短，可能没有充分回应玩家行动。"})
    if len(text) > 6000:
        content_issues.append({"code": "too_long", "message": "单轮剧情过长，容易稀释重点并增加状态提取误差。"})

    normalized = [re.sub(r"\s+", "", part) for part in paragraphs]
    duplicate_count = sum(count - 1 for count in Counter(normalized).values() if count > 1)
    if duplicate_count:
        content_issues.append({"code": "duplicate_paragraph", "message": "剧情存在完全重复的段落。"})

    recent_text = "\n".join(str(item.get("ai_response") or "") for item in (recent_turns or [])[-3:])
    repeated_recent = [part for part in normalized if len(part) >= 24 and part in re.sub(r"\s+", "", recent_text)]
    if repeated_recent:
        content_issues.append({"code": "repeats_recent_turn", "message": "剧情重复了最近回合的完整句段。"})

    if user_input.strip() and text and not paragraphs:
        content_issues.append({"code": "no_structured_response", "message": "未检测到对玩家输入的结构化剧情响应。"})

    likely_cause = "none"
    if format_issues:
        likely_cause = "format_or_parser"
    elif content_issues:
        likely_cause = "prompt_context_or_model"

    score = max(0, 100 - len(format_issues) * 25 - len(content_issues) * 12)
    return {
        "ok": not format_issues and not content_issues,
        "score": score,
        "likely_cause": likely_cause,
        "format_issues": format_issues,
        "content_issues": content_issues,
        "metrics": {
            "characters": len(text),
            "paragraphs": len(paragraphs),
            "bare_paragraphs": len(bare),
        },
    }


def attach_quality_diagnostics(checker_result: dict[str, Any], quality: dict[str, Any]) -> dict[str, Any]:
    return {**(checker_result or {}), "output_quality": quality}
