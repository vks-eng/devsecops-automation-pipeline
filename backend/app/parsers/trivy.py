"""Parser for Trivy ``--format json`` output (schema version 2)."""

from __future__ import annotations

from typing import Any

from app.parsers.common import ParsedFinding, ParsedScan, ParseError, truncate

_SEVERITY_MAP = {
    "CRITICAL": "critical",
    "HIGH": "high",
    "MEDIUM": "medium",
    "LOW": "low",
    "UNKNOWN": "info",
}


def classify_trivy_severity(raw: str | None) -> str:
    return _SEVERITY_MAP.get((raw or "UNKNOWN").upper(), "info")


def _recommendation(pkg: str, installed: str, fixed: str | None, target_class: str) -> str:
    if fixed:
        first_fix = fixed.split(",")[0].strip()
        if target_class == "os-pkgs":
            return (
                f"Rebuild on an updated base image or upgrade OS package {pkg} "
                f"from {installed} to {first_fix}."
            )
        return f"Upgrade {pkg} from {installed} to {first_fix} or later and rebuild the image."
    return (
        f"No fixed version of {pkg} is available yet. Assess exploitability, consider a "
        "smaller or distroless base image, and monitor the advisory."
    )


def parse_trivy_report(report: dict[str, Any]) -> ParsedScan:
    if not isinstance(report, dict):
        raise ParseError("Trivy report must be a JSON object")
    results = report.get("Results") or []
    if not isinstance(results, list):
        raise ParseError("Trivy report 'Results' must be a list")

    parsed = ParsedScan()
    metadata = report.get("Metadata") or {}
    os_info = metadata.get("OS") or {}
    targets: list[dict[str, Any]] = []
    parsed.metadata = {
        "artifact_name": report.get("ArtifactName"),
        "artifact_type": report.get("ArtifactType"),
        "schema_version": report.get("SchemaVersion"),
        "os": f"{os_info.get('Family', '')} {os_info.get('Name', '')}".strip() or None,
        "image_id": metadata.get("ImageID"),
        "repo_digests": metadata.get("RepoDigests") or [],
        "targets": targets,
    }

    seen: set[tuple[str, str, str]] = set()
    for result in results:
        if not isinstance(result, dict):
            raise ParseError("Trivy result entries must be objects")
        target = str(result.get("Target", ""))
        target_class = str(result.get("Class", ""))
        vulns = result.get("Vulnerabilities") or []
        targets.append(
            {
                "target": target,
                "class": target_class,
                "type": result.get("Type"),
                "vulnerabilities": len(vulns),
            }
        )
        for vuln in vulns:
            vuln_id = str(vuln.get("VulnerabilityID") or "UNKNOWN")
            pkg = str(vuln.get("PkgName") or "unknown")
            installed = str(vuln.get("InstalledVersion") or "")
            key = (vuln_id, pkg, installed)
            if key in seen:  # the same CVE can be reported for several targets
                continue
            seen.add(key)
            fixed = vuln.get("FixedVersion") or None
            parsed.findings.append(
                ParsedFinding(
                    category="container",
                    severity=classify_trivy_severity(vuln.get("Severity")),
                    rule_id=truncate(vuln_id, 200),
                    title=truncate(vuln.get("Title") or f"{vuln_id} in {pkg}", 500),
                    description=truncate(vuln.get("Description") or "", 4000),
                    component=truncate(pkg, 500),
                    installed_version=truncate(installed, 100) or None,
                    fixed_version=truncate(fixed, 200) if fixed else None,
                    file_path=truncate(target, 500) or None,
                    reference_url=truncate(vuln.get("PrimaryURL"), 500) or None,
                    recommendation=_recommendation(pkg, installed, fixed, target_class),
                )
            )
    return parsed
