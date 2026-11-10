"""Unit tests are pure: no database, no network, no subprocesses."""

from __future__ import annotations

from collections.abc import Iterator

import pytest


@pytest.fixture(autouse=True)
def clean_db() -> Iterator[None]:  # overrides the DB-backed autouse fixture
    yield
