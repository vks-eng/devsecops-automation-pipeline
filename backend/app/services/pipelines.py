"""Pipeline (GitHub Actions) run ingestion via API polling or webhooks."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.adapters import registry
from app.models import NotificationType, PipelineRun, Project
from app.parsers.common import ParsedPipelineRun
from app.parsers.github import parse_workflow_run, parse_workflow_runs
from app.services import credentials
from app.services.notifications import notify_project

FAILED_CONCLUSIONS = {"failure", "timed_out", "startup_failure"}


def upsert_run(
    db: Session, project: Project, run: ParsedPipelineRun, source: str
) -> tuple[PipelineRun, bool]:
    """Insert or update a run. Returns ``(row, newly_failed)``."""
    row = db.scalar(
        select(PipelineRun).where(
            PipelineRun.project_id == project.id, PipelineRun.external_id == run.external_id
        )
    )
    previously_failed = bool(row and row.conclusion in FAILED_CONCLUSIONS)
    if row is None:
        row = PipelineRun(project_id=project.id, external_id=run.external_id)
        db.add(row)
    row.workflow_name = run.workflow_name
    row.branch = run.branch
    row.commit_sha = run.commit_sha
    row.event = run.event
    row.status = run.status
    row.conclusion = run.conclusion
    row.actor = run.actor
    row.html_url = run.html_url
    row.started_at = run.started_at
    row.completed_at = run.completed_at
    row.duration_seconds = run.duration_seconds
    row.source = source
    newly_failed = run.conclusion in FAILED_CONCLUSIONS and not previously_failed
    return row, newly_failed


def _notify_failure(db: Session, project: Project, row: PipelineRun) -> None:
    notify_project(
        db,
        project,
        NotificationType.PIPELINE_FAILURE,
        f"Pipeline '{row.workflow_name}' failed for {project.name}",
        f"Run {row.external_id} on branch {row.branch or '-'} ({row.commit_sha[:7]}) concluded "
        f"with '{row.conclusion}'.",
        "high",
        "/pipelines",
    )


def sync_project_runs(db: Session, project: Project, notify: bool = True) -> int:
    provider = registry.get_ci_provider()
    token = credentials.get_token(db, project.id, "github")
    payload = provider.list_workflow_runs(project.repo_owner, project.repo_name, token, limit=60)
    count = 0
    source = "mock" if provider.mode == "mock" else "api"
    for run in parse_workflow_runs(payload):
        row, newly_failed = upsert_run(db, project, run, source)
        db.flush()
        if newly_failed and notify:
            _notify_failure(db, project, row)
        count += 1
    db.commit()
    return count


def handle_workflow_run_event(db: Session, payload: dict) -> PipelineRun | None:
    """Process a verified ``workflow_run`` webhook payload."""
    repo = payload.get("repository") or {}
    full_name = str(repo.get("full_name") or "")
    if "/" not in full_name:
        return None
    owner, name = full_name.split("/", 1)
    project = db.scalar(
        select(Project).where(
            func.lower(Project.repo_owner) == owner.lower(),
            func.lower(Project.repo_name) == name.lower(),
        )
    )
    if project is None:  # only registered repositories are tracked
        return None
    run = parse_workflow_run(payload.get("workflow_run") or {})
    row, newly_failed = upsert_run(db, project, run, "webhook")
    db.flush()
    if newly_failed:
        _notify_failure(db, project, row)
    db.commit()
    return row
