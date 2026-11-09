"""Static, illustrative data used by the mock adapters (no network, no credentials)."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

_DIR = Path(__file__).parent


@lru_cache
def _load(name: str) -> str:
    if "/" in name or "\\" in name or not name.endswith(".json"):
        raise ValueError("invalid mock data file name")
    return (_DIR / name).read_text(encoding="utf-8")


def load_mock_json(name: str) -> Any:
    # Return a fresh copy on every call so callers can mutate safely.
    return json.loads(_load(name))
