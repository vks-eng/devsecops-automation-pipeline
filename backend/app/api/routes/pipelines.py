from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Query
from sqlalchemy import func, select

from app.api.deps import CurrentUser, DbSession
from app.models import PipelineRun, Project
from app.schemas import Page, PipelineRunOut
from app.services.access import accessible_project_ids

router = APIRouter(prefix="/pipelines", tags=["pipelines"])


@router.get("/runs", response_model=Page[PipelineRunOut])
def list_runs(
    db: DbSession,
    user: CurrentUser,
    project_id: int | None = None,
    conclusion: str | None = Query(None, pattern="^(success|failure|cancelled|timed_out|skipped)$"),
    branch: str | None = Query(None, max_length=200),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> Page[PipelineRunOut]:
    ids = accessible_project_ids(db, user)
    if project_id is not None:
        ids = [i for i in ids if i == project_id]
    stmt = select(PipelineRun).where(PipelineRun.project_id.in_(ids or [-1]))
    if conclusion:
        stmt = stmt.where(PipelineRun.conclusion == conclusion)
    if branch:
        stmt = stmt.where(PipelineRun.branch == branch)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = list(
        db.scalars(
            stmt.order_by(PipelineRun.started_at.desc().nulls_last(), PipelineRun.id.desc())
            .limit(limit)
            .offset(offset)
        )
    )
    names = dict(
        db.execute(
            select(Project.id, Project.name).where(
                Project.id.in_({r.project_id for r in rows} or {-1})
            )
        ).all()
    )
    items = []
    for r in rows:
        item = PipelineRunOut.model_validate(r)
        item.project_name = names.get(r.project_id)
        items.append(item)
    return Page[PipelineRunOut](items=items, total=total, limit=limit, offset=offset)


@router.get("/stats")
def pipeline_stats(
    db: DbSession,
    user: CurrentUser,
    days: int = Query(30, ge=1, le=365),
    project_id: int | None = None,
) -> dict[str, Any]:
    ids = accessible_project_ids(db, user)
    if project_id is not None:
        ids = [i for i in ids if i == project_id]
    since = datetime.now(UTC) - timedelta(days=days)
    runs = list(
        db.scalars(
            select(PipelineRun).where(
                PipelineRun.project_id.in_(ids or [-1]), PipelineRun.started_at >= since
            )
        )
    )
    completed = [r for r in runs if r.status == "completed"]
    success = sum(1 for r in completed if r.conclusion == "success")
    failed = sum(1 for r in completed if r.conclusion in ("failure", "timed_out"))
    durations = [r.duration_seconds for r in completed if r.duration_seconds]
    daily: dict[str, dict[str, int]] = {}
    for r in completed:
        if r.started_at is None:
            continue
        d = r.started_at.date().isoformat()
        bucket = daily.setdefault(d, {"success": 0, "failure": 0, "other": 0})
        key = (
            "success"
            if r.conclusion == "success"
            else ("failure" if r.conclusion in ("failure", "timed_out") else "other")
        )
        bucket[key] += 1
    by_workflow: dict[str, dict[str, int]] = {}
    for r in completed:
        w = by_workflow.setdefault(r.workflow_name, {"total": 0, "success": 0})
        w["total"] += 1
        w["success"] += r.conclusion == "success"
    return {
        "days": days,
        "total_runs": len(runs),
        "completed_runs": len(completed),
        "in_progress": len(runs) - len(completed),
        "successful": success,
        "failed": failed,
        "success_rate": round(success / (success + failed), 3) if success + failed else None,
        "avg_duration_seconds": round(sum(durations) / len(durations)) if durations else None,
        "daily": [{"date": k, **v} for k, v in sorted(daily.items())],
        "by_workflow": [{"workflow": k, **v} for k, v in sorted(by_workflow.items())],
    }
