"""Seed demo data for LOCAL development: users, projects, mock pipeline runs and scans.

    python -m app.seed

The demo credentials below are public and for local use only. The seed refuses to run
when ENVIRONMENT=production.
"""

from __future__ import annotations

import sys

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import hash_password
from app.core.validators import parse_github_repo_url
from app.db.session import get_sessionmaker
from app.models import Project, ProjectMember, ProjectRole, ScanType, User, UserRole
from app.services.pipelines import sync_project_runs
from app.services.scans import create_scan, execute_scan

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
