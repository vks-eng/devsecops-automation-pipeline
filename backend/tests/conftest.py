"""Test fixtures. Tests ALWAYS run against PostgreSQL.

* CI: ``TEST_DATABASE_URL`` points at a Postgres service container.
* Local: if ``TEST_DATABASE_URL`` is unset, an embedded PostgreSQL is started with the
  ``pgserver`` dev dependency (no system install, no Docker).
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

os.environ.update(
    {
        "ENVIRONMENT": "test",
        "SECRET_KEY": "test-secret-key-for-pytest-only-0123456789",
        "GITHUB_WEBHOOK_SECRET": "test-webhook-secret",
        "CELERY_TASK_ALWAYS_EAGER": "true",
        "GITHUB_MODE": "mock",
        "SONARQUBE_MODE": "mock",
        "TRIVY_MODE": "mock",
        "DOCKER_MODE": "mock",
        "PIP_AUDIT_MODE": "mock",
        "NOTIFICATION_WEBHOOK_URL": "",
        "SMTP_HOST": "",
        "TOKEN_ENCRYPTION_KEY": "",
    }
)

FIXTURES = Path(__file__).parent / "fixtures"
BACKEND = Path(__file__).resolve().parents[1]


def load_fixture(name: str) -> Any:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def _normalise(url: str) -> str:
    return url.replace("postgresql://", "postgresql+psycopg2://", 1)


@pytest.fixture(scope="session")
def database_url() -> Iterator[str]:
    external = os.environ.get("TEST_DATABASE_URL")
    if external:
        yield _normalise(external)
        return
    try:
        import pgserver
        import psycopg2
    except ImportError:  # pragma: no cover
        pytest.exit("Set TEST_DATABASE_URL or install the 'pgserver' dev dependency", 2)
    data_dir = tempfile.mkdtemp(prefix="shieldops-pg-")
    server = pgserver.get_server(data_dir, cleanup_mode="delete")
    conn = psycopg2.connect(server.get_uri())
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute("CREATE DATABASE shieldops_test")
    conn.close()
    logging.getLogger("pgserver").setLevel(logging.WARNING)
    yield _normalise(server.get_uri("shieldops_test"))
    from app.db.session import get_engine

    get_engine().dispose()
    server.cleanup()


@pytest.fixture(scope="session")
def migrated(database_url: str) -> str:
    os.environ["DATABASE_URL"] = database_url
    from app.core.config import get_settings
    from app.db.session import get_engine, get_sessionmaker

    get_settings.cache_clear()
    get_engine.cache_clear()
    get_sessionmaker.cache_clear()

    from alembic import command
    from alembic.config import Config

    cfg = Config(str(BACKEND / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND / "alembic"))
    cfg.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")
    return database_url


@pytest.fixture(autouse=True)
def clean_db(migrated: str) -> Iterator[None]:
    from sqlalchemy import text

    from app.adapters import registry
    from app.api.routes.auth import reset_throttle
    from app.db.base import Base
    from app.db.session import get_engine

    yield
    registry.clear_overrides()
    reset_throttle()
    tables = ", ".join(f'"{t.name}"' for t in Base.metadata.sorted_tables)
    with get_engine().begin() as conn:
        conn.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))


@pytest.fixture
def db(migrated: str) -> Iterator[Any]:
    from app.db.session import get_sessionmaker

    session = get_sessionmaker()()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(migrated: str) -> Iterator[Any]:
    from fastapi.testclient import TestClient

    from app.main import create_app

    with TestClient(create_app()) as c:
        yield c


API = "/api/v1"


def register(client: Any, email: str, password: str = "Password12345") -> dict[str, str]:
    r = client.post(
        f"{API}/auth/register",
        json={"email": email, "password": password, "full_name": email.split("@")[0]},
    )
    assert r.status_code == 201, r.text
    r = client.post(f"{API}/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture
def admin_headers(client: Any) -> dict[str, str]:
    return register(client, "admin@example.com")


@pytest.fixture
def user_headers(client: Any, admin_headers: dict[str, str]) -> dict[str, str]:
    return register(client, "member@example.com")


PROJECT_PAYLOAD = {
    "name": "Payments API",
    "repo_url": "https://github.com/acme-demo/payments-api",
    "team": "Payments",
    "default_branch": "main",
    "branches": ["develop"],
    "sonar_project_key": "acme_payments-api",
    "container_images": ["ghcr.io/acme-demo/payments-api:1.8.2", "python:3.11-slim"],
}


@pytest.fixture
def project(client: Any, admin_headers: dict[str, str]) -> dict[str, Any]:
    r = client.post(f"{API}/projects", json=PROJECT_PAYLOAD, headers=admin_headers)
    assert r.status_code == 201, r.text
    return r.json()
