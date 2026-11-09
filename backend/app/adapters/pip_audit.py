"""pip-audit dependency auditing adapters.

Requirements content comes from a repository (untrusted). Before anything is written to
disk it is reduced to *pinned* ``name==version`` lines; every pip option line
(``-r``, ``-e``, ``--index-url``, ``--extra-index-url``, ``-f`` ...), URL/VCS
requirements and local paths are rejected. pip-audit is then invoked with
``--no-deps --disable-pip`` so it never installs or builds anything.
"""

from __future__ import annotations

import json
import re
from typing import Any

from packaging.version import InvalidVersion, Version

from app.adapters.base import AdapterError
from app.adapters.mock_data import load_mock_json
from app.adapters.process import ephemeral_workspace, minimal_env, resolve_binary, run_fixed_argv

_PINNED_RE = re.compile(
    r"^(?P<name>[A-Za-z0-9](?:[A-Za-z0-9._-]{0,98}[A-Za-z0-9])?)"
    r"(?:\[[A-Za-z0-9,._ -]{1,100}\])?"
    r"\s*==\s*(?P<version>[A-Za-z0-9.+!_-]{1,50})"
    r"(?:\s*;\s*[A-Za-z0-9_ .'\"<>=!(),-]{1,200})?$"
)
MAX_REQUIREMENTS = 2000


def sanitize_requirements(text: str) -> list[tuple[str, str]]:
    """Return ``[(name, version)]`` for pinned requirements; raise on anything unsafe."""
    if len(text) > 512_000:
        raise AdapterError("requirements file is too large")
    pins: list[tuple[str, str]] = []
    for lineno, raw in enumerate(text.splitlines(), start=1):
        line = raw.split(" #", 1)[0].strip()
        if not line or line.startswith("#"):
            continue
        if line.endswith("\\"):
            raise AdapterError(f"line {lineno}: line continuations (hashes) are not supported")
        if line.startswith("-"):
            raise AdapterError(f"line {lineno}: pip options are not allowed in audited files")
        match = _PINNED_RE.fullmatch(line)
        if not match:
            raise AdapterError(f"line {lineno}: only pinned 'name==version' requirements allowed")
        pins.append((match.group("name"), match.group("version")))
        if len(pins) > MAX_REQUIREMENTS:
            raise AdapterError("too many requirements")
    return pins


class PipAuditCliAdapter:
    mode = "real"

    def __init__(self, binary: str = "pip-audit", timeout: int = 300) -> None:
        self.binary = binary
        self.timeout = timeout

    @staticmethod
    def build_argv(binary_path: str, requirements_path: str, output_path: str) -> list[str]:
        return [
            binary_path,
            "--requirement",
            requirements_path,
            "--format",
            "json",
            "--output",
            output_path,
            "--progress-spinner",
            "off",
            "--no-deps",
            "--disable-pip",
        ]

    def audit_requirements(self, requirements_text: str) -> dict[str, Any]:
        pins = sanitize_requirements(requirements_text)
        if not pins:
            return {"dependencies": [], "fixes": []}
        binary_path = resolve_binary(self.binary)
        with ephemeral_workspace() as work:
            req = work / "requirements.txt"
            out = work / "report.json"
            req.write_text("".join(f"{n}=={v}\n" for n, v in pins), encoding="utf-8")
            # pip-audit exits 1 when vulnerabilities are found - that is not an error.
            run_fixed_argv(
                self.build_argv(binary_path, str(req), str(out)),
                cwd=work,
                timeout=self.timeout,
                env=minimal_env(work),
                allowed_returncodes=(0, 1),
            )
            try:
                return json.loads(out.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise AdapterError("pip-audit did not produce a valid JSON report") from exc


def _is_affected(version: str, advisory: dict[str, Any]) -> bool:
    try:
        v = Version(version)
        fixed = advisory.get("fixed_in")
        introduced = advisory.get("introduced")
        if introduced and v < Version(introduced):
            return False
        return v < Version(fixed) if fixed else True
    except InvalidVersion:
        return False


class MockPipAuditAdapter:
    """Matches pinned requirements against a small built-in advisory table and emits
    output in exactly the same JSON format as ``pip-audit --format json``."""

    mode = "mock"

    def audit_requirements(self, requirements_text: str) -> dict[str, Any]:
        pins = sanitize_requirements(requirements_text)
        advisories: dict[str, list[dict[str, Any]]] = load_mock_json("pip_audit_advisories.json")
        dependencies: list[dict[str, Any]] = []
        fixes: list[dict[str, Any]] = []
        for name, version in pins:
            canonical = re.sub(r"[-_.]+", "-", name).lower()
            vulns = []
            for adv in advisories.get(canonical, []):
                if _is_affected(version, adv):
                    vulns.append(
                        {
                            "id": adv["id"],
                            "fix_versions": [adv["fixed_in"]] if adv.get("fixed_in") else [],
                            "aliases": adv.get("aliases", []),
                            "description": adv.get("description", ""),
                        }
                    )
            dependencies.append({"name": canonical, "version": version, "vulns": vulns})
            if vulns and all(v["fix_versions"] for v in vulns):
                newest = max((v["fix_versions"][0] for v in vulns), key=Version)
                fixes.append({"name": canonical, "old_version": version, "new_version": newest})
        return {"dependencies": dependencies, "fixes": fixes}
