"""Pydantic v2 request/response schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from app.core.validators import (
    ValidationError,
    parse_github_repo_url,
    validate_branch_name,
    validate_image_ref,
    validate_slug,
    validate_sonar_project_key,
)
from app.models import ProjectRole, ScanType


def _wrap(fn: Any, value: Any) -> Any:
    try:
        return fn(value)
    except ValidationError as exc:
        raise ValueError(str(exc)) from exc


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------- auth
class RegisterRequest(BaseModel):
    email: EmailStr
    full_name: str = Field(default="", max_length=200)
    password: str = Field(min_length=10, max_length=256)

    @field_validator("password")
    @classmethod
    def _complexity(cls, v: str) -> str:
        if not any(c.isdigit() for c in v) or not any(c.isalpha() for c in v):
            raise ValueError("Password must contain letters and digits")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=256)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"  # noqa: S105
    expires_in: int


class UserOut(ORMModel):
    id: int
    email: str
    full_name: str
    role: str
    is_active: bool
    created_at: datetime


class UserRoleUpdate(BaseModel):
    role: Literal["admin", "member"] | None = None
    is_active: bool | None = None


# ---------------------------------------------------------------- projects
class ScanConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    requirements_path: str = Field(
        default="requirements.txt", max_length=200, pattern=r"^[A-Za-z0-9._/-]+\.txt$"
    )
    enable_code_quality: bool = True
    enable_container: bool = True
    enable_dependency: bool = True

    @field_validator("requirements_path")
    @classmethod
    def _relative(cls, v: str) -> str:
        if v.startswith("/") or ".." in v:
            raise ValueError("requirements_path must be a relative path inside the repo")
        return v


class ProjectBase(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    description: str = Field(default="", max_length=2000)
    team: str = Field(default="", max_length=120)
    default_branch: str = "main"
    branches: list[str] = Field(default_factory=list, max_length=20)
    sonar_project_key: str | None = None
    container_images: list[str] = Field(default_factory=list, max_length=20)
    scan_config: ScanConfig = Field(default_factory=ScanConfig)

    @field_validator("default_branch")
    @classmethod
    def _branch(cls, v: str) -> str:
        return _wrap(validate_branch_name, v)

    @field_validator("branches")
    @classmethod
    def _branches(cls, v: list[str]) -> list[str]:
        return list(dict.fromkeys(_wrap(validate_branch_name, b) for b in v))

    @field_validator("sonar_project_key")
    @classmethod
    def _sonar(cls, v: str | None) -> str | None:
        return None if not v else _wrap(validate_sonar_project_key, v)

    @field_validator("container_images")
    @classmethod
    def _images(cls, v: list[str]) -> list[str]:
        return list(dict.fromkeys(_wrap(validate_image_ref, i) for i in v))


class ProjectCreate(ProjectBase):
    repo_url: str = Field(max_length=300)
    slug: str | None = None

    @field_validator("repo_url")
    @classmethod
    def _repo(cls, v: str) -> str:
        _wrap(parse_github_repo_url, v)
        return v

    @field_validator("slug")
    @classmethod
    def _slug(cls, v: str | None) -> str | None:
        return None if v is None else _wrap(validate_slug, v)


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    team: str | None = Field(default=None, max_length=120)
    default_branch: str | None = None
    branches: list[str] | None = Field(default=None, max_length=20)
    sonar_project_key: str | None = None
    container_images: list[str] | None = Field(default=None, max_length=20)
    scan_config: ScanConfig | None = None

    @field_validator("default_branch")
    @classmethod
    def _branch(cls, v: str | None) -> str | None:
        return None if v is None else _wrap(validate_branch_name, v)

    @field_validator("branches")
    @classmethod
    def _branches(cls, v: list[str] | None) -> list[str] | None:
        return None if v is None else list(dict.fromkeys(_wrap(validate_branch_name, b) for b in v))

    @field_validator("sonar_project_key")
    @classmethod
    def _sonar(cls, v: str | None) -> str | None:
        return None if not v else _wrap(validate_sonar_project_key, v)

    @field_validator("container_images")
    @classmethod
    def _images(cls, v: list[str] | None) -> list[str] | None:
        return None if v is None else list(dict.fromkeys(_wrap(validate_image_ref, i) for i in v))


class ProjectOut(ORMModel):
    id: int
    name: str
    slug: str
    description: str
    team: str
    repo_url: str
    repo_owner: str
    repo_name: str
    default_branch: str
    branches: list[str]
    sonar_project_key: str | None
    container_images: list[str]
    scan_config: dict[str, Any]
    owner_id: int
    created_at: datetime
    updated_at: datetime
    my_role: str | None = None


class MemberCreate(BaseModel):
    email: EmailStr
    role: ProjectRole = ProjectRole.VIEWER

    @model_validator(mode="after")
    def _no_owner(self) -> MemberCreate:
        if self.role == ProjectRole.OWNER:
            raise ValueError("Ownership cannot be granted via membership")
        return self


class MemberOut(BaseModel):
    user_id: int
    email: str
    full_name: str
    role: str


class CredentialIn(BaseModel):
    token: str = Field(min_length=20, max_length=255, pattern=r"^[A-Za-z0-9_]+$")


class CredentialStatus(BaseModel):
    provider: str
    configured: bool
    token_hint: str | None = None
    created_at: datetime | None = None


# ---------------------------------------------------------------- scans
class ScanCreate(BaseModel):
    scan_type: ScanType
    target: str | None = Field(default=None, max_length=255)


class ScanImport(BaseModel):
    scan_type: Literal["container", "dependency"]
    target: str | None = Field(default=None, max_length=255)
    report: dict[str, Any] | list[Any]


class ScanOut(ORMModel):
    id: int
    project_id: int
    scan_type: str
    target: str
    status: str
    adapter_mode: str
    trigger: str
    summary: dict[str, Any]
    quality_gate_status: str | None
    error: str | None
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    project_name: str | None = None


class ScanDetail(ScanOut):
    metadata: dict[str, Any] = Field(default_factory=dict, validation_alias="metadata_json")


class FindingOut(ORMModel):
    id: int
    scan_id: int
    project_id: int
    category: str
    finding_type: str
    severity: str
    rule_id: str
    title: str
    description: str
    component: str
    installed_version: str | None
    fixed_version: str | None
    file_path: str | None
    line: int | None
    reference_url: str | None
    recommendation: str
    created_at: datetime
    project_name: str | None = None


class Page[T](BaseModel):
    items: list[T]
    total: int
    limit: int
    offset: int


class DependencyOut(ORMModel):
    id: int
    scan_id: int
    project_id: int
    name: str
    version: str
    ecosystem: str
    vulnerable: bool
    vulnerability_count: int
    project_name: str | None = None


# ---------------------------------------------------------------- pipelines
class PipelineRunOut(ORMModel):
    id: int
    project_id: int
    external_id: str
    workflow_name: str
    branch: str
    commit_sha: str
    event: str
    status: str
    conclusion: str | None
    actor: str
    html_url: str
    started_at: datetime | None
    completed_at: datetime | None
    duration_seconds: int | None
    source: str
    project_name: str | None = None


# ---------------------------------------------------------------- notifications / audit
class NotificationOut(ORMModel):
    id: int
    project_id: int | None
    type: str
    severity: str
    title: str
    message: str
    link: str
    read_at: datetime | None
    created_at: datetime


class AuditLogOut(ORMModel):
    id: int
    actor_id: int | None
    actor_email: str
    action: str
    resource_type: str
    resource_id: str
    outcome: str
    ip_address: str
    details: dict[str, Any]
    created_at: datetime
