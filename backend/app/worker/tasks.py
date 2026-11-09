"""Background tasks. Each task opens its own DB session."""

from __future__ import annotations

import logging

from sqlalchemy import select

from app.adapters.base import AdapterError
from app.db.session import get_sessionmaker
from app.models import Project
from app.parsers.common import ParseError
from app.services.pipelines import sync_project_runs
from app.services.scans import execute_scan
from app.worker.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="app.worker.tasks.run_scan")
def run_scan(scan_id: int) -> str | None:
    with get_sessionmaker()() as db:
        scan = execute_scan(db, scan_id)
        return scan.status if scan else None


@celery_app.task(name="app.worker.tasks.sync_project_pipelines")
def sync_project_pipelines(project_id: int) -> int:
    with get_sessionmaker()() as db:
        project = db.get(Project, project_id)
        if project is None:
            return 0
        try:
            return sync_project_runs(db, project)
        except (AdapterError, ParseError) as exc:
            logger.warning("Pipeline sync failed for project %s: %s", project_id, exc)
            return 0


@celery_app.task(name="app.worker.tasks.sync_all_pipelines")
def sync_all_pipelines() -> int:
    with get_sessionmaker()() as db:
        ids = list(db.scalars(select(Project.id)))
    return sum(sync_project_pipelines(pid) for pid in ids)


def enqueue_scan(scan_id: int) -> None:
    run_scan.delay(scan_id)
