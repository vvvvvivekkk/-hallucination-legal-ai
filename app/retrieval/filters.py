from __future__ import annotations

from typing import Any


def match_filters(payload: dict[str, Any], conditions: dict[str, Any] | None) -> bool:
    if not conditions:
        return True
    for field, spec in conditions.items():
        value = payload.get(field)
        if isinstance(spec, dict):
            if "min" in spec and (value is None or value < spec["min"]):
                return False
            if "max" in spec and (value is None or value > spec["max"]):
                return False
        elif isinstance(spec, (list, tuple, set)):
            if isinstance(value, list):
                matched = bool(set(value) & set(spec))
            else:
                matched = value in spec
            if not matched:
                return False
        else:
            if value != spec:
                return False
    return True
