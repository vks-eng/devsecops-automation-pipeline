"""Authorization helpers: project-level role checks (admins bypass)."""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models import Project, ProjectMember, ProjectRole, User

_ROLE_RANK = {
    ProjectRole.VIEWER.value: 1,
    ProjectRole.MAINTAINER.value: 2,
    ProjectRole.OWNER.value: 3,
}


def project_role(db: Session, project: Project, user: User) -> str | None:
    if project.owner_id == user.id:
        return ProjectRole.OWNER.value
    member = db.scalar(
        select(ProjectMember).where(
            ProjectMember.project_id == project.id, ProjectMember.user_id == user.id
        )
    )
    return member.role if member else None


def get_project_for_user(
    db: Session, project_id: int, user: User, min_role: ProjectRole = ProjectRole.VIEWER
) -> Project:
    project = db.get(Project, project_id)
    # 404 for both "missing" and "not a member" avoids leaking project existence.
    if project is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")
    if user.is_admin:
        return project
    role = project_role(db, project, user)
    if role is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")
    if _ROLE_RANK[role] < _ROLE_RANK[min_role.value]:
        raise HTTPException(status.HTTP_403_FORBIDDEN, f"Requires project role '{min_role.value}'")
    return project


def accessible_project_ids(db: Session, user: User) -> list[int]:
    if user.is_admin:
        return list(db.scalars(select(Project.id)))
    stmt = (
        select(Project.id)
        .outerjoin(ProjectMember, ProjectMember.project_id == Project.id)
        .where(or_(Project.owner_id == user.id, ProjectMember.user_id == user.id))
        .distinct()
    )
    return list(db.scalars(stmt))


def project_recipients(db: Session, project: Project) -> list[int]:
    ids = {project.owner_id}
    ids.update(
        db.scalars(select(ProjectMember.user_id).where(ProjectMember.project_id == project.id))
    )
    return sorted(ids)
