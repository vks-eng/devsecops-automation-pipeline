"""Security score methodology (see docs/security-score.md).

    score = clamp(100 - vulnerability_penalty - quality_gate_penalty - pipeline_penalty, 0, 100)

* vulnerability_penalty = min(60, 10*critical + 5*high + 2*medium + 0.5*low)
  counted over open findings of the *latest* completed scan per (scan type, target);
  SonarQube code smells are excluded (they affect maintainability, not security).
* quality_gate_penalty  = 15 if the latest quality gate failed, 5 if it warned, else 0.
* pipeline_penalty      = 15 * (1 - success_rate) over the last 20 completed runs
  (0 when there is no pipeline history yet).

Grades: A >= 90, B >= 80, C >= 70, D >= 60, otherwise F.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Finding, PipelineRun, Project, Scan, ScanStatus

WEIGHTS = {"critical": 10.0, "high": 5.0, "medium": 2.0, "low": 0.5, "info": 0.0}
VULN_PENALTY_CAP = 60.0
GATE_PENALTY = {"failed": 15.0, "warning": 5.0}
PIPELINE_PENALTY_MAX = 15.0
PIPELINE_WINDOW = 20


@dataclass(slots=True)
class ScoreResult:
    score: float
    grade: str
    vulnerability_penalty: float
    quality_gate_penalty: float
    pipeline_penalty: float

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def grade_for(score: float) -> str:
    for threshold, grade in ((90, "A"), (80, "B"), (70, "C"), (60, "D")):
        if score >= threshold:
            return grade
    return "F"


def compute_score(
    counts: dict[str, int], quality_gate: str | None, success_rate: float | None
) -> ScoreResult:
    vuln = min(VULN_PENALTY_CAP, sum(WEIGHTS.get(s, 0) * n for s, n in counts.items()))
    gate = GATE_PENALTY.get(quality_gate or "", 0.0)
    pipeline = 0.0 if success_rate is None else PIPELINE_PENALTY_MAX * (1 - success_rate)
    score = round(max(0.0, min(100.0, 100 - vuln - gate - pipeline)), 1)
    return ScoreResult(score, grade_for(score), round(vuln, 1), gate, round(pipeline, 1))


def latest_scans(db: Session, project_ids: list[int]) -> list[Scan]:
    """Latest completed scan per (project, scan type, target)."""
    if not project_ids:
        return []
    ranked = (
        select(
            Scan.id,
            func.row_number()
            .over(
                partition_by=(Scan.project_id, Scan.scan_type, Scan.target),
                order_by=(Scan.completed_at.desc(), Scan.id.desc()),
            )
            .label("rn"),
        )
        .where(Scan.project_id.in_(project_ids), Scan.status == ScanStatus.COMPLETED.value)
        .subquery()
    )
    return list(
        db.scalars(select(Scan).join(ranked, ranked.c.id == Scan.id).where(ranked.c.rn == 1))
    )


def security_counts(db: Session, scan_ids: list[int]) -> dict[str, int]:
    counts = dict.fromkeys(WEIGHTS, 0)
    if not scan_ids:
        return counts
    rows = db.execute(
        select(Finding.severity, func.count())
        .where(Finding.scan_id.in_(scan_ids), Finding.finding_type != "code_smell")
        .group_by(Finding.severity)
    )
    for severity, n in rows:
        counts[severity] = counts.get(severity, 0) + int(n)
    return counts


def pipeline_success_rate(db: Session, project_id: int) -> float | None:
    conclusions = list(
        db.scalars(
            select(PipelineRun.conclusion)
            .where(
                PipelineRun.project_id == project_id,
                PipelineRun.status == "completed",
                PipelineRun.conclusion.in_(["success", "failure", "timed_out"]),
            )
            .order_by(PipelineRun.started_at.desc().nulls_last())
            .limit(PIPELINE_WINDOW)
        )
    )
    if not conclusions:
        return None
    return sum(1 for c in conclusions if c == "success") / len(conclusions)


def project_security_overview(db: Session, project: Project) -> dict[str, Any]:
    scans = latest_scans(db, [project.id])
    counts = security_counts(db, [s.id for s in scans])
    code_scans = sorted(
        (s for s in scans if s.scan_type == "code_quality"),
        key=lambda s: s.completed_at or s.created_at,
        reverse=True,
    )
    gate = code_scans[0].quality_gate_status if code_scans else None
    rate = pipeline_success_rate(db, project.id)
    result = compute_score(counts, gate, rate)
    last_scan = max((s.completed_at for s in scans if s.completed_at), default=None)
    return {
        "project_id": project.id,
        "project_name": project.name,
        "slug": project.slug,
        "team": project.team,
        "counts": counts,
        "quality_gate_status": gate,
        "pipeline_success_rate": None if rate is None else round(rate, 3),
        "last_scan_at": last_scan,
        **result.as_dict(),
    }
