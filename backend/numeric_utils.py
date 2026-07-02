from __future__ import annotations


def as_int(value, default: int = 0) -> int:
    if isinstance(value, str):
        normalized = value.strip().lower()
        semantic_values = {
            "none": 0,
            "unknown": default,
            "low": 3,
            "minor": 3,
            "small": 3,
            "normal": 5,
            "medium": 5,
            "moderate": 5,
            "mid": 5,
            "high": 8,
            "important": 8,
            "critical": 10,
            "core": 10,
            "低": 3,
            "普通": 5,
            "一般": 5,
            "中": 5,
            "正常": 5,
            "高": 8,
            "重要": 8,
            "核心": 10,
            "关键": 10,
        }
        if normalized in semantic_values:
            return semantic_values[normalized]
    try:
        return int(value)
    except (TypeError, ValueError):
        return default
