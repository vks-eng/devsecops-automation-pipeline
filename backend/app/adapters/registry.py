"""Adapter selection based on configuration. Mock is the default for every integration.

Tests (or alternative deployments) can override any adapter with :func:`override`.
"""

from __future__ import annotations

from typing import Any

from app.adapters.base import (
    CIProvider,
    CodeQualityProvider,
    ContainerScanner,
    DependencyAuditor,
    ImageInspector,
)
from app.adapters.docker import DockerCliAdapter, MockDockerAdapter
from app.adapters.github_actions import GitHubActionsAdapter, MockGitHubActionsAdapter
from app.adapters.pip_audit import MockPipAuditAdapter, PipAuditCliAdapter
from app.adapters.sonarqube import MockSonarQubeAdapter, SonarQubeAdapter
from app.adapters.trivy import MockTrivyAdapter, TrivyBinaryAdapter, TrivyDockerAdapter
from app.core.config import get_settings

_overrides: dict[str, Any] = {}


def override(name: str, adapter: Any | None) -> None:
    if adapter is None:
        _overrides.pop(name, None)
    else:
        _overrides[name] = adapter


def clear_overrides() -> None:
    _overrides.clear()


def get_ci_provider() -> CIProvider:
    if "ci" in _overrides:
        return _overrides["ci"]
    s = get_settings()
    if s.github_mode == "real":
        return GitHubActionsAdapter(s.github_api_url, s.http_timeout_seconds)
    return MockGitHubActionsAdapter()


def get_code_quality_provider() -> CodeQualityProvider:
    if "code_quality" in _overrides:
        return _overrides["code_quality"]
    s = get_settings()
    if s.sonarqube_mode == "real":
        return SonarQubeAdapter(s.sonarqube_url, s.sonarqube_token, s.http_timeout_seconds)
    return MockSonarQubeAdapter()


def get_container_scanner() -> ContainerScanner:
    if "container" in _overrides:
        return _overrides["container"]
    s = get_settings()
    if s.trivy_mode == "binary":
        return TrivyBinaryAdapter(s.trivy_binary, s.trivy_timeout_seconds)
    if s.trivy_mode == "docker":
        return TrivyDockerAdapter(s.docker_binary, s.trivy_docker_image, s.trivy_timeout_seconds)
    return MockTrivyAdapter()


def get_image_inspector() -> ImageInspector:
    if "docker" in _overrides:
        return _overrides["docker"]
    s = get_settings()
    if s.docker_mode == "real":
        return DockerCliAdapter(s.docker_binary)
    return MockDockerAdapter()


def get_dependency_auditor() -> DependencyAuditor:
    if "dependency" in _overrides:
        return _overrides["dependency"]
    s = get_settings()
    if s.pip_audit_mode == "real":
        return PipAuditCliAdapter(s.pip_audit_binary, s.pip_audit_timeout_seconds)
    return MockPipAuditAdapter()


def integration_status() -> list[dict[str, Any]]:
    """Non-sensitive description of the active adapters (for the Settings page)."""
    s = get_settings()
    return [
        {
            "name": "GitHub Actions",
            "key": "github",
            "mode": get_ci_provider().mode,
            "configured": s.github_mode == "real",
            "details": s.github_api_url,
            "webhook_secret_configured": bool(s.github_webhook_secret),
        },
        {
            "name": "SonarQube",
            "key": "sonarqube",
            "mode": get_code_quality_provider().mode,
            "configured": bool(s.sonarqube_token) and s.sonarqube_mode == "real",
            "details": s.sonarqube_url,
        },
        {
            "name": "Trivy",
            "key": "trivy",
            "mode": get_container_scanner().mode,
            "configured": s.trivy_mode != "mock",
            "details": s.trivy_docker_image if s.trivy_mode == "docker" else s.trivy_binary,
        },
        {
            "name": "Docker",
            "key": "docker",
            "mode": get_image_inspector().mode,
            "configured": s.docker_mode == "real",
            "details": s.docker_binary,
        },
        {
            "name": "pip-audit",
            "key": "pip_audit",
            "mode": get_dependency_auditor().mode,
            "configured": s.pip_audit_mode == "real",
            "details": s.pip_audit_binary,
        },
    ]
