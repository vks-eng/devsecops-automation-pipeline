from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter
from sqlalchemy import func, select

from app.api.deps import CurrentUser, DbSession
from app.models import SEVERITY_ORDER, PipelineRun, Project, Scan
from app.services.access import accessible_project_ids
from app.services.scoring import project_security_overview

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard/summary")
def dashboard_summary(db: DbSession, user: CurrentUser) -> dict[str, Any]:
    ids = accessible_project_ids(db, user)
    projects = list(
        db.scalars(select(Project).where(Project.id.in_(ids or [-1])).order_by(Project.name))
    )
    overviews = [project_security_overview(db, p) for p in projects]
    totals = {s: sum(o["counts"].get(s, 0) for o in overviews) for s in SEVERITY_ORDER}

    since = datetime.now(UTC) - timedelta(days=30)
    run_rows = db.execute(
        select(PipelineRun.conclusion, func.count())
        .where(
            PipelineRun.project_id.in_(ids or [-1]),
            PipelineRun.started_at >= since,
            PipelineRun.status == "completed",
        )
        .group_by(PipelineRun.conclusion)
    ).all()
    by_conclusion = {c or "unknown": int(n) for c, n in run_rows}
    ok = by_conclusion.get("success", 0)
    bad = by_conclusion.get("failure", 0) + by_conclusion.get("timed_out", 0)

    recent_runs = list(
        db.scalars(
            select(PipelineRun)
            .where(PipelineRun.project_id.in_(ids or [-1]))
            .order_by(PipelineRun.started_at.desc().nulls_last())
            .limit(10)
        )
    )
    recent_scans = list(
        db.scalars(
            select(Scan)
            .where(Scan.project_id.in_(ids or [-1]))
            .order_by(Scan.created_at.desc())
            .limit(10)
        )
    )
    names = {p.id: p.name for p in projects}
    scans_total = (
        db.scalar(select(func.count()).select_from(Scan).where(Scan.project_id.in_(ids or [-1])))
        or 0
    )
    scored = [o["score"] for o in overviews]
    return {
        "total_projects": len(projects),
        "total_scans": scans_total,
        "average_score": round(sum(scored) / len(scored), 1) if scored else None,
        "vulnerability_totals": totals,
        "pipeline": {
            "window_days": 30,
            "by_conclusion": by_conclusion,
            "success_rate": round(ok / (ok + bad), 3) if ok + bad else None,
        },
        "quality_gates": {
            g: sum(1 for o in overviews if (o["quality_gate_status"] or "none") == g)
            for g in ("passed", "failed", "warning", "none")
        },
        "projects": overviews,
        "recent_runs": [
            {
                "id": r.id,
                "project_id": r.project_id,
                "project_name": names.get(r.project_id),
                "workflow_name": r.workflow_name,
                "branch": r.branch,
                "status": r.status,
                "conclusion": r.conclusion,
                "started_at": r.started_at,
                "duration_seconds": r.duration_seconds,
                "html_url": r.html_url,
            }
            for r in recent_runs
        ],
        "recent_scans": [
            {
                "id": s.id,
                "project_id": s.project_id,
                "project_name": names.get(s.project_id),
                "scan_type": s.scan_type,
                "target": s.target,
                "status": s.status,
                "summary": s.summary,
                "created_at": s.created_at,
                "completed_at": s.completed_at,
            }
            for s in recent_scans
        ],
    }


@router.get("/code-quality/overview")
def code_quality_overview(db: DbSession, user: CurrentUser) -> list[dict[str, Any]]:
    ids = accessible_project_ids(db, user)
    projects = list(
        db.scalars(select(Project).where(Project.id.in_(ids or [-1])).order_by(Project.name))
    )
    out = []
    for p in projects:
        scan = db.scalar(
            select(Scan)
            .where(
                Scan.project_id == p.id,
                Scan.scan_type == "code_quality",
                Scan.status == "completed",
            )
            .order_by(Scan.completed_at.desc())
            .limit(1)
        )
        meta = (scan.metadata_json or {}) if scan else {}
        out.append(
            {
                "project_id": p.id,
                "project_name": p.name,
                "sonar_project_key": p.sonar_project_key,
                "scan_id": scan.id if scan else None,
                "quality_gate_status": scan.quality_gate_status if scan else None,
                "completed_at": scan.completed_at if scan else None,
                "adapter_mode": scan.adapter_mode if scan else None,
                "summary": scan.summary if scan else {},
                "by_type": meta.get("by_type", {}),
                "measures": meta.get("measures", {}),
                "conditions": meta.get("quality_gate_conditions", []),
            }
        )
    return out
