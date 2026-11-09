"""Parser for ``pip-audit --format json`` output.

pip-audit reports vulnerabilities per dependency but does NOT include a severity rating.
Severity is therefore resolved as follows (documented in docs/security-score.md):

1. an explicit ``severity`` field on the vulnerability entry, if an enrichment step added one;
2. otherwise ``medium`` when a fixed version exists, and ``high`` when no fix is available
   (an unfixable known vulnerability cannot be remediated by simply upgrading).
"""

from __future__ import annotations

from typing import Any

from app.parsers.common import (
    SEVERITIES,
    ParsedDependency,
    ParsedFinding,
    ParsedScan,
    ParseError,
    truncate,
)


def classify_pip_audit_severity(vuln: dict[str, Any]) -> str:
    explicit = str(vuln.get("severity") or "").lower()
    if explicit in SEVERITIES:
        return explicit
    if explicit == "moderate":
        return "medium"
    return "medium" if vuln.get("fix_versions") else "high"


def parse_pip_audit_report(report: dict[str, Any] | list[Any]) -> ParsedScan:
    # pip-audit >= 2.5 emits {"dependencies": [...], "fixes": [...]};
    # older versions emitted a bare list of dependencies.
    if isinstance(report, list):
        dependencies: Any = report
    elif isinstance(report, dict):
        dependencies = report.get("dependencies")
        if not isinstance(dependencies, list):
            raise ParseError("pip-audit report must contain a 'dependencies' list")
    else:
        raise ParseError("pip-audit report must be a JSON object")

    parsed = ParsedScan()
    skipped: list[dict[str, str]] = []
    for dep in dependencies:
        if not isinstance(dep, dict) or "name" not in dep:
            raise ParseError("pip-audit dependency entries must be objects with a name")
        name = truncate(dep["name"], 200)
        version = truncate(dep.get("version") or "", 100)
        if dep.get("skip_reason"):
            skipped.append({"name": name, "reason": truncate(dep["skip_reason"], 300)})
        vulns = dep.get("vulns") or []
        parsed.dependencies.append(
            ParsedDependency(name=name, version=version, vulnerability_count=len(vulns))
        )
        for vuln in vulns:
            vuln_id = str(vuln.get("id") or "UNKNOWN")
            fixes = [str(v) for v in (vuln.get("fix_versions") or [])]
            aliases = [str(a) for a in (vuln.get("aliases") or [])]
            cve = next((a for a in aliases if a.startswith("CVE-")), None)
            title = f"{vuln_id} in {name} {version}" + (f" ({cve})" if cve else "")
            if fixes:
                rec = f"Upgrade {name} from {version} to {fixes[0]} or later and re-lock."
            else:
                rec = (
                    f"No fixed release of {name} is available. Evaluate replacing the package, "
                    "pinning to an unaffected version, or applying a compensating control."
                )
            ref = (
                f"https://osv.dev/vulnerability/{vuln_id}"
                if vuln_id.startswith(("PYSEC-", "GHSA-"))
                else None
            )
            parsed.findings.append(
                ParsedFinding(
                    category="dependency",
                    severity=classify_pip_audit_severity(vuln),
                    rule_id=truncate(vuln_id, 200),
                    title=truncate(title, 500),
                    description=truncate(vuln.get("description") or "", 4000),
                    component=name,
                    installed_version=version or None,
                    fixed_version=truncate(", ".join(fixes), 200) or None,
                    reference_url=ref,
                    recommendation=rec,
                )
            )
    parsed.metadata = {
        "dependency_count": len(parsed.dependencies),
        "vulnerable_dependency_count": sum(1 for d in parsed.dependencies if d.vulnerability_count),
        "skipped": skipped,
        "fixes": report.get("fixes", []) if isinstance(report, dict) else [],
    }
    return parsed
