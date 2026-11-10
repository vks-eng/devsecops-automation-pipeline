"""Configuration validation tests (Settings is built from explicit kwargs, not the env)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.core.config import Settings


def make(**kwargs: object) -> Settings:
    return Settings(_env_file=None, **kwargs)  # type: ignore[call-arg]


def test_defaults_use_mock_integrations_and_eager_tasks() -> None:
    s = make()
    assert (s.github_mode, s.sonarqube_mode, s.trivy_mode, s.docker_mode, s.pip_audit_mode) == (
        "mock", "mock", "mock", "mock", "mock")
    assert s.celery_task_always_eager is True


@pytest.mark.parametrize("url", ["sqlite:///x.db", "mysql://u:p@h/db", "postgres-ish://x"])
def test_only_postgresql_is_accepted(url: str) -> None:
    with pytest.raises(ValidationError, match="PostgreSQL"):
        make(database_url=url)


def test_postgres_url_is_normalised_to_psycopg2() -> None:
    assert make(database_url="postgresql://u:p@h/db").database_url == (
        "postgresql+psycopg2://u:p@h/db")


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("http://a, http://b", ["http://a", "http://b"]), ('["http://x"]', ["http://x"]),
     ("", [])],
)
def test_cors_origins_accept_csv_and_json(raw: str, expected: list[str],
                                          monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CORS_ORIGINS", raw)
    assert Settings(_env_file=None).cors_origins == expected  # type: ignore[call-arg]


@pytest.mark.parametrize(
    ("field", "value"),
    [("github_mode", "live"), ("trivy_mode", "real"), ("jwt_algorithm", "none"),
     ("environment", "staging"), ("secret_key", "short")],
)
def test_invalid_values_are_rejected(field: str, value: str) -> None:
    with pytest.raises(ValidationError):
        make(**{field: value})


def test_real_modes_are_selectable() -> None:
    s = make(github_mode="real", sonarqube_mode="real", trivy_mode="docker", docker_mode="real",
             pip_audit_mode="real")
    assert s.trivy_mode == "docker"
