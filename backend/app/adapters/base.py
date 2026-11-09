"""Adapter interfaces.

Every external integration has exactly one interface here and (at least) two
implementations: a *real* one that talks to the external system and a *mock* one that
returns deterministic, realistic data so the whole platform runs locally without
credentials. Implementations are selected by :mod:`app.adapters.registry`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


class AdapterError(RuntimeError):
    """An integration failed. Messages must never contain secrets."""


@dataclass(slots=True)
class RepoAccess:
    full_name: str
    private: bool
    can_read: bool
    permissions: dict[str, bool] = field(default_factory=dict)


@dataclass(slots=True)
class ImageMetadata:
    image_ref: str
    digest: str | None
    size_bytes: int | None
    created: str | None
    os: str | None
    architecture: str | None
    available_locally: bool


class CIProvider(Protocol):
    mode: str

    def list_workflow_runs(
        self, owner: str, repo: str, token: str | None, branch: str | None = None, limit: int = 30
    ) -> dict[str, Any]:
        """Return the raw GitHub ``GET /repos/{o}/{r}/actions/runs`` payload."""
        ...

    def check_repo_access(self, owner: str, repo: str, token: str | None) -> RepoAccess: ...

    def get_file(self, owner: str, repo: str, path: str, ref: str, token: str | None) -> str: ...


class CodeQualityProvider(Protocol):
    mode: str

    def fetch_project_analysis(self, project_key: str, branch: str | None) -> dict[str, Any]:
        """Return ``{"issues": ..., "quality_gate": ..., "measures": ...}`` raw payloads."""
        ...


class ContainerScanner(Protocol):
    mode: str

    def scan_image(self, image_ref: str) -> dict[str, Any]:
        """Return the raw Trivy JSON report for a validated image reference."""
        ...


class ImageInspector(Protocol):
    mode: str

    def inspect_image(self, image_ref: str) -> ImageMetadata: ...


class DependencyAuditor(Protocol):
    mode: str

    def audit_requirements(self, requirements_text: str) -> dict[str, Any]:
        """Return the raw ``pip-audit --format json`` report for pinned requirements."""
        ...
