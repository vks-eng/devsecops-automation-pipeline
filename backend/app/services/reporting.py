"""Report generation (JSON / CSV / HTML), vulnerability trends and remediation advice."""

from __future__ import annotations

import csv
import html
import io
from collections import Counter, defaultdict
from datetime import UTC, date, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import SEVERITY_ORDER, Finding, Project, Scan, ScanStatus
from app.services.scoring import WEIGHTS, latest_scans, project_security_overview

CSV_COLUMNS = [
    "project",
    "scan_type",
    "target",
    "severity",
    "rule_id",
    "title",
    "component",
    "installed_version",
    "fixed_version",
    "file_path",
    "line",
    "recommendation",
]


def _severity_rank(sev: str) -> int:
    return SEVERITY_ORDER.index(sev) if sev in SEVERITY_ORDER else len(SEVERITY_ORDER)


def remediation_recommendations(findings: list[Finding], limit: int = 15) -> list[dict[str, Any]]:
    """Group findings by component and rank remediation actions by risk reduction."""
    groups: dict[tuple[str, str], list[Finding]] = defaultdict(list)
    for f in findings:
        if f.finding_type == "code_smell":
            continue
        groups[(f.category, f.component or f.rule_id)].append(f)
    recs = []
    for (category, component), items in groups.items():
        items.sort(key=lambda f: _severity_rank(f.severity))
        top = items[0]
        risk = sum(WEIGHTS.get(f.severity, 0) for f in items)
        fixes = sorted({f.fixed_version for f in items if f.fixed_version})
        recs.append(
            {
                "category": category,
                "component": component,
                "highest_severity": top.severity,
                "finding_count": len(items),
                "risk_reduction": risk,
                "fixed_versions": fixes,
                "action": top.recommendation,
                "rule_ids": sorted({f.rule_id for f in items})[:10],
            }
        )
    recs.sort(key=lambda r: (-r["risk_reduction"], _severity_rank(r["highest_severity"])))
    return recs[:limit]


def _finding_dict(f: Finding, scan: Scan, project: Project) -> dict[str, Any]:
    return {
        "project": project.slug,
        "scan_type": scan.scan_type,
        "target": scan.target,
        "severity": f.severity,
        "rule_id": f.rule_id,
        "title": f.title,
        "finding_type": f.finding_type,
        "component": f.component,
        "installed_version": f.installed_version,
        "fixed_version": f.fixed_version,
        "file_path": f.file_path,
        "line": f.line,
        "reference_url": f.reference_url,
        "recommendation": f.recommendation,
    }


def build_project_report(db: Session, project: Project) -> dict[str, Any]:
    scans = latest_scans(db, [project.id])
    scan_by_id = {s.id: s for s in scans}
    findings = list(
        db.scalars(select(Finding).where(Finding.scan_id.in_(list(scan_by_id) or [-1])))
    )
    findings.sort(key=lambda f: (_severity_rank(f.severity), f.rule_id))
    overview = project_security_overview(db, project)
    by_category: dict[str, Counter[str]] = defaultdict(Counter)
    for f in findings:
        by_category[f.category][f.severity] += 1
    return {
        "report_version": "1.0",
        "generated_at": datetime.now(UTC).isoformat(),
        "project": {
            "id": project.id,
            "name": project.name,
            "slug": project.slug,
            "team": project.team,
            "repository": project.repo_url,
            "default_branch": project.default_branch,
        },
        "security_score": {
            "score": overview["score"],
            "grade": overview["grade"],
            "vulnerability_penalty": overview["vulnerability_penalty"],
            "quality_gate_penalty": overview["quality_gate_penalty"],
            "pipeline_penalty": overview["pipeline_penalty"],
            "methodology": "docs/security-score.md",
        },
        "quality_gate_status": overview["quality_gate_status"],
        "pipeline_success_rate": overview["pipeline_success_rate"],
        "severity_totals": overview["counts"],
        "by_category": {
            cat: {s: c.get(s, 0) for s in SEVERITY_ORDER} for cat, c in by_category.items()
        },
        "scans": [
            {
                "id": s.id,
                "scan_type": s.scan_type,
                "target": s.target,
                "adapter_mode": s.adapter_mode,
                "completed_at": s.completed_at.isoformat() if s.completed_at else None,
                "summary": s.summary,
                "quality_gate_status": s.quality_gate_status,
            }
            for s in scans
        ],
        "recommendations": remediation_recommendations(findings),
        "findings": [_finding_dict(f, scan_by_id[f.scan_id], project) for f in findings],
    }


def report_to_csv(findings: list[dict[str, Any]]) -> str:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=CSV_COLUMNS, extrasaction="ignore")
    writer.writeheader()
    for row in findings:
        # Neutralise spreadsheet formula injection (CSV injection).
        safe = {
            k: ("'" + v if isinstance(v, str) and v[:1] in ("=", "+", "-", "@", "\t", "\r") else v)
            for k, v in row.items()
        }
        writer.writerow(safe)
    return buffer.getvalue()


_SEV_COLORS = {
    "critical": "#b91c1c",
    "high": "#c2410c",
    "medium": "#a16207",
    "low": "#1d4ed8",
    "info": "#475569",
}


def report_to_html(report: dict[str, Any]) -> str:
    e = html.escape
    p = report["project"]
    score = report["security_score"]
    totals = report["severity_totals"]
    sev_cells = "".join(
        f"<td style='color:{_SEV_COLORS[s]};font-weight:600'>{totals.get(s, 0)}</td>"
        for s in SEVERITY_ORDER
    )
    rec_rows = "".join(
        f"<tr><td>{e(r['highest_severity'])}</td><td>{e(r['category'])}</td>"
        f"<td>{e(r['component'])}</td><td>{r['finding_count']}</td><td>{e(r['action'])}</td></tr>"
        for r in report["recommendations"]
    )
    finding_rows = "".join(
        f"<tr><td style='color:{_SEV_COLORS.get(f['severity'], '#000')}'>{e(f['severity'])}</td>"
        f"<td>{e(f['scan_type'])}</td><td>{e(f['rule_id'])}</td><td>{e(f['title'])}</td>"
        f"<td>{e(f['component'] or '')}</td><td>{e(f['fixed_version'] or '-')}</td></tr>"
        for f in report["findings"]
    )
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>Security report - {e(p["name"])}</title>
<style>
body{{font-family:system-ui,sans-serif;margin:2rem;color:#0f172a}}
table{{border-collapse:collapse;width:100%;margin:1rem 0;font-size:13px}}
th,td{{border:1px solid #cbd5e1;padding:6px 8px;text-align:left;vertical-align:top}}
th{{background:#f1f5f9}} .score{{font-size:2.5rem;font-weight:700}}
</style></head><body>
<h1>Security report: {e(p["name"])}</h1>
<p>Repository: {e(p["repository"])} &middot; Team: {e(p["team"] or "-")} &middot;
Generated: {e(report["generated_at"])}</p>
<p class="score">{score["score"]} / 100 (grade {e(score["grade"])})</p>
<p>Quality gate: {e(str(report["quality_gate_status"] or "n/a"))} &middot;
Pipeline success rate: {
        e(
            str(
                report["pipeline_success_rate"]
                if report["pipeline_success_rate"] is not None
                else "n/a"
            )
        )
    }</p>
<h2>Open findings by severity</h2>
<table><tr>{"".join(f"<th>{s}</th>" for s in SEVERITY_ORDER)}</tr><tr>{sev_cells}</tr></table>
<h2>Top remediation recommendations</h2>
<table><tr><th>Severity</th><th>Category</th><th>Component</th><th>Findings</th><th>Action</th>
</tr>{rec_rows}</table>
<h2>Findings ({len(report["findings"])})</h2>
<table><tr><th>Severity</th><th>Scan</th><th>ID</th><th>Title</th><th>Component</th><th>Fix</th>
</tr>{finding_rows}</table>
</body></html>"""


def summary_rows(db: Session, projects: list[Project]) -> list[dict[str, Any]]:
    rows = []
    for project in projects:
        o = project_security_overview(db, project)
        rows.append(
            {
                "project": project.slug,
                "name": project.name,
                "team": project.team,
                "score": o["score"],
                "grade": o["grade"],
                **{s: o["counts"].get(s, 0) for s in SEVERITY_ORDER},
                "quality_gate": o["quality_gate_status"] or "",
                "pipeline_success_rate": o["pipeline_success_rate"],
                "last_scan_at": o["last_scan_at"].isoformat() if o["last_scan_at"] else "",
            }
        )
    return rows


def rows_to_csv(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return ""
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue()


def vulnerability_trends(
    db: Session, project_ids: list[int], days: int = 30
) -> list[dict[str, Any]]:
    """Open findings per day: for each day, sum the latest completed scan per
    (project, type, target) as of the end of that day."""
    end = datetime.now(UTC).date()
    start = end - timedelta(days=days - 1)
    if not project_ids:
        return [
            {"date": (start + timedelta(d)).isoformat(), **dict.fromkeys(SEVERITY_ORDER, 0)}
            for d in range(days)
        ]
    scans = list(
        db.scalars(
            select(Scan)
            .where(
                Scan.project_id.in_(project_ids),
                Scan.status == ScanStatus.COMPLETED.value,
                Scan.completed_at.is_not(None),
            )
            .order_by(Scan.completed_at)
        )
    )
    series = []
    latest: dict[tuple[int, str, str], dict[str, Any]] = {}
    idx = 0
    for offset in range(days):
        day: date = start + timedelta(days=offset)
        day_end = datetime.combine(day + timedelta(days=1), datetime.min.time(), tzinfo=UTC)
        while idx < len(scans) and scans[idx].completed_at < day_end:  # type: ignore[operator]
            s = scans[idx]
            latest[(s.project_id, s.scan_type, s.target)] = s.summary or {}
            idx += 1
        totals = {sev: sum(int(v.get(sev, 0)) for v in latest.values()) for sev in SEVERITY_ORDER}
        series.append({"date": day.isoformat(), **totals})
    return series
