from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any, Literal

from fastapi import APIRouter, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession
from app.models import Project, ScoreSnapshot
from app.services import audit
from app.services.access import accessible_project_ids, get_project_for_user
from app.services.reporting import (
    build_project_report,
    report_to_csv,
    report_to_html,
    rows_to_csv,
    summary_rows,
    vulnerability_trends,
)

router = APIRouter(prefix="/reports", tags=["reports"])


def _download(content: str, media_type: str, filename: str) -> Response:
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/projects/{project_id}", response_model=None)
def project_report(
    project_id: int,
    db: DbSession,
    user: CurrentUser,
    request: Request,
    fmt: Literal["json", "csv", "html"] = Query("json", alias="format"),
    download: bool = False,
) -> Response | dict[str, Any]:
    project = get_project_for_user(db, project_id, user)
    report = build_project_report(db, project)
    audit.record(
        db,
        "report.export",
        actor=user,
        resource_type="project",
        resource_id=project.id,
        request=request,
        details={"format": fmt},
    )
    stamp = datetime.now(UTC).strftime("%Y%m%d")
    base = f"security-report-{project.slug}-{stamp}"
    if fmt == "csv":
        return _download(report_to_csv(report["findings"]), "text/csv", f"{base}.csv")
    if fmt == "html":
        html = report_to_html(report)
        if download:
            return _download(html, "text/html", f"{base}.html")
        return HTMLResponse(html)
    if download:
        return _download(
            json.dumps(report, indent=2, default=str), "application/json", f"{base}.json"
        )
    return JSONResponse(json.loads(json.dumps(report, default=str)))


@router.get("/summary", response_model=None)
def portfolio_summary(
    db: DbSession, user: CurrentUser, fmt: Literal["json", "csv"] = Query("json", alias="format")
) -> Response | list[dict[str, Any]]:
    ids = accessible_project_ids(db, user)
    projects = list(
        db.scalars(select(Project).where(Project.id.in_(ids or [-1])).order_by(Project.name))
    )
    rows = summary_rows(db, projects)
    if fmt == "csv":
        stamp = datetime.now(UTC).strftime("%Y%m%d")
        return _download(rows_to_csv(rows), "text/csv", f"security-summary-{stamp}.csv")
    return rows


@router.get("/trends")
def trends(
    db: DbSession,
    user: CurrentUser,
    days: int = Query(30, ge=7, le=180),
    project_id: int | None = None,
) -> dict[str, Any]:
    ids = accessible_project_ids(db, user)
    if project_id is not None:
        ids = [i for i in ids if i == project_id]
    snapshots = list(
        db.scalars(
            select(ScoreSnapshot)
            .where(ScoreSnapshot.project_id.in_(ids or [-1]))
            .order_by(ScoreSnapshot.created_at)
        )
    )
    daily_scores: dict[str, list[float]] = {}
    for s in snapshots:
        daily_scores.setdefault(s.created_at.date().isoformat(), []).append(s.score)
    return {
        "vulnerabilities": vulnerability_trends(db, ids, days),
        "scores": [
            {"date": d, "average_score": round(sum(v) / len(v), 1)}
            for d, v in sorted(daily_scores.items())
        ][-days:],
    }
