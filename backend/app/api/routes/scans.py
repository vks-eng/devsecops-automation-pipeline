"""Cross-project read endpoints: scans, findings (vulnerability reports), dependency inventory."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import case, func, or_, select

from app.api.deps import CurrentUser, DbSession
from app.models import DependencyItem, Finding, Project, Scan, ScanStatus
from app.schemas import DependencyOut, FindingOut, Page, ScanDetail, ScanOut
from app.services.access import accessible_project_ids, get_project_for_user
from app.services.scoring import latest_scans

router = APIRouter(tags=["scans"])

SEVERITY_RANK = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
SeverityQ = Query(None, pattern="^(critical|high|medium|low|info)$")


def _names(db: DbSession, ids: set[int]) -> dict[int, str]:
    if not ids:
        return {}
    return dict(db.execute(select(Project.id, Project.name).where(Project.id.in_(ids))).all())


@router.get("/scans", response_model=list[ScanOut])
def list_scans(
    db: DbSession,
    user: CurrentUser,
    scan_type: str | None = Query(None, pattern="^(code_quality|container|dependency)$"),
    project_id: int | None = None,
    scan_status: str | None = Query(
        None, alias="status", pattern="^(pending|running|completed|failed)$"
    ),
    limit: int = Query(50, ge=1, le=200),
) -> list[ScanOut]:
    ids = accessible_project_ids(db, user)
    if project_id is not None:
        ids = [i for i in ids if i == project_id]
    stmt = select(Scan).where(Scan.project_id.in_(ids or [-1]))
    if scan_type:
        stmt = stmt.where(Scan.scan_type == scan_type)
    if scan_status:
        stmt = stmt.where(Scan.status == scan_status)
    scans = list(db.scalars(stmt.order_by(Scan.created_at.desc()).limit(limit)))
    names = _names(db, {s.project_id for s in scans})
    out = []
    for s in scans:
        item = ScanOut.model_validate(s)
        item.project_name = names.get(s.project_id)
        out.append(item)
    return out


@router.get("/scans/{scan_id}", response_model=ScanDetail)
def get_scan(scan_id: int, db: DbSession, user: CurrentUser) -> ScanDetail:
    scan = db.get(Scan, scan_id)
    if scan is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Scan not found")
    project = get_project_for_user(db, scan.project_id, user)
    detail = ScanDetail.model_validate(scan)
    detail.metadata = scan.metadata_json or {}
    detail.project_name = project.name
    return detail


@router.get("/findings", response_model=Page[FindingOut])
def list_findings(
    db: DbSession,
    user: CurrentUser,
    category: str | None = Query(None, pattern="^(code_quality|container|dependency)$"),
    severity: str | None = SeverityQ,
    finding_type: str | None = Query(None, pattern="^(vulnerability|bug|code_smell)$"),
    project_id: int | None = None,
    scan_id: int | None = None,
    q: str | None = Query(None, max_length=100),
    latest_only: bool = True,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> Page[FindingOut]:
    ids = accessible_project_ids(db, user)
    if project_id is not None:
        ids = [i for i in ids if i == project_id]
    stmt = select(Finding).where(Finding.project_id.in_(ids or [-1]))
    if scan_id is not None:
        stmt = stmt.where(Finding.scan_id == scan_id)
    elif latest_only:
        scan_ids = [s.id for s in latest_scans(db, ids)]
        stmt = stmt.where(Finding.scan_id.in_(scan_ids or [-1]))
    if category:
        stmt = stmt.where(Finding.category == category)
    if severity:
        stmt = stmt.where(Finding.severity == severity)
    if finding_type:
        stmt = stmt.where(Finding.finding_type == finding_type)
    if q:
        like = f"%{q.replace('%', '').replace('_', '')}%"
        stmt = stmt.where(
            or_(
                Finding.title.ilike(like),
                Finding.rule_id.ilike(like),
                Finding.component.ilike(like),
            )
        )
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    severity_order = case(SEVERITY_RANK, value=Finding.severity, else_=len(SEVERITY_RANK))
    rows = list(db.scalars(stmt.order_by(severity_order, Finding.id).limit(limit).offset(offset)))
    names = _names(db, {f.project_id for f in rows})
    items = []
    for f in rows:
        item = FindingOut.model_validate(f)
        item.project_name = names.get(f.project_id)
        items.append(item)
    return Page[FindingOut](items=items, total=total, limit=limit, offset=offset)


@router.get("/findings/summary")
def findings_summary(
    db: DbSession, user: CurrentUser, project_id: int | None = None
) -> dict[str, Any]:
    ids = accessible_project_ids(db, user)
    if project_id is not None:
        ids = [i for i in ids if i == project_id]
    scan_ids = [s.id for s in latest_scans(db, ids)]
    rows = db.execute(
        select(Finding.category, Finding.severity, func.count())
        .where(Finding.scan_id.in_(scan_ids or [-1]), Finding.finding_type != "code_smell")
        .group_by(Finding.category, Finding.severity)
    ).all()
    result: dict[str, dict[str, int]] = {}
    for category, severity, n in rows:
        result.setdefault(category, {})[severity] = int(n)
    return {"by_category": result}


@router.get("/findings/top-rules")
def top_rules(
    db: DbSession,
    user: CurrentUser,
    project_id: int | None = None,
    limit: int = Query(8, ge=1, le=50),
) -> list[dict[str, Any]]:
    """Most frequent open rules / CVEs across the latest scans (security findings only)."""
    ids = accessible_project_ids(db, user)
    if project_id is not None:
        ids = [i for i in ids if i == project_id]
    scan_ids = [s.id for s in latest_scans(db, ids)]
    worst = func.min(case(SEVERITY_RANK, value=Finding.severity, else_=len(SEVERITY_RANK)))
    rows = db.execute(
        select(
            Finding.rule_id,
            Finding.category,
            func.max(Finding.title),
            func.count(),
            func.count(func.distinct(Finding.project_id)),
            worst,
        )
        .where(Finding.scan_id.in_(scan_ids or [-1]), Finding.finding_type != "code_smell")
        .group_by(Finding.rule_id, Finding.category)
        .order_by(func.count().desc(), worst, Finding.rule_id)
        .limit(limit)
    ).all()
    names = {v: k for k, v in SEVERITY_RANK.items()}
    return [
        {
            "rule_id": rule,
            "category": category,
            "title": title,
            "count": int(count),
            "projects": int(projects),
            "severity": names.get(int(rank), "info"),
        }
        for rule, category, title, count, projects, rank in rows
    ]


@router.get("/dependencies", response_model=list[DependencyOut])
def dependency_inventory(
    db: DbSession, user: CurrentUser, project_id: int | None = None, vulnerable_only: bool = False
) -> list[DependencyOut]:
    ids = accessible_project_ids(db, user)
    if project_id is not None:
        ids = [i for i in ids if i == project_id]
    scan_ids = [
        s.id
        for s in latest_scans(db, ids)
        if s.scan_type == "dependency" and s.status == ScanStatus.COMPLETED.value
    ]
    stmt = select(DependencyItem).where(DependencyItem.scan_id.in_(scan_ids or [-1]))
    if vulnerable_only:
        stmt = stmt.where(DependencyItem.vulnerable.is_(True))
    rows = list(
        db.scalars(stmt.order_by(DependencyItem.vulnerability_count.desc(), DependencyItem.name))
    )
    names = _names(db, {d.project_id for d in rows})
    out = []
    for d in rows:
        item = DependencyOut.model_validate(d)
        item.project_name = names.get(d.project_id)
        out.append(item)
    return out
