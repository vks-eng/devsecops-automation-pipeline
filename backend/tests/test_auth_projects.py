from __future__ import annotations

from typing import Any

import pytest

from app.adapters import registry
from app.adapters.base import AdapterError, RepoAccess
from app.adapters.github_actions import MockGitHubActionsAdapter
from app.models import AuditLog, IntegrationCredential
from tests.conftest import API, PROJECT_PAYLOAD, register

# ----------------------------------------------------------------------------- auth


def test_first_user_is_admin_and_second_is_member(client: Any) -> None:
    admin = register(client, "first@example.com")
    member = register(client, "second@example.com")
    assert client.get(f"{API}/auth/me", headers=admin).json()["role"] == "admin"
    assert client.get(f"{API}/auth/me", headers=member).json()["role"] == "member"
    assert client.get(f"{API}/users", headers=member).status_code == 403
    assert len(client.get(f"{API}/users", headers=admin).json()) == 2


def test_register_validation_and_duplicates(client: Any) -> None:
    register(client, "a@example.com")
    r = client.post(
        f"{API}/auth/register", json={"email": "A@example.com", "password": "Password12345"}
    )
    assert r.status_code == 409
    weak = client.post(
        f"{API}/auth/register", json={"email": "b@example.com", "password": "onlyletters"}
    )
    assert weak.status_code == 422
    bad_email = client.post(
        f"{API}/auth/register", json={"email": "nope", "password": "Password12345"}
    )
    assert bad_email.status_code == 422


def test_registration_can_be_disabled(client: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.config import get_settings

    register(client, "a@example.com")
    monkeypatch.setenv("ALLOW_REGISTRATION", "false")
    get_settings.cache_clear()
    try:
        r = client.post(
            f"{API}/auth/register", json={"email": "b@example.com", "password": "Password12345"}
        )
        assert r.status_code == 403
    finally:
        monkeypatch.undo()
        get_settings.cache_clear()


def test_login_failures_are_audited_and_throttled(client: Any, db: Any) -> None:
    register(client, "a@example.com")
    for _ in range(5):
        r = client.post(f"{API}/auth/login", json={"email": "a@example.com", "password": "bad"})
        assert r.status_code == 401
    r = client.post(
        f"{API}/auth/login", json={"email": "a@example.com", "password": "Password12345"}
    )
    assert r.status_code == 429
    outcomes = [a.outcome for a in db.query(AuditLog).filter(AuditLog.action == "auth.login")]
    assert outcomes.count("failure") == 5 and "blocked" in outcomes


def test_protected_routes_require_valid_token(client: Any) -> None:
    assert client.get(f"{API}/projects").status_code == 401
    assert (
        client.get(f"{API}/projects", headers={"Authorization": "Bearer junk"}).status_code == 401
    )
    assert client.get(f"{API}/auth/me", headers={"Authorization": "Basic abc"}).status_code == 401


def test_deactivated_user_loses_access(
    client: Any, admin_headers: dict, user_headers: dict
) -> None:
    me = client.get(f"{API}/auth/me", headers=user_headers).json()
    r = client.patch(f"{API}/users/{me['id']}", json={"is_active": False}, headers=admin_headers)
    assert r.status_code == 200
    assert client.get(f"{API}/auth/me", headers=user_headers).status_code == 401
    admin_id = client.get(f"{API}/auth/me", headers=admin_headers).json()["id"]
    r = client.patch(f"{API}/users/{admin_id}", json={"role": "member"}, headers=admin_headers)
    assert r.status_code == 400
    assert (
        client.patch(
            f"{API}/users/9999", json={"role": "member"}, headers=admin_headers
        ).status_code
        == 404
    )


# ----------------------------------------------------------------------------- projects


def test_create_and_get_project(client: Any, admin_headers: dict, project: dict) -> None:
    assert project["slug"] == "payments-api"
    assert project["repo_owner"] == "acme-demo"
    assert project["repo_name"] == "payments-api"
    assert project["my_role"] == "owner"
    assert project["scan_config"]["requirements_path"] == "requirements.txt"
    r = client.get(f"{API}/projects/{project['id']}", headers=admin_headers)
    assert r.status_code == 200
    dup = client.post(
        f"{API}/projects", json={**PROJECT_PAYLOAD, "name": "Other"}, headers=admin_headers
    )
    assert dup.status_code == 409


@pytest.mark.parametrize(
    "override",
    [
        {"repo_url": "https://github.com/acme/api.git"},
        {"repo_url": "https://evil.com/acme/api"},
        {"repo_url": "git@github.com:acme/api.git"},
        {"default_branch": "main; rm -rf /"},
        {"branches": ["../etc"]},
        {"container_images": ["nginx && curl evil"]},
        {"sonar_project_key": "bad key"},
        {"slug": "Bad Slug"},
        {"scan_config": {"requirements_path": "../../etc/passwd.txt"}},
        {"scan_config": {"requirements_path": "requirements.txt", "unknown": True}},
        {"name": "x"},
    ],
)
def test_project_validation(client: Any, admin_headers: dict, override: dict) -> None:
    r = client.post(f"{API}/projects", json={**PROJECT_PAYLOAD, **override}, headers=admin_headers)
    assert r.status_code == 422, r.text


def test_project_rbac(client: Any, admin_headers: dict, user_headers: dict, project: dict) -> None:
    pid = project["id"]
    # Non-members cannot see the project (404 to avoid leaking existence).
    assert client.get(f"{API}/projects/{pid}", headers=user_headers).status_code == 404
    assert client.get(f"{API}/projects", headers=user_headers).json() == []
    # Add as viewer: read but not write.
    r = client.post(
        f"{API}/projects/{pid}/members",
        json={"email": "member@example.com", "role": "viewer"},
        headers=admin_headers,
    )
    assert r.status_code == 201
    assert client.get(f"{API}/projects/{pid}", headers=user_headers).json()["my_role"] == "viewer"
    assert (
        client.patch(f"{API}/projects/{pid}", json={"team": "x"}, headers=user_headers).status_code
        == 403
    )
    assert (
        client.post(
            f"{API}/projects/{pid}/scans", json={"scan_type": "dependency"}, headers=user_headers
        ).status_code
        == 403
    )
    # Promote to maintainer: can update + scan, but not manage members or delete.
    client.post(
        f"{API}/projects/{pid}/members",
        json={"email": "member@example.com", "role": "maintainer"},
        headers=admin_headers,
    )
    r = client.patch(
        f"{API}/projects/{pid}",
        json={"team": "Core", "branches": ["release/1.x"]},
        headers=user_headers,
    )
    assert r.status_code == 200 and r.json()["branches"] == ["release/1.x"]
    assert (
        client.post(
            f"{API}/projects/{pid}/members",
            json={"email": "admin@example.com", "role": "viewer"},
            headers=user_headers,
        ).status_code
        == 403
    )
    assert client.delete(f"{API}/projects/{pid}", headers=user_headers).status_code == 403
    members = client.get(f"{API}/projects/{pid}/members", headers=user_headers).json()
    assert {m["role"] for m in members} == {"owner", "maintainer"}
    # Owner role cannot be granted via membership.
    assert (
        client.post(
            f"{API}/projects/{pid}/members",
            json={"email": "member@example.com", "role": "owner"},
            headers=admin_headers,
        ).status_code
        == 422
    )
    uid = next(m["user_id"] for m in members if m["role"] == "maintainer")
    assert (
        client.delete(f"{API}/projects/{pid}/members/{uid}", headers=admin_headers).status_code
        == 204
    )
    assert client.get(f"{API}/projects/{pid}", headers=user_headers).status_code == 404


def test_member_errors(client: Any, admin_headers: dict, project: dict) -> None:
    pid = project["id"]
    assert (
        client.post(
            f"{API}/projects/{pid}/members",
            json={"email": "ghost@example.com"},
            headers=admin_headers,
        ).status_code
        == 404
    )
    assert (
        client.post(
            f"{API}/projects/{pid}/members",
            json={"email": "admin@example.com"},
            headers=admin_headers,
        ).status_code
        == 400
    )
    assert (
        client.delete(f"{API}/projects/{pid}/members/999", headers=admin_headers).status_code == 404
    )


def test_delete_project_is_audited(
    client: Any, admin_headers: dict, project: dict, db: Any
) -> None:
    assert (
        client.delete(f"{API}/projects/{project['id']}", headers=admin_headers).status_code == 204
    )
    assert client.get(f"{API}/projects/{project['id']}", headers=admin_headers).status_code == 404
    actions = {a.action for a in db.query(AuditLog)}
    assert {"project.create", "project.delete"} <= actions


# ----------------------------------------------------------------------------- credentials


# Built at runtime so no realistic token literal appears in source (push protection).
TOKEN = "github_pat_" + "11" + "A" * 40 + "6789"


def test_github_token_is_encrypted_and_never_returned(
    client: Any, admin_headers: dict, project: dict, db: Any
) -> None:
    pid = project["id"]
    status = client.get(f"{API}/projects/{pid}/credentials/github", headers=admin_headers).json()
    assert status["configured"] is False
    r = client.put(
        f"{API}/projects/{pid}/credentials/github", json={"token": TOKEN}, headers=admin_headers
    )
    assert r.status_code == 200
    assert TOKEN not in r.text
    assert r.json()["token_hint"] == "****6789"
    stored = db.query(IntegrationCredential).one()
    assert TOKEN not in stored.encrypted_token
    audit = db.query(AuditLog).filter(AuditLog.action == "credential.set").one()
    assert TOKEN not in str(audit.details)
    status = client.get(f"{API}/projects/{pid}/credentials/github", headers=admin_headers).json()
    assert status["configured"] is True and TOKEN not in str(status)
    assert (
        client.delete(f"{API}/projects/{pid}/credentials/github", headers=admin_headers).status_code
        == 204
    )
    assert (
        client.delete(f"{API}/projects/{pid}/credentials/github", headers=admin_headers).status_code
        == 404
    )


def test_github_token_rejected_when_repo_not_accessible(
    client: Any, admin_headers: dict, project: dict
) -> None:
    class Denying(MockGitHubActionsAdapter):
        def check_repo_access(self, owner: str, repo: str, token: str | None) -> RepoAccess:
            raise AdapterError("GitHub API denied access (HTTP 401)")

    class NoRead(MockGitHubActionsAdapter):
        def check_repo_access(self, owner: str, repo: str, token: str | None) -> RepoAccess:
            return RepoAccess(full_name="x", private=True, can_read=False)

    registry.override("ci", Denying())
    r = client.put(
        f"{API}/projects/{project['id']}/credentials/github",
        json={"token": TOKEN},
        headers=admin_headers,
    )
    assert r.status_code == 400 and TOKEN not in r.text
    registry.override("ci", NoRead())
    r = client.put(
        f"{API}/projects/{project['id']}/credentials/github",
        json={"token": TOKEN},
        headers=admin_headers,
    )
    assert r.status_code == 400
    bad = client.put(
        f"{API}/projects/{project['id']}/credentials/github",
        json={"token": "short"},
        headers=admin_headers,
    )
    assert bad.status_code == 422


def test_health_and_settings(client: Any, admin_headers: dict) -> None:
    assert client.get(f"{API}/health").json() == {"status": "ok"}
    assert client.get(f"{API}/health/ready").json()["database"] == "ok"
    r = client.get(f"{API}/settings/integrations", headers=admin_headers)
    body = r.json()
    assert {i["mode"] for i in body["integrations"]} == {"mock"}
    assert body["background_processing"].startswith("eager")
    assert r.headers["X-Content-Type-Options"] == "nosniff"
    assert r.headers["X-Frame-Options"] == "DENY"
