from __future__ import annotations

import pytest

from app.parsers.common import ParseError
from app.parsers.github import parse_workflow_run, parse_workflow_runs
from app.parsers.pip_audit import classify_pip_audit_severity, parse_pip_audit_report
from app.parsers.sonarqube import (
    classify_sonar_severity,
    parse_quality_gate,
    parse_sonar_issues,
    parse_sonar_results,
)
from app.parsers.trivy import classify_trivy_severity, parse_trivy_report
from tests.conftest import load_fixture

# ----------------------------------------------------------------------------- Trivy


def test_trivy_parses_fixture_and_deduplicates() -> None:
    parsed = parse_trivy_report(load_fixture("trivy_report.json"))
    ids = [f.rule_id for f in parsed.findings]
    assert ids.count("CVE-2024-1135") == 1  # duplicate across paths removed
    assert len(parsed.findings) == 7
    assert parsed.severity_counts() == {"critical": 1, "high": 2, "medium": 2, "low": 1, "info": 1}
    assert parsed.metadata["os"] == "debian 12.5"
    assert parsed.metadata["artifact_name"] == "ghcr.io/acme-demo/payments-api:1.8.2"
    assert len(parsed.metadata["targets"]) == 3
    assert parsed.metadata["targets"][2]["vulnerabilities"] == 0


def test_trivy_finding_fields_and_recommendations() -> None:
    parsed = parse_trivy_report(load_fixture("trivy_report.json"))
    by_id = {f.rule_id: f for f in parsed.findings}
    glibc = by_id["CVE-2023-4911"]
    assert glibc.category == "container"
    assert glibc.component == "libc6"
    assert glibc.fixed_version == "2.36-9+deb12u3"
    assert "base image" in glibc.recommendation
    zlib = by_id["CVE-2023-45853"]
    assert zlib.fixed_version is None
    assert "No fixed version" in zlib.recommendation
    assert by_id["CVE-2024-1135"].recommendation.startswith(
        "Upgrade gunicorn from 21.2.0 to 22.0.0"
    )


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("CRITICAL", "critical"),
        ("HIGH", "high"),
        ("medium", "medium"),
        ("LOW", "low"),
        ("UNKNOWN", "info"),
        (None, "info"),
        ("weird", "info"),
    ],
)
def test_trivy_severity_classification(raw: str | None, expected: str) -> None:
    assert classify_trivy_severity(raw) == expected


def test_trivy_empty_and_invalid() -> None:
    assert parse_trivy_report({"SchemaVersion": 2, "Results": None}).findings == []
    with pytest.raises(ParseError):
        parse_trivy_report([])  # type: ignore[arg-type]
    with pytest.raises(ParseError):
        parse_trivy_report({"Results": {"oops": 1}})
    with pytest.raises(ParseError):
        parse_trivy_report({"Results": ["not-an-object"]})


# ----------------------------------------------------------------------------- pip-audit


def test_pip_audit_parses_fixture() -> None:
    parsed = parse_pip_audit_report(load_fixture("pip_audit_report.json"))
    assert len(parsed.dependencies) == 5
    assert len(parsed.findings) == 4
    assert parsed.metadata["vulnerable_dependency_count"] == 3
    assert parsed.metadata["skipped"][0]["name"] == "internal-sdk"
    req = next(f for f in parsed.findings if f.rule_id == "GHSA-j8r2-6x86-q33q")
    assert req.title == "GHSA-j8r2-6x86-q33q in requests 2.28.2 (CVE-2023-32681)"
    assert req.fixed_version == "2.31.0"
    assert req.reference_url == "https://osv.dev/vulnerability/GHSA-j8r2-6x86-q33q"
    assert req.severity == "medium"
    unfixed = next(f for f in parsed.findings if f.component == "legacy-crypto-helper")
    assert unfixed.severity == "high"
    assert unfixed.fixed_version is None
    assert "No fixed release" in unfixed.recommendation


def test_pip_audit_legacy_list_format_and_explicit_severity() -> None:
    parsed = parse_pip_audit_report(
        [
            {
                "name": "x",
                "version": "1",
                "vulns": [{"id": "PYSEC-1", "fix_versions": ["2"], "severity": "CRITICAL"}],
            }
        ]
    )
    assert parsed.findings[0].severity == "critical"
    assert classify_pip_audit_severity({"severity": "moderate"}) == "medium"


def test_pip_audit_invalid() -> None:
    with pytest.raises(ParseError):
        parse_pip_audit_report({"deps": []})
    with pytest.raises(ParseError):
        parse_pip_audit_report({"dependencies": [{"version": "1"}]})
    with pytest.raises(ParseError):
        parse_pip_audit_report("nope")  # type: ignore[arg-type]


# ----------------------------------------------------------------------------- SonarQube


def test_sonar_issues_and_quality_gate() -> None:
    parsed = parse_sonar_results(
        load_fixture("sonar_issues.json"),
        load_fixture("sonar_quality_gate.json"),
        load_fixture("sonar_measures.json"),
    )
    assert len(parsed.findings) == 4  # CLOSED issue skipped
    assert parsed.quality_gate_status == "failed"
    assert parsed.metadata["by_type"] == {"bug": 1, "vulnerability": 2, "code_smell": 1}
    assert parsed.metadata["measures"]["coverage"] == "64.3"
    assert parsed.metadata["quality_gate_conditions"][1]["metric"] == "new_coverage"
    sql = next(f for f in parsed.findings if f.rule_id == "python:S2077")
    assert sql.severity == "high"  # impacts HIGH wins over legacy CRITICAL->high
    assert sql.file_path == "app/repository.py"
    assert sql.line == 42
    assert "20min" in sql.recommendation
    secret = next(f for f in parsed.findings if f.rule_id == "python:S2068")
    assert secret.severity == "critical"
    bug = next(f for f in parsed.findings if f.finding_type == "bug")
    assert bug.severity == "medium"  # legacy MAJOR


@pytest.mark.parametrize(
    ("issue", "expected"),
    [
        ({"severity": "BLOCKER"}, "critical"),
        ({"severity": "CRITICAL"}, "high"),
        ({"severity": "MAJOR"}, "medium"),
        ({"severity": "MINOR"}, "low"),
        ({"severity": "INFO"}, "info"),
        ({"severity": "MINOR", "impacts": [{"severity": "LOW"}, {"severity": "HIGH"}]}, "high"),
        ({}, "info"),
    ],
)
def test_sonar_severity_mapping(issue: dict, expected: str) -> None:
    assert classify_sonar_severity(issue) == expected


def test_sonar_quality_gate_statuses_and_errors() -> None:
    assert parse_quality_gate({"projectStatus": {"status": "OK"}})[0] == "passed"
    assert parse_quality_gate({"projectStatus": {"status": "WARN"}})[0] == "warning"
    assert parse_quality_gate({"projectStatus": {"status": "NONE"}})[0] == "none"
    with pytest.raises(ParseError):
        parse_quality_gate({})
    with pytest.raises(ParseError):
        parse_sonar_issues({"issues": "bad"})


# ----------------------------------------------------------------------------- GitHub


def test_github_workflow_runs() -> None:
    runs = parse_workflow_runs(load_fixture("github_workflow_runs.json"))
    assert [r.conclusion for r in runs] == ["success", "failure", None]
    first = runs[0]
    assert first.external_id == "11223344551"
    assert first.duration_seconds == 445
    assert first.actor == "alice-dev"
    assert runs[2].completed_at is None
    assert runs[2].duration_seconds is None


def test_github_invalid_payloads() -> None:
    with pytest.raises(ParseError):
        parse_workflow_runs({"runs": []})
    with pytest.raises(ParseError):
        parse_workflow_run({"name": "no id"})
