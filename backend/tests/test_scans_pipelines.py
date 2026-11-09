from __future__ import annotations

import json
from typing import Any

import pytest

from app.adapters import registry
from app.adapters.base import AdapterError
from app.adapters.trivy import MockTrivyAdapter
from app.core.security import compute_github_signature
from app.models import AuditLog, Notification, PipelineRun, Scan
from tests.conftest import API, load_fixture

# ----------------------------------------------------------------------------- scans


@pytest.mark.parametrize(
    ("scan_type", "target"),
    [
        ("container", "ghcr.io/acme-demo/payments-api:1.8.2"),
        ("dependency", "main"),
        ("code_quality", "develop"),
        ("container", None),
        ("dependency", None),
    ],
)
def test_trigger_scan_completes_in_eager_mode(
    client: Any, admin_headers: dict, project: dict, scan_type: str, target: str | None
) -> None:
    r = client.post(
        f"{API}/projects/{project['id']}/scans",
        json={"scan_type": scan_type, "target": target},
        headers=admin_headers,
    )
    assert r.status_code == 202, r.text
    scan = client.get(f"{API}/scans/{r.json()['id']}", headers=admin_headers).json()
    assert scan["status"] == "completed", scan
    assert scan["adapter_mode"] == "mock"
    assert scan["summary"]["total"] >= 0
    assert scan["project_name"] == "Payments API"


def test_container_scan_records_findings_and_image_metadata(
    client: Any, admin_headers: dict, project: dict
) -> None:
    r = client.post(
        f"{API}/projects/{project['id']}/scans",
        json={"scan_type": "container", "target": "python:3.11-slim"},
        headers=admin_headers,
    )
    scan = client.get(f"{API}/scans/{r.json()['id']}", headers=admin_headers).json()
    assert scan["metadata"]["image"]["digest"].startswith("sha256:")
    findings = client.get(
        f"{API}/findings", params={"scan_id": scan["id"], "limit": 500}, headers=admin_headers
    ).json()
    assert findings["total"] == scan["summary"]["total"] + scan["summary"]["code_smells"]
    severities = [f["severity"] for f in findings["items"]]
    order = ["critical", "high", "medium", "low", "info"]
    assert severities == sorted(severities, key=order.index)


def test_dependency_scan_builds_inventory(client: Any, admin_headers: dict, project: dict) -> None:
    client.post(
        f"{API}/projects/{project['id']}/scans",
        json={"scan_type": "dependency"},
        headers=admin_headers,
    )
    inventory = client.get(
        f"{API}/dependencies", params={"project_id": project["id"]}, headers=admin_headers
    ).json()
    assert len(inventory) >= 9
    vulnerable = client.get(
        f"{API}/dependencies", params={"vulnerable_only": True}, headers=admin_headers
    ).json()
    assert all(d["vulnerable"] for d in vulnerable)


@pytest.mark.parametrize(
    ("body", "fragment"),
    [
        ({"scan_type": "container", "target": "docker.io/someone/else:latest"}, "not registered"),
        ({"scan_type": "container", "target": "nginx;id"}, "valid"),
        ({"scan_type": "dependency", "target": "feature/unknown"}, "not configured"),
        ({"scan_type": "dependency", "target": "--upload-pack=evil"}, "invalid"),
    ],
)
def test_scans_only_allowed_for_registered_targets(
    client: Any, admin_headers: dict, project: dict, body: dict, fragment: str, db: Any
) -> None:
    r = client.post(f"{API}/projects/{project['id']}/scans", json=body, headers=admin_headers)
    assert r.status_code == 422
    assert fragment in r.json()["detail"]
    denied = (
        db.query(AuditLog)
        .filter(AuditLog.action == "scan.trigger", AuditLog.outcome == "denied")
        .count()
    )
    assert denied == 1


def test_scan_requires_config(client: Any, admin_headers: dict) -> None:
    r = client.post(
        f"{API}/projects",
        json={"name": "Bare", "repo_url": "https://github.com/acme/bare"},
        headers=admin_headers,
    )
    pid = r.json()["id"]
    assert (
        client.post(
            f"{API}/projects/{pid}/scans", json={"scan_type": "code_quality"}, headers=admin_headers
        ).status_code
        == 422
    )
    assert (
        client.post(
            f"{API}/projects/{pid}/scans", json={"scan_type": "container"}, headers=admin_headers
        ).status_code
        == 422
    )
    client.patch(
        f"{API}/projects/{pid}",
        json={"scan_config": {"requirements_path": "requirements.txt", "enable_dependency": False}},
        headers=admin_headers,
    )
    r = client.post(
        f"{API}/projects/{pid}/scans", json={"scan_type": "dependency"}, headers=admin_headers
    )
    assert r.status_code == 400


def test_failed_scan_is_recorded_and_notified(
    client: Any, admin_headers: dict, project: dict, db: Any
) -> None:
    class Broken(MockTrivyAdapter):
        def scan_image(self, image_ref: str) -> dict:
            raise AdapterError("trivy exited with code 1: db download failed")

    registry.override("container", Broken())
    r = client.post(
        f"{API}/projects/{project['id']}/scans",
        json={"scan_type": "container"},
        headers=admin_headers,
    )
    scan = client.get(f"{API}/scans/{r.json()['id']}", headers=admin_headers).json()
    assert scan["status"] == "failed"
    assert "db download failed" in scan["error"]
    assert db.query(Notification).filter(Notification.type == "scan_failed").count() == 1


def test_import_reports(client: Any, admin_headers: dict, project: dict) -> None:
    pid = project["id"]
    r = client.post(
        f"{API}/projects/{pid}/scans/import",
        json={
            "scan_type": "container",
            "target": "ghcr.io/acme-demo/payments-api:1.8.2",
            "report": load_fixture("trivy_report.json"),
        },
        headers=admin_headers,
    )
    assert r.status_code == 201, r.text
    assert r.json()["summary"]["critical"] == 1
    assert r.json()["adapter_mode"] == "import"
    r = client.post(
        f"{API}/projects/{pid}/scans/import",
        json={"scan_type": "dependency", "report": load_fixture("pip_audit_report.json")},
        headers=admin_headers,
    )
    assert r.status_code == 201
    assert r.json()["summary"]["high"] == 1
    bad = client.post(
        f"{API}/projects/{pid}/scans/import",
        json={"scan_type": "dependency", "report": {"nope": []}},
        headers=admin_headers,
    )
    assert bad.status_code == 422
    unregistered = client.post(
        f"{API}/projects/{pid}/scans/import",
        json={"scan_type": "container", "target": "evil/image:1", "report": {}},
        headers=admin_headers,
    )
    assert unregistered.status_code == 422


def test_rescan_replaces_open_findings(client: Any, admin_headers: dict, project: dict) -> None:
    pid = project["id"]
    for _ in range(2):
        client.post(
            f"{API}/projects/{pid}/scans/import",
            json={
                "scan_type": "container",
                "target": "python:3.11-slim",
                "report": load_fixture("trivy_report.json"),
            },
            headers=admin_headers,
        )
    findings = client.get(
        f"{API}/findings", params={"category": "container"}, headers=admin_headers
    ).json()
    assert findings["total"] == 7  # latest scan only
    all_findings = client.get(
        f"{API}/findings",
        params={"category": "container", "latest_only": False},
        headers=admin_headers,
    ).json()
    assert all_findings["total"] == 14
    search = client.get(f"{API}/findings", params={"q": "gunicorn"}, headers=admin_headers).json()
    assert search["total"] == 1
    crit = client.get(
        f"{API}/findings", params={"severity": "critical"}, headers=admin_headers
    ).json()
    assert {f["severity"] for f in crit["items"]} == {"critical"}
    summary = client.get(f"{API}/findings/summary", headers=admin_headers).json()
    assert summary["by_category"]["container"]["critical"] == 1


def test_critical_findings_trigger_notifications(
    client: Any, admin_headers: dict, project: dict, user_headers: dict
) -> None:
    client.post(
        f"{API}/projects/{project['id']}/members",
        json={"email": "member@example.com", "role": "viewer"},
        headers=admin_headers,
    )
    client.post(
        f"{API}/projects/{project['id']}/scans/import",
        json={
            "scan_type": "container",
            "target": "python:3.11-slim",
            "report": load_fixture("trivy_report.json"),
        },
        headers=admin_headers,
    )
    for headers in (admin_headers, user_headers):
        notes = client.get(f"{API}/notifications", headers=headers).json()
        types = {n["type"] for n in notes}
        assert {"scan_completed", "critical_vulnerability"} <= types
    count = client.get(f"{API}/notifications/unread-count", headers=user_headers).json()
    assert count["unread"] == 2
    nid = client.get(f"{API}/notifications", headers=user_headers).json()[0]["id"]
    assert (
        client.post(f"{API}/notifications/{nid}/read", headers=user_headers).json()["read_at"]
        is not None
    )
    # Users cannot read other users' notifications.
    assert client.post(f"{API}/notifications/{nid}/read", headers=admin_headers).status_code == 404
    assert client.post(f"{API}/notifications/read-all", headers=user_headers).json()["updated"] == 1
    assert (
        client.get(
            f"{API}/notifications", params={"unread_only": True}, headers=user_headers
        ).json()
        == []
    )


def test_scan_listing_is_scoped(
    client: Any, admin_headers: dict, user_headers: dict, project: dict
) -> None:
    client.post(
        f"{API}/projects/{project['id']}/scans",
        json={"scan_type": "dependency"},
        headers=admin_headers,
    )
    assert len(client.get(f"{API}/scans", headers=admin_headers).json()) == 1
    assert client.get(f"{API}/scans", headers=user_headers).json() == []
    sid = client.get(f"{API}/scans", headers=admin_headers).json()[0]["id"]
    assert client.get(f"{API}/scans/{sid}", headers=user_headers).status_code == 404
    assert client.get(f"{API}/scans/99999", headers=admin_headers).status_code == 404
    assert client.get(f"{API}/findings", headers=user_headers).json()["total"] == 0
    history = client.get(
        f"{API}/projects/{project['id']}/scans",
        params={"scan_type": "dependency"},
        headers=admin_headers,
    ).json()
    assert len(history) == 1


# ----------------------------------------------------------------------------- pipelines


def test_pipeline_sync_and_stats(client: Any, admin_headers: dict, project: dict, db: Any) -> None:
    pid = project["id"]
    r = client.post(f"{API}/projects/{pid}/pipelines/sync", headers=admin_headers)
    assert r.status_code == 200 and r.json()["synced"] == 30
    # Idempotent: same run IDs are upserted, not duplicated.
    client.post(f"{API}/projects/{pid}/pipelines/sync", headers=admin_headers)
    assert db.query(PipelineRun).count() == 30
    runs = client.get(f"{API}/pipelines/runs", params={"limit": 5}, headers=admin_headers).json()
    assert runs["total"] == 30 and len(runs["items"]) == 5
    stats = client.get(f"{API}/pipelines/stats", headers=admin_headers).json()
    assert stats["total_runs"] > 0
    assert 0 <= stats["success_rate"] <= 1
    failures = db.query(PipelineRun).filter(PipelineRun.conclusion == "failure").count()
    notes = db.query(Notification).filter(Notification.type == "pipeline_failure").count()
    assert notes == failures


def test_pipeline_sync_adapter_error(client: Any, admin_headers: dict, project: dict) -> None:
    class Down:
        mode = "real"

        def list_workflow_runs(self, *a: Any, **k: Any) -> dict:
            raise AdapterError("GitHub API error (HTTP 502)")

    registry.override("ci", Down())
    r = client.post(f"{API}/projects/{project['id']}/pipelines/sync", headers=admin_headers)
    assert r.status_code == 502


# ----------------------------------------------------------------------------- webhooks


def _signed(body: bytes, secret: str = "test-webhook-secret") -> dict[str, str]:
    return {
        "X-Hub-Signature-256": compute_github_signature(secret, body),
        "X-GitHub-Event": "workflow_run",
        "X-GitHub-Delivery": "d-1",
        "Content-Type": "application/json",
    }


def test_webhook_valid_signature_creates_run_and_alert(client: Any, project: dict, db: Any) -> None:
    body = json.dumps(load_fixture("github_workflow_run_event.json")).encode()
    r = client.post(f"{API}/webhooks/github", content=body, headers=_signed(body))
    assert r.status_code == 202 and r.json()["status"] == "processed"
    run = db.query(PipelineRun).one()
    assert run.source == "webhook" and run.conclusion == "failure"
    assert run.duration_seconds == 339
    assert db.query(Notification).filter(Notification.type == "pipeline_failure").count() == 1
    # Redelivery of the same event does not create duplicates or new alerts.
    client.post(f"{API}/webhooks/github", content=body, headers=_signed(body))
    assert db.query(PipelineRun).count() == 1
    assert db.query(Notification).filter(Notification.type == "pipeline_failure").count() == 1


@pytest.mark.parametrize(
    "headers",
    [
        {},
        {"X-Hub-Signature-256": "sha256=" + "0" * 64},
        {"X-Hub-Signature-256": "sha1=abc"},
        {"X-Hub-Signature-256": compute_github_signature("wrong-secret", b"{}")},
    ],
)
def test_webhook_rejects_bad_signatures(client: Any, project: dict, db: Any, headers: dict) -> None:
    body = json.dumps(load_fixture("github_workflow_run_event.json")).encode()
    r = client.post(
        f"{API}/webhooks/github",
        content=body,
        headers={"X-GitHub-Event": "workflow_run", **headers},
    )
    assert r.status_code == 401
    assert db.query(PipelineRun).count() == 0
    assert db.query(AuditLog).filter(AuditLog.outcome == "rejected").count() == 1


def test_webhook_tampered_body_rejected(client: Any, project: dict) -> None:
    body = json.dumps(load_fixture("github_workflow_run_event.json")).encode()
    headers = _signed(body)
    tampered = body.replace(b'"failure"', b'"success"')
    assert (
        client.post(f"{API}/webhooks/github", content=tampered, headers=headers).status_code == 401
    )


def test_webhook_ping_unregistered_and_other_events(client: Any, project: dict, db: Any) -> None:
    ping = b'{"zen": "hi"}'
    r = client.post(
        f"{API}/webhooks/github", content=ping, headers={**_signed(ping), "X-GitHub-Event": "ping"}
    )
    assert r.json() == {"status": "pong"}
    push = b'{"ref": "refs/heads/main"}'
    r = client.post(
        f"{API}/webhooks/github", content=push, headers={**_signed(push), "X-GitHub-Event": "push"}
    )
    assert r.json()["status"] == "ignored"
    event = load_fixture("github_workflow_run_event.json")
    event["repository"]["full_name"] = "someone/else"
    body = json.dumps(event).encode()
    r = client.post(f"{API}/webhooks/github", content=body, headers=_signed(body))
    assert r.json()["status"] == "ignored_unregistered_repository"
    assert db.query(PipelineRun).count() == 0
    bad = b"not json"
    assert (
        client.post(f"{API}/webhooks/github", content=bad, headers=_signed(bad)).status_code == 400
    )


def test_webhook_disabled_without_secret(client: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.config import get_settings

    monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", "")
    get_settings.cache_clear()
    try:
        r = client.post(f"{API}/webhooks/github", content=b"{}", headers=_signed(b"{}"))
        assert r.status_code == 503
    finally:
        monkeypatch.undo()
        get_settings.cache_clear()


def test_eager_worker_tasks(project: dict, db: Any) -> None:
    from app.worker.tasks import sync_all_pipelines

    assert sync_all_pipelines.delay().get() == 30
    assert db.query(Scan).count() == 0
