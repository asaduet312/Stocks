"""Data normalisation utilities for psxdata parsers."""
from __future__ import annotations

import re
from typing import Any


def coerce_numeric(value: Any) -> float | None:
    """Convert a raw PSX cell value to float, stripping formatting characters."""
    if value is None:
        return None
    if not isinstance(value, str):
        return None
    cleaned = value.strip()
    if not cleaned:
        return None
    cleaned = cleaned.replace(",", "").replace("%", "").replace("PKR", "").strip()
    try:
        return float(cleaned)
    except (ValueError, TypeError):
        return None


def normalize_column_name(name: str) -> str:
    """Normalize a raw PSX table header to a snake_case identifier."""
    name = name.strip().lower()
    name = name.replace(" ", "_")
    name = re.sub(r"[^\w]", "_", name)
    name = re.sub(r"_+", "_", name)
    name = name.strip("_")
    return name
