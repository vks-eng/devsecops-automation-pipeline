"""Normalised data structures shared by all scanner parsers."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

SEVERITIES = ("critical", "high", "medium", "low", "info")


class ParseError(ValueError):
    """Raised when scanner output is malformed."""


@dataclass(slots=True)
class ParsedFinding:
    category: str
    severity: str
    rule_id: str
    title: str
    description: str = ""
    component: str = ""
    finding_type: str = "vulnerability"
    installed_version: str | None = None
    fixed_version: str | None = None
    file_path: str | None = None
    line: int | None = None
    reference_url: str | None = None
    recommendation: str = ""


@dataclass(slots=True)
class ParsedDependency:
    name: str
    version: str
    ecosystem: str = "pypi"
    vulnerability_count: int = 0


@dataclass(slots=True)
class ParsedScan:
    findings: list[ParsedFinding] = field(default_factory=list)
    dependencies: list[ParsedDependency] = field(default_factory=list)
    quality_gate_status: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def severity_counts(self) -> dict[str, int]:
        counter = Counter(f.severity for f in self.findings)
        return {sev: counter.get(sev, 0) for sev in SEVERITIES}


@dataclass(slots=True)
class ParsedPipelineRun:
    external_id: str
    workflow_name: str
    branch: str
    commit_sha: str
    event: str
    status: str
    conclusion: str | None
    actor: str
    html_url: str
    started_at: datetime | None
    completed_at: datetime | None

    @property
    def duration_seconds(self) -> int | None:
        if self.started_at and self.completed_at:
            return max(0, int((self.completed_at - self.started_at).total_seconds()))
        return None


def truncate(value: Any, limit: int) -> str:
    text = "" if value is None else str(value)
    return text if len(text) <= limit else text[: limit - 1] + "…"


def parse_iso8601(value: Any) -> datetime | None:
    if not value or not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
