"""Parsers for SonarQube Web API responses.

* ``GET /api/issues/search`` - issues (bugs, vulnerabilities, code smells)
* ``GET /api/qualitygates/project_status`` - quality gate status
* ``GET /api/measures/component`` - headline metrics (coverage, duplication, ...)
"""

from __future__ import annotations

from typing import Any

from app.parsers.common import ParsedFinding, ParsedScan, ParseError, truncate

# Legacy (<= 9.x) issue severities.
_LEGACY_SEVERITY = {
    "BLOCKER": "critical",
    "CRITICAL": "high",
    "MAJOR": "medium",
    "MINOR": "low",
    "INFO": "info",
}
# Clean Code "impacts" severities (10.x+).
_IMPACT_SEVERITY = {
    "BLOCKER": "critical",
    "HIGH": "high",
    "MEDIUM": "medium",
    "LOW": "low",
    "INFO": "info",
}
_TYPE_MAP = {"VULNERABILITY": "vulnerability", "BUG": "bug", "CODE_SMELL": "code_smell"}
_RANK = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}


def classify_sonar_severity(issue: dict[str, Any]) -> str:
    impacts = issue.get("impacts") or []
    mapped = [
        _IMPACT_SEVERITY[str(i.get("severity", "")).upper()]
        for i in impacts
        if isinstance(i, dict) and str(i.get("severity", "")).upper() in _IMPACT_SEVERITY
    ]
    if mapped:
        return min(mapped, key=_RANK.__getitem__)
    return _LEGACY_SEVERITY.get(str(issue.get("severity", "")).upper(), "info")


def _file_from_component(component: str) -> str | None:
    # Component keys look like "<projectKey>:<path/to/file.py>"
    return component.split(":", 1)[1] if ":" in component else None


def parse_sonar_issues(payload: dict[str, Any]) -> list[ParsedFinding]:
    if not isinstance(payload, dict) or not isinstance(payload.get("issues", []), list):
        raise ParseError("SonarQube issues payload must contain an 'issues' list")
    findings: list[ParsedFinding] = []
    for issue in payload.get("issues", []):
        if not isinstance(issue, dict):
            raise ParseError("SonarQube issues must be objects")
        if str(issue.get("status", "OPEN")).upper() in {"CLOSED", "RESOLVED"}:
            continue
        rule = str(issue.get("rule") or "unknown")
        component = str(issue.get("component") or "")
        issue_type = _TYPE_MAP.get(str(issue.get("type", "")).upper(), "code_smell")
        message = str(issue.get("message") or rule)
        effort = issue.get("effort")
        findings.append(
            ParsedFinding(
                category="code_quality",
                finding_type=issue_type,
                severity=classify_sonar_severity(issue),
                rule_id=truncate(rule, 200),
                title=truncate(message, 500),
                description=truncate(
                    f"{issue_type.replace('_', ' ').title()} reported by rule {rule}.", 4000
                ),
                component=truncate(component, 500),
                file_path=_file_from_component(component),
                line=issue.get("line") if isinstance(issue.get("line"), int) else None,
                recommendation=(
                    f"Review the guidance for rule {rule} in SonarQube and fix the flagged code"
                    + (f" (estimated effort: {effort})." if effort else ".")
                ),
            )
        )
    return findings


def parse_quality_gate(payload: dict[str, Any]) -> tuple[str, list[dict[str, Any]]]:
    if not isinstance(payload, dict) or not isinstance(payload.get("projectStatus"), dict):
        raise ParseError("Quality gate payload must contain 'projectStatus'")
    status_raw = str(payload["projectStatus"].get("status", "NONE")).upper()
    status = {"OK": "passed", "ERROR": "failed", "WARN": "warning"}.get(status_raw, "none")
    conditions = [
        {
            "metric": c.get("metricKey"),
            "status": c.get("status"),
            "actual": c.get("actualValue"),
            "threshold": c.get("errorThreshold"),
            "comparator": c.get("comparator"),
        }
        for c in payload["projectStatus"].get("conditions", []) or []
        if isinstance(c, dict)
    ]
    return status, conditions


def parse_measures(payload: dict[str, Any] | None) -> dict[str, str]:
    if not payload:
        return {}
    component = payload.get("component") or {}
    return {
        str(m.get("metric")): str(m.get("value"))
        for m in component.get("measures", [])
        if isinstance(m, dict) and "metric" in m and "value" in m
    }


def parse_sonar_results(
    issues_payload: dict[str, Any],
    gate_payload: dict[str, Any],
    measures_payload: dict[str, Any] | None = None,
) -> ParsedScan:
    parsed = ParsedScan(findings=parse_sonar_issues(issues_payload))
    status, conditions = parse_quality_gate(gate_payload)
    parsed.quality_gate_status = status
    parsed.metadata = {
        "quality_gate_conditions": conditions,
        "total_issues_reported": issues_payload.get("total", len(parsed.findings)),
        "measures": parse_measures(measures_payload),
        "by_type": {
            t: sum(1 for f in parsed.findings if f.finding_type == t)
            for t in ("bug", "vulnerability", "code_smell")
        },
    }
    return parsed
