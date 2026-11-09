"""Scan orchestration: create -> (background) execute adapter -> parse -> persist -> notify."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.adapters import registry
from app.adapters.base import AdapterError
from app.adapters.github_actions import validate_repo_path
from app.core.validators import (
    ValidationError,
    validate_branch_name,
    validate_image_ref,
    validate_sonar_project_key,
)
from app.models import (
    DependencyItem,
    Finding,
    NotificationType,
    Project,
    Scan,
    ScanStatus,
    ScanType,
    ScoreSnapshot,
)
from app.parsers.common import SEVERITIES, ParsedScan, ParseError
from app.parsers.pip_audit import parse_pip_audit_report
from app.parsers.sonarqube import parse_sonar_results
from app.parsers.trivy import parse_trivy_report
from app.services import credentials
from app.services.notifications import notify_project
from app.services.scoring import project_security_overview

logger = logging.getLogger(__name__)


class ScanRequestError(ValueError):
    """The scan request is invalid for this project."""


def resolve_target(project: Project, scan_type: ScanType, target: str | None) -> str:
    """Validate the requested scan target against the project's registered configuration.

    Only *registered* targets can be scanned: images must be listed in the project's
    ``container_images`` and branches must be configured for the project. This prevents
    the platform from being used to scan arbitrary third-party artifacts.
    """
    try:
        if scan_type == ScanType.CONTAINER:
            if not target:
                if not project.container_images:
                    raise ScanRequestError("Project has no registered container images")
                target = project.container_images[0]
            validate_image_ref(target)
            if target not in project.container_images:
                raise ScanRequestError("Image is not registered for this project")
            return target
        branch = target or project.default_branch
        validate_branch_name(branch)
        if branch not in {project.default_branch, *project.branches}:
            raise ScanRequestError("Branch is not configured for this project")
        if scan_type == ScanType.CODE_QUALITY:
            if not project.sonar_project_key:
                raise ScanRequestError("Project has no SonarQube project key configured")
            validate_sonar_project_key(project.sonar_project_key)
        return branch
    except ValidationError as exc:
        raise ScanRequestError(str(exc)) from exc


def create_scan(
    db: Session,
    project: Project,
    scan_type: ScanType,
    target: str | None,
    user_id: int | None,
    trigger: str = "manual",
) -> Scan:
    resolved = resolve_target(project, scan_type, target)
    scan = Scan(
        project_id=project.id,
        scan_type=scan_type.value,
        target=resolved,
        status=ScanStatus.PENDING.value,
        triggered_by_id=user_id,
        trigger=trigger,
    )
    db.add(scan)
    db.commit()
    return scan


def _run_adapter(db: Session, project: Project, scan: Scan) -> tuple[ParsedScan, str, dict]:
    extra: dict[str, Any] = {}
    if scan.scan_type == ScanType.CONTAINER.value:
        scanner = registry.get_container_scanner()
        inspector = registry.get_image_inspector()
        meta = inspector.inspect_image(scan.target)
        extra["image"] = {
            "digest": meta.digest,
            "size_bytes": meta.size_bytes,
            "os": meta.os,
            "architecture": meta.architecture,
            "available_locally": meta.available_locally,
        }
        return parse_trivy_report(scanner.scan_image(scan.target)), scanner.mode, extra
    if scan.scan_type == ScanType.DEPENDENCY.value:
        ci = registry.get_ci_provider()
        auditor = registry.get_dependency_auditor()
        path = validate_repo_path(
            str(project.scan_config.get("requirements_path", "requirements.txt"))
        )
        token = credentials.get_token(db, project.id, "github")
        requirements = ci.get_file(project.repo_owner, project.repo_name, path, scan.target, token)
        extra["requirements_path"] = path
        return parse_pip_audit_report(auditor.audit_requirements(requirements)), auditor.mode, extra
    if scan.scan_type == ScanType.CODE_QUALITY.value:
        provider = registry.get_code_quality_provider()
        raw = provider.fetch_project_analysis(str(project.sonar_project_key), scan.target)
        parsed = parse_sonar_results(raw["issues"], raw["quality_gate"], raw.get("measures"))
        return parsed, provider.mode, extra
    raise ScanRequestError(f"Unsupported scan type {scan.scan_type}")


def persist_results(db: Session, project: Project, scan: Scan, parsed: ParsedScan) -> None:
    db.execute(delete(Finding).where(Finding.scan_id == scan.id))
    db.execute(delete(DependencyItem).where(DependencyItem.scan_id == scan.id))
    for f in parsed.findings:
        db.add(
            Finding(
                scan_id=scan.id,
                project_id=project.id,
                category=f.category,
                finding_type=f.finding_type,
                severity=f.severity,
                rule_id=f.rule_id,
                title=f.title,
                description=f.description,
                component=f.component,
                installed_version=f.installed_version,
                fixed_version=f.fixed_version,
                file_path=f.file_path,
                line=f.line,
                reference_url=f.reference_url,
                recommendation=f.recommendation,
            )
        )
    for d in parsed.dependencies:
        db.add(
            DependencyItem(
                scan_id=scan.id,
                project_id=project.id,
                name=d.name,
                version=d.version,
                ecosystem=d.ecosystem,
                vulnerable=d.vulnerability_count > 0,
                vulnerability_count=d.vulnerability_count,
            )
        )
    # Severity counts cover security-relevant findings (vulnerabilities and bugs);
    # code smells are tracked separately so they do not distort security metrics.
    security = [f for f in parsed.findings if f.finding_type != "code_smell"]
    counts = {s: sum(1 for f in security if f.severity == s) for s in SEVERITIES}
    scan.summary = {
        **counts,
        "total": sum(counts.values()),
        "code_smells": len(parsed.findings) - len(security),
    }
    scan.quality_gate_status = parsed.quality_gate_status
    scan.metadata_json = {**(scan.metadata_json or {}), **parsed.metadata}
    scan.status = ScanStatus.COMPLETED.value
    scan.completed_at = datetime.now(UTC)
    scan.error = None


def _after_completion(db: Session, project: Project, scan: Scan) -> None:
    counts = scan.summary or {}
    label = scan.scan_type.replace("_", " ")
    link = f"/projects/{project.id}?scan={scan.id}"
    notify_project(
        db,
        project,
        NotificationType.SCAN_COMPLETED,
        f"{label.title()} scan completed for {project.name}",
        f"Target {scan.target}: {counts.get('critical', 0)} critical, {counts.get('high', 0)} "
        f"high, {counts.get('medium', 0)} medium, {counts.get('low', 0)} low findings.",
        "info",
        link,
    )
    if counts.get("critical", 0) > 0:
        notify_project(
            db,
            project,
            NotificationType.CRITICAL_VULNERABILITY,
            f"{counts['critical']} critical finding(s) in {project.name}",
            f"The latest {label} scan of {scan.target} reported critical issues. "
            "Review remediation recommendations in the report.",
            "critical",
            link,
        )
    if scan.quality_gate_status == "failed":
        notify_project(
            db,
            project,
            NotificationType.CRITICAL_VULNERABILITY,
            f"Quality gate failed for {project.name}",
            f"SonarQube quality gate failed on branch {scan.target}.",
            "high",
            link,
        )
    overview = project_security_overview(db, project)
    db.add(
        ScoreSnapshot(
            project_id=project.id,
            score=overview["score"],
            grade=overview["grade"],
            counts=overview["counts"],
        )
    )


def execute_scan(db: Session, scan_id: int) -> Scan | None:
    scan = db.get(Scan, scan_id)
    if scan is None or scan.status not in (ScanStatus.PENDING.value, ScanStatus.FAILED.value):
        return scan
    project = db.get(Project, scan.project_id)
    if project is None:
        return None
    scan.status = ScanStatus.RUNNING.value
    scan.started_at = datetime.now(UTC)
    db.commit()
    try:
        parsed, mode, extra = _run_adapter(db, project, scan)
        scan.adapter_mode = mode
        scan.metadata_json = extra
        persist_results(db, project, scan, parsed)
        db.flush()
        _after_completion(db, project, scan)
        db.commit()
    except (AdapterError, ParseError, ScanRequestError) as exc:
        db.rollback()
        scan = db.get(Scan, scan_id)
        if scan is None:  # deleted concurrently
            return None
        scan.status = ScanStatus.FAILED.value
        scan.error = str(exc)[:2000]
        scan.completed_at = datetime.now(UTC)
        notify_project(
            db,
            project,
            NotificationType.SCAN_FAILED,
            f"{scan.scan_type.replace('_', ' ').title()} scan failed for {project.name}",
            scan.error,
            "high",
            f"/projects/{project.id}?scan={scan.id}",
        )
        db.commit()
        logger.warning("Scan %s failed: %s", scan_id, scan.error)
    return scan


def import_scan_report(
    db: Session,
    project: Project,
    scan_type: ScanType,
    target: str | None,
    report: dict[str, Any] | list[Any],
    user_id: int | None,
) -> Scan:
    """Ingest a report produced elsewhere (e.g. Trivy / pip-audit run in GitHub Actions)."""
    if scan_type == ScanType.CODE_QUALITY:
        raise ScanRequestError("Code quality results are pulled from SonarQube, not imported")
    resolved = resolve_target(project, scan_type, target)
    parsed = (
        parse_trivy_report(report)  # type: ignore[arg-type]
        if scan_type == ScanType.CONTAINER
        else parse_pip_audit_report(report)
    )
    now = datetime.now(UTC)
    scan = Scan(
        project_id=project.id,
        scan_type=scan_type.value,
        target=resolved,
        status=ScanStatus.RUNNING.value,
        triggered_by_id=user_id,
        trigger="import",
        adapter_mode="import",
        started_at=now,
    )
    db.add(scan)
    db.flush()
    persist_results(db, project, scan, parsed)
    db.flush()
    _after_completion(db, project, scan)
    db.commit()
    return scan
