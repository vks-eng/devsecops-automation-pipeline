from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.adapters import registry
from app.adapters.base import AdapterError
from app.api.deps import CurrentUser, DbSession
from app.core.validators import parse_github_repo_url, slugify
from app.models import Project, ProjectMember, ProjectRole, Scan, ScanType, User
from app.parsers.common import ParseError
from app.schemas import (
    CredentialIn,
    CredentialStatus,
    MemberCreate,
    MemberOut,
    ProjectCreate,
    ProjectOut,
    ProjectUpdate,
    ScanCreate,
    ScanImport,
    ScanOut,
)
from app.services import audit, credentials
from app.services.access import accessible_project_ids, get_project_for_user, project_role
from app.services.pipelines import sync_project_runs
from app.services.scans import ScanRequestError, create_scan, import_scan_report
from app.services.scoring import project_security_overview
from app.worker.tasks import enqueue_scan

router = APIRouter(prefix="/projects", tags=["projects"])


def _out(db: DbSession, project: Project, user: User) -> ProjectOut:
    out = ProjectOut.model_validate(project)
    out.my_role = (
        "admin"
        if user.is_admin and project.owner_id != user.id
        else project_role(db, project, user)
    )
    return out


@router.get("", response_model=list[ProjectOut])
def list_projects(db: DbSession, user: CurrentUser) -> list[ProjectOut]:
    ids = accessible_project_ids(db, user)
    projects = db.scalars(select(Project).where(Project.id.in_(ids or [-1])).order_by(Project.name))
    return [_out(db, p, user) for p in projects]


@router.post("", response_model=ProjectOut, status_code=201)
def create_project(
    body: ProjectCreate, db: DbSession, user: CurrentUser, request: Request
) -> ProjectOut:
    owner, repo = parse_github_repo_url(body.repo_url)
    slug = body.slug or slugify(body.name)
    if db.scalar(select(Project).where(Project.slug == slug)):
        raise HTTPException(status.HTTP_409_CONFLICT, "Project slug already exists")
    if db.scalar(
        select(Project).where(
            func.lower(Project.repo_owner) == owner.lower(),
            func.lower(Project.repo_name) == repo.lower(),
        )
    ):
        raise HTTPException(status.HTTP_409_CONFLICT, "Repository is already registered")
    data = body.model_dump(exclude={"slug", "scan_config"})
    project = Project(
        **data,
        slug=slug,
        repo_owner=owner,
        repo_name=repo,
        owner_id=user.id,
        scan_config=body.scan_config.model_dump(),
    )
    db.add(project)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Project already exists") from None
    audit.record(
        db,
        "project.create",
        actor=user,
        resource_type="project",
        resource_id=project.id,
        request=request,
        details={"repo": f"{owner}/{repo}", "slug": slug},
    )
    return _out(db, project, user)


@router.get("/{project_id}", response_model=ProjectOut)
def get_project(project_id: int, db: DbSession, user: CurrentUser) -> ProjectOut:
    return _out(db, get_project_for_user(db, project_id, user), user)


@router.patch("/{project_id}", response_model=ProjectOut)
def update_project(
    project_id: int, body: ProjectUpdate, db: DbSession, user: CurrentUser, request: Request
) -> ProjectOut:
    project = get_project_for_user(db, project_id, user, ProjectRole.MAINTAINER)
    changes = body.model_dump(exclude_unset=True)
    if "scan_config" in changes and body.scan_config is not None:
        changes["scan_config"] = body.scan_config.model_dump()
    for field, value in changes.items():
        if field in {"name", "default_branch"} and value is None:
            continue
        setattr(project, field, value)
    audit.record(
        db,
        "project.update",
        actor=user,
        resource_type="project",
        resource_id=project.id,
        request=request,
        details={"fields": sorted(changes)},
    )
    return _out(db, project, user)


@router.delete("/{project_id}", status_code=204)
def delete_project(project_id: int, db: DbSession, user: CurrentUser, request: Request) -> None:
    project = get_project_for_user(db, project_id, user, ProjectRole.OWNER)
    audit.record(
        db,
        "project.delete",
        actor=user,
        resource_type="project",
        resource_id=project.id,
        request=request,
        details={"slug": project.slug},
        commit=False,
    )
    db.delete(project)
    db.commit()


# ------------------------------------------------------------------ members
@router.get("/{project_id}/members", response_model=list[MemberOut])
def list_members(project_id: int, db: DbSession, user: CurrentUser) -> list[MemberOut]:
    project = get_project_for_user(db, project_id, user)
    owner = db.get(User, project.owner_id)
    out = (
        [MemberOut(user_id=owner.id, email=owner.email, full_name=owner.full_name, role="owner")]
        if owner
        else []
    )
    for m in db.scalars(select(ProjectMember).where(ProjectMember.project_id == project.id)):
        out.append(
            MemberOut(
                user_id=m.user_id, email=m.user.email, full_name=m.user.full_name, role=m.role
            )
        )
    return out


@router.post("/{project_id}/members", response_model=MemberOut, status_code=201)
def add_member(
    project_id: int, body: MemberCreate, db: DbSession, user: CurrentUser, request: Request
) -> MemberOut:
    project = get_project_for_user(db, project_id, user, ProjectRole.OWNER)
    target = db.scalar(select(User).where(func.lower(User.email) == body.email.lower()))
    if target is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    if target.id == project.owner_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "User already owns this project")
    member = db.scalar(
        select(ProjectMember).where(
            ProjectMember.project_id == project.id, ProjectMember.user_id == target.id
        )
    )
    if member is None:
        member = ProjectMember(project_id=project.id, user_id=target.id)
        db.add(member)
    member.role = body.role.value
    audit.record(
        db,
        "project.member.upsert",
        actor=user,
        resource_type="project",
        resource_id=project.id,
        request=request,
        details={"member": target.email, "role": member.role},
    )
    return MemberOut(
        user_id=target.id, email=target.email, full_name=target.full_name, role=member.role
    )


@router.delete("/{project_id}/members/{user_id}", status_code=204)
def remove_member(
    project_id: int, user_id: int, db: DbSession, user: CurrentUser, request: Request
) -> None:
    project = get_project_for_user(db, project_id, user, ProjectRole.OWNER)
    member = db.scalar(
        select(ProjectMember).where(
            ProjectMember.project_id == project.id, ProjectMember.user_id == user_id
        )
    )
    if member is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Member not found")
    db.delete(member)
    audit.record(
        db,
        "project.member.remove",
        actor=user,
        resource_type="project",
        resource_id=project.id,
        request=request,
        details={"user_id": user_id},
    )


# ------------------------------------------------------------------ credentials
@router.get("/{project_id}/credentials/github", response_model=CredentialStatus)
def credential_status(project_id: int, db: DbSession, user: CurrentUser) -> CredentialStatus:
    project = get_project_for_user(db, project_id, user, ProjectRole.MAINTAINER)
    cred = credentials.get_credential(db, project.id, "github")
    return CredentialStatus(
        provider="github",
        configured=cred is not None,
        token_hint=cred.token_hint if cred else None,
        created_at=cred.created_at if cred else None,
    )


@router.put("/{project_id}/credentials/github", response_model=CredentialStatus)
def set_credential(
    project_id: int, body: CredentialIn, db: DbSession, user: CurrentUser, request: Request
) -> CredentialStatus:
    project = get_project_for_user(db, project_id, user, ProjectRole.OWNER)
    # Verify the token can actually read the registered repository before storing it.
    try:
        access = registry.get_ci_provider().check_repo_access(
            project.repo_owner, project.repo_name, body.token
        )
    except AdapterError as exc:
        audit.record(
            db,
            "credential.set",
            actor=user,
            resource_type="project",
            resource_id=project.id,
            outcome="failure",
            request=request,
            details={"provider": "github", "reason": str(exc)},
        )
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, f"Token verification failed: {exc}"
        ) from None
    if not access.can_read:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Token cannot read this repository")
    cred = credentials.set_token(db, project.id, "github", body.token, user.id)
    audit.record(
        db,
        "credential.set",
        actor=user,
        resource_type="project",
        resource_id=project.id,
        request=request,
        details={"provider": "github", "hint": cred.token_hint},
    )
    return CredentialStatus(
        provider="github", configured=True, token_hint=cred.token_hint, created_at=cred.created_at
    )


@router.delete("/{project_id}/credentials/github", status_code=204)
def delete_credential(project_id: int, db: DbSession, user: CurrentUser, request: Request) -> None:
    project = get_project_for_user(db, project_id, user, ProjectRole.OWNER)
    if not credentials.delete_token(db, project.id, "github"):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No credential configured")
    audit.record(
        db,
        "credential.delete",
        actor=user,
        resource_type="project",
        resource_id=project.id,
        request=request,
        details={"provider": "github"},
    )


# ------------------------------------------------------------------ scans & pipelines
@router.get("/{project_id}/scans", response_model=list[ScanOut])
def project_scans(
    project_id: int,
    db: DbSession,
    user: CurrentUser,
    scan_type: ScanType | None = None,
    limit: int = Query(50, ge=1, le=200),
) -> list[Scan]:
    project = get_project_for_user(db, project_id, user)
    stmt = select(Scan).where(Scan.project_id == project.id)
    if scan_type:
        stmt = stmt.where(Scan.scan_type == scan_type.value)
    return list(db.scalars(stmt.order_by(Scan.created_at.desc()).limit(limit)))


@router.post("/{project_id}/scans", response_model=ScanOut, status_code=202)
def trigger_scan(
    project_id: int, body: ScanCreate, db: DbSession, user: CurrentUser, request: Request
) -> Scan:
    # Authorization: only maintainers/owners (or admins) of a registered project may scan.
    project = get_project_for_user(db, project_id, user, ProjectRole.MAINTAINER)
    flag = f"enable_{body.scan_type.value}"
    if project.scan_config.get(flag, True) is False:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"{body.scan_type.value} scans are disabled for this project",
        )
    try:
        scan = create_scan(db, project, body.scan_type, body.target, user.id)
    except ScanRequestError as exc:
        audit.record(
            db,
            "scan.trigger",
            actor=user,
            resource_type="project",
            resource_id=project.id,
            outcome="denied",
            request=request,
            details={"scan_type": body.scan_type.value, "reason": str(exc)},
        )
        raise HTTPException(422, str(exc)) from None
    audit.record(
        db,
        "scan.trigger",
        actor=user,
        resource_type="scan",
        resource_id=scan.id,
        request=request,
        details={"project_id": project.id, "scan_type": scan.scan_type, "target": scan.target},
    )
    enqueue_scan(scan.id)
    db.refresh(scan)
    return scan


@router.post("/{project_id}/scans/import", response_model=ScanOut, status_code=201)
def import_scan(
    project_id: int, body: ScanImport, db: DbSession, user: CurrentUser, request: Request
) -> Scan:
    project = get_project_for_user(db, project_id, user, ProjectRole.MAINTAINER)
    try:
        scan = import_scan_report(
            db, project, ScanType(body.scan_type), body.target, body.report, user.id
        )
    except (ScanRequestError, ParseError) as exc:
        db.rollback()
        raise HTTPException(422, str(exc)) from None
    audit.record(
        db,
        "scan.import",
        actor=user,
        resource_type="scan",
        resource_id=scan.id,
        request=request,
        details={"project_id": project.id, "scan_type": scan.scan_type},
    )
    return scan


@router.post("/{project_id}/pipelines/sync")
def sync_pipelines(
    project_id: int, db: DbSession, user: CurrentUser, request: Request
) -> dict[str, Any]:
    project = get_project_for_user(db, project_id, user, ProjectRole.MAINTAINER)
    try:
        count = sync_project_runs(db, project)
    except (AdapterError, ParseError) as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"Pipeline sync failed: {exc}") from None
    audit.record(
        db,
        "pipeline.sync",
        actor=user,
        resource_type="project",
        resource_id=project.id,
        request=request,
        details={"runs": count},
    )
    return {"synced": count}


@router.get("/{project_id}/security")
def project_security(project_id: int, db: DbSession, user: CurrentUser) -> dict[str, Any]:
    return project_security_overview(db, get_project_for_user(db, project_id, user))
