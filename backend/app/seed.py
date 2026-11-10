"""Seed demo data for LOCAL development: users, projects, mock pipeline runs and scans.

    python -m app.seed

The demo credentials below are public and for local use only. The seed refuses to run
when ENVIRONMENT=production.
"""

from __future__ import annotations

import math
import sys
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.adapters.github_actions import MOCK_PINS, mock_requirements
from app.adapters.pip_audit import MockPipAuditAdapter
from app.core.config import get_settings
from app.core.security import hash_password
from app.core.validators import parse_github_repo_url
from app.db.session import get_sessionmaker
from app.models import (
    Project,
    ProjectMember,
    ProjectRole,
    Scan,
    ScanType,
    ScoreSnapshot,
    User,
    UserRole,
)
from app.services.pipelines import sync_project_runs
from app.services.scans import create_scan, execute_scan, import_scan_report

HISTORY_DAYS = (28, 21, 14, 7)


def _historical_requirements(full_name: str, days_ago: int) -> str:
    """Older snapshots pin more vulnerable versions (dependencies were upgraded over time).

    Starts from the repository's current mock requirements and reverts a share of the
    already-patched packages to their vulnerable pin; the share grows with age.
    """
    vulnerable = {name: old for name, old, fixed in MOCK_PINS if fixed is not None}
    lines = mock_requirements(full_name).splitlines()
    pins = [line.split("==", 1) for line in lines if "==" in line]
    patched = [n for n, v in pins if n in vulnerable and v != vulnerable[n]]
    revert = set(patched[: math.ceil(len(patched) * days_ago / HISTORY_DAYS[0])])
    return "".join(f"{n}=={vulnerable[n] if n in revert else v}\n" for n, v in pins)


def seed_history(db: Session, project: Project, user_id: int) -> None:
    """Back-dated scans so trend charts have history (demo data only).

    Dependency scans use progressively more patched requirements, so the trend shows
    remediation over time; code-quality and container scans repeat the mock results.
    """
    if db.scalar(select(Scan.id).where(Scan.project_id == project.id, Scan.trigger == "seed")):
        return
    auditor = MockPipAuditAdapter()
    for days_ago in HISTORY_DAYS:
        when = datetime.now(UTC) - timedelta(days=days_ago, hours=2)
        last_snapshot = db.scalar(select(func.max(ScoreSnapshot.id))) or 0
        report = auditor.audit_requirements(
            _historical_requirements(project.repo_full_name, days_ago)
        )
        scans = [
            import_scan_report(
                db, project, ScanType.DEPENDENCY, project.default_branch, report, user_id
            )
        ]
        targets = [(ScanType.CODE_QUALITY, None)] + [
            (ScanType.CONTAINER, image) for image in project.container_images
        ]
        for scan_type, target in targets:
            created = create_scan(db, project, scan_type, target, user_id, trigger="seed")
            executed = execute_scan(db, created.id)
            if executed is not None:
                scans.append(executed)
        for scan in scans:
            scan.trigger = "seed"
            scan.created_at = scan.started_at = scan.completed_at = when
        for snapshot in db.scalars(
            select(ScoreSnapshot).where(
                ScoreSnapshot.project_id == project.id, ScoreSnapshot.id > last_snapshot
            )
        ):
            snapshot.created_at = when
        db.commit()


DEMO_USERS = [
    ("admin@example.com", "Ada Admin", "ShieldOpsAdmin2026", UserRole.ADMIN),
    ("dev@example.com", "Dev Maintainer", "ShieldOpsDev2026", UserRole.MEMBER),
    ("viewer@example.com", "Vic Viewer", "ShieldOpsView2026", UserRole.MEMBER),
]

DEMO_PROJECTS = [
    {
        "name": "Payments API",
        "team": "Payments",
        "repo_url": "https://github.com/acme-demo/payments-api",
        "branches": ["develop"],
        "sonar_project_key": "acme_payments-api",
        "container_images": ["ghcr.io/acme-demo/payments-api:1.8.2", "python:3.11-slim"],
        "description": "Card payment processing service (FastAPI).",
    },
    {
        "name": "Customer Portal",
        "team": "Web",
        "repo_url": "https://github.com/acme-demo/customer-portal",
        "branches": ["release/2.x"],
        "sonar_project_key": "acme_customer-portal",
        "container_images": ["ghcr.io/acme-demo/customer-portal:2.4.0"],
        "description": "Customer-facing self-service portal.",
    },
    {
        "name": "Data Pipeline",
        "team": "Data",
        "repo_url": "https://github.com/acme-demo/data-pipeline",
        "branches": [],
        "sonar_project_key": "acme_data-pipeline",
        "container_images": ["ghcr.io/acme-demo/etl-worker:0.9.1-alpine"],
        "description": "Nightly ETL jobs.",
    },
    {
        "name": "Auth Service",
        "team": "Platform",
        "repo_url": "https://github.com/acme-demo/auth-service",
        "branches": ["develop"],
        "sonar_project_key": "acme_auth-service",
        "container_images": ["gcr.io/distroless/python3-debian12:nonroot"],
        "description": "OAuth2 / OIDC identity provider.",
    },
]


def seed(db: Session) -> None:
    users: dict[str, User] = {}
    for email, name, password, role in DEMO_USERS:
        user = db.scalar(select(User).where(User.email == email))
        if user is None:
            user = User(
                email=email,
                full_name=name,
                hashed_password=hash_password(password),
                role=role.value,
            )
            db.add(user)
        users[email] = user
    db.commit()
    admin = users["admin@example.com"]
    for spec in DEMO_PROJECTS:
        owner, repo = parse_github_repo_url(spec["repo_url"])
        project = db.scalar(
            select(Project).where(Project.repo_owner == owner, Project.repo_name == repo)
        )
        if project is None:
            project = Project(
                **spec,
                slug=repo,
                repo_owner=owner,
                repo_name=repo,
                default_branch="main",
                owner_id=admin.id,
                scan_config={"requirements_path": "requirements.txt"},
            )
            db.add(project)
            db.flush()
            db.add(
                ProjectMember(
                    project_id=project.id,
                    user_id=users["dev@example.com"].id,
                    role=ProjectRole.MAINTAINER.value,
                )
            )
            db.add(
                ProjectMember(
                    project_id=project.id,
                    user_id=users["viewer@example.com"].id,
                    role=ProjectRole.VIEWER.value,
                )
            )
            db.commit()
        sync_project_runs(db, project, notify=False)
        seed_history(db, project, admin.id)
        targets = [(ScanType.CODE_QUALITY, None), (ScanType.DEPENDENCY, None)] + [
            (ScanType.CONTAINER, image) for image in project.container_images
        ]
        for scan_type, target in targets:
            scan = create_scan(db, project, scan_type, target, admin.id, trigger="seed")
            execute_scan(db, scan.id)
        print(f"seeded {project.name}")


def main() -> int:
    if get_settings().environment == "production":
        print("Refusing to seed demo data in production", file=sys.stderr)
        return 1
    with get_sessionmaker()() as db:
        seed(db)
    print("Demo users (LOCAL ONLY): " + ", ".join(f"{e} / {p}" for e, _, p, _ in DEMO_USERS))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
