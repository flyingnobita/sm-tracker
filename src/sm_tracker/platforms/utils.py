"""Shared utility helpers for platform adapters."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def extract_int(data: Any, *keys: str) -> int | None:
    """Return the first int found by trying each key via attr then mapping access.

    Checks attribute access first (for SDK response objects), then mapping
    access (for plain dicts). Tries keys in order and returns on the first
    successful conversion. Returns None if no key yields a coercible value.
    """
    for key in keys:
        value = getattr(data, key, None)
        if value is None and isinstance(data, Mapping):
            value = data.get(key)
        if value is not None:
            try:
                return int(value)
            except (ValueError, TypeError):
                return None
    return None


def coerce_int(value: Any) -> int | None:
    """Coerce a raw value to int, returning None if the value is absent or non-numeric."""
    if value is None:
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None
