"""Unit tests: security score methodology, report builders and notification rules."""

from __future__ import annotations

import csv
import io
from types import SimpleNamespace
from typing import Any

import pytest

from app.models import NotificationType
from app.services import notifications
from app.services.reporting import (
    CSV_COLUMNS,
    remediation_recommendations,
    report_to_csv,
    report_to_html,
    rows_to_csv,
)
from app.services.scoring import compute_score, grade_for

ZERO = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}


# ----------------------------------------------------------------------------- score methodology


@pytest.mark.parametrize(
    ("counts", "gate", "rate", "score", "grade"),
    [
        ({}, None, None, 100.0, "A"),  # nothing known yet
        ({"info": 50}, "passed", 1.0, 100.0, "A"),  # info never penalised
        ({"low": 4}, None, None, 98.0, "A"),  # 0.5 per low
        ({"medium": 5}, None, None, 90.0, "A"),  # boundary: exactly 90 -> A
        ({"medium": 5, "low": 1}, None, None, 89.5, "B"),  # just below -> B
        ({"high": 2}, None, None, 90.0, "A"),
        ({"critical": 1}, None, None, 90.0, "A"),
        ({"critical": 1, "high": 1}, None, None, 85.0, "B"),
        ({"critical": 3}, None, None, 70.0, "C"),
        ({"critical": 4}, None, None, 60.0, "D"),
        ({"critical": 4, "low": 1}, None, None, 59.5, "F"),
        ({"critical": 100}, None, None, 40.0, "F"),  # vulnerability penalty capped at 60
        ({}, "failed", None, 85.0, "B"),
        ({}, "warning", None, 95.0, "A"),
        ({}, "none", None, 100.0, "A"),
        ({}, None, 0.0, 85.0, "B"),  # all pipelines failing -> -15
        ({}, None, 0.5, 92.5, "A"),
        ({"critical": 100}, "failed", 0.0, 10.0, "F"),  # worst case floor
    ],
)
def test_score_table(counts: dict, gate: str | None, rate: float | None, score: float,
                     grade: str) -> None:
    result = compute_score({**ZERO, **counts}, gate, rate)
    assert result.score == score
    assert result.grade == grade
    assert 0 <= result.score <= 100


def test_score_breakdown_is_reported() -> None:
    result = compute_score({**ZERO, "critical": 2, "high": 1}, "failed", 0.8)
    assert result.as_dict() == {
        "score": 55.0,
        "grade": "F",
        "vulnerability_penalty": 25.0,
        "quality_gate_penalty": 15.0,
        "pipeline_penalty": 3.0,
    }


@pytest.mark.parametrize(("score", "grade"), [(100, "A"), (90, "A"), (89.9, "B"), (80, "B"),
                                              (79.9, "C"), (70, "C"), (60, "D"), (59.9, "F"),
                                              (0, "F")])
def test_grade_boundaries(score: float, grade: str) -> None:
    assert grade_for(score) == grade


# ----------------------------------------------------------------------------- report builders


def _finding(**kw: Any) -> SimpleNamespace:
    base = dict(category="container", finding_type="vulnerability", severity="high",
                component="openssl", rule_id="CVE-1", fixed_version=None,
                recommendation="Upgrade openssl")
    return SimpleNamespace(**{**base, **kw})


def test_recommendations_grouped_and_ranked_by_risk() -> None:
    findings = [
        _finding(component="openssl", severity="high", rule_id="CVE-1", fixed_version="3.0.2"),
        _finding(component="openssl", severity="critical", rule_id="CVE-2",
                 recommendation="Upgrade openssl now", fixed_version="3.0.3"),
        _finding(component="zlib", severity="medium", rule_id="CVE-3"),
        _finding(component="app.py", category="code_quality", finding_type="code_smell",
                 severity="critical", rule_id="python:S1"),
    ]
    recs = remediation_recommendations(findings)  # type: ignore[arg-type]
    assert [r["component"] for r in recs] == ["openssl", "zlib"]  # code smell excluded
    top = recs[0]
    assert top["highest_severity"] == "critical"
    assert top["risk_reduction"] == 15.0
    assert top["fixed_versions"] == ["3.0.2", "3.0.3"]
    assert top["action"] == "Upgrade openssl now"
    assert top["finding_count"] == 2


def test_csv_export_neutralises_formula_injection() -> None:
    rows = [{"project": "p", "severity": "high", "title": "=HYPERLINK(\"http://evil\")",
             "component": "+cmd", "recommendation": "@SUM(A1)", "rule_id": "-1"}]
    text = report_to_csv(rows)
    parsed = list(csv.DictReader(io.StringIO(text)))
    assert list(parsed[0].keys()) == CSV_COLUMNS
    assert parsed[0]["title"].startswith("'=")
    assert parsed[0]["component"] == "'+cmd"
    assert parsed[0]["recommendation"] == "'@SUM(A1)"
    assert parsed[0]["rule_id"] == "'-1"
    assert rows_to_csv([]) == ""
    assert rows_to_csv([{"a": 1, "b": 2}]).splitlines() == ["a,b", "1,2"]


def test_html_report_escapes_untrusted_content() -> None:
    report = {
        "project": {"name": "<script>alert(1)</script>", "repository": "https://github.com/a/b",
                    "team": "t"},
        "generated_at": "2026-11-10",
        "security_score": {"score": 50.0, "grade": "F"},
        "quality_gate_status": "failed",
        "pipeline_success_rate": None,
        "severity_totals": {"critical": 1, "high": 0, "medium": 0, "low": 0, "info": 0},
        "recommendations": [{"highest_severity": "critical", "category": "container",
                             "component": "<img src=x onerror=1>", "finding_count": 1,
                             "action": "fix"}],
        "findings": [{"severity": "critical", "scan_type": "container", "rule_id": "CVE-1",
                      "title": "<b>bold</b>", "component": "x", "fixed_version": None}],
    }
    html = report_to_html(report)
    assert "<script>" not in html and "&lt;script&gt;" in html
    assert "<img" not in html and "<b>bold</b>" not in html
    assert "50.0 / 100" in html


# ----------------------------------------------------------------------------- notification rules


class _FakeDb:
    def __init__(self) -> None:
        self.added: list[Any] = []

    def add(self, obj: Any) -> None:
        self.added.append(obj)

    def flush(self) -> None:
        pass


def test_notifications_fan_out_and_external_channel_rules(monkeypatch: pytest.MonkeyPatch
                                                          ) -> None:
    from app.core.config import get_settings

    posted: list[dict[str, Any]] = []
    monkeypatch.setattr(notifications, "project_recipients", lambda db, p: [1, 2, 3])
    monkeypatch.setattr(notifications.httpx, "post",
                        lambda url, json, timeout: posted.append(json))
    monkeypatch.setenv("NOTIFICATION_WEBHOOK_URL", "https://hooks.example.com/alerts")
    get_settings.cache_clear()
    try:
        db = _FakeDb()
        project = SimpleNamespace(id=7, slug="payments-api")
        created = notifications.notify_project(
            db, project, NotificationType.SCAN_COMPLETED, "done", "msg"  # type: ignore[arg-type]
        )
        assert [n.user_id for n in created] == [1, 2, 3]
        assert posted == []  # scan-completed stays in-app only
        notifications.notify_project(
            db, project, NotificationType.CRITICAL_VULNERABILITY, "crit", "msg", "critical"  # type: ignore[arg-type]
        )
        assert posted == [{"event": "critical_vulnerability", "severity": "critical",
                           "project": "payments-api", "title": "crit", "message": "msg"}]
        # Plain-HTTP webhooks are refused in production.
        monkeypatch.setenv("NOTIFICATION_WEBHOOK_URL", "http://insecure.example.com")
        monkeypatch.setenv("ENVIRONMENT", "production")
        get_settings.cache_clear()
        notifications.notify_project(
            db, project, NotificationType.PIPELINE_FAILURE, "f", "m"  # type: ignore[arg-type]
        )
        assert len(posted) == 1
    finally:
        monkeypatch.undo()
        get_settings.cache_clear()
