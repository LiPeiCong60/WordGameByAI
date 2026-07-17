from __future__ import annotations

from datetime import datetime, timezone


def utc_now() -> datetime:
    """Return UTC as a naive datetime for compatibility with existing DB columns."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def utc_from_timestamp(value: int | float) -> datetime:
    return datetime.fromtimestamp(value, timezone.utc).replace(tzinfo=None)
