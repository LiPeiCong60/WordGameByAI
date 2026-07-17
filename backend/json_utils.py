from __future__ import annotations

import json
import re
from copy import deepcopy
from typing import Any


def parse_json_field(value: Any, default: Any = None) -> Any:
    if default is None:
        default = {}
    if value in (None, ""):
        return deepcopy(default)
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return deepcopy(default)


def dump_json_field(value: Any) -> str:
    if value is None:
        value = {}
    if isinstance(value, str):
        parsed = parse_json_field(value, default=None)
        if parsed is not None:
            return json.dumps(parsed, ensure_ascii=False)
        return value
    return json.dumps(value, ensure_ascii=False, default=str)


def merge_json_field(old_value: Any, new_value: Any) -> str:
    old = parse_json_field(old_value, default={})
    new = parse_json_field(new_value, default={})
    if not isinstance(old, dict) or not isinstance(new, dict):
        return dump_json_field(new)
    merged = {**old, **new}
    return dump_json_field(merged)


def safe_json_loads(text: str, default: Any = None) -> Any:
    if default is None:
        default = {}
    if not text:
        return deepcopy(default)
    source = str(text).strip().lstrip("\ufeff")
    fenced = re.sub(r"^```(?:json)?\s*|\s*```$", "", source, flags=re.IGNORECASE)
    candidates = [source, fenced]
    balanced = _first_balanced_object(fenced)
    if balanced:
        candidates.append(balanced)
    for candidate in candidates:
        for repaired in (candidate, re.sub(r",\s*([}\]])", r"\1", candidate)):
            try:
                return json.loads(repaired)
            except (TypeError, json.JSONDecodeError):
                continue
    return deepcopy(default)


def _first_balanced_object(text: str) -> str:
    start = text.find("{")
    if start < 0:
        return ""
    depth = 0
    in_string = False
    escaped = False
    for index in range(start, len(text)):
        char = text[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start : index + 1]
    return ""
