from __future__ import annotations

import json
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
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                pass
    return deepcopy(default)
