"""SonarQube Web API adapters (issues, quality gate, measures)."""

from __future__ import annotations

import hashlib
import random
from typing import Any

import httpx

from app.adapters.base import AdapterError
from app.adapters.mock_data import load_mock_json
from app.core.validators import ValidationError, validate_branch_name, validate_sonar_project_key

MEASURE_KEYS = (
    "coverage,duplicated_lines_density,ncloc,bugs,vulnerabilities,code_smells,"
    "security_hotspots,reliability_rating,security_rating,sqale_rating"
)


class SonarQubeAdapter:
    """Talks to a SonarQube server using a user/project analysis token (Bearer auth).

    The token only needs *Browse* permission on the target projects.
    """

    mode = "real"
    max_pages = 10
    page_size = 500

    def __init__(
        self,
        base_url: str,
        token: str,
        timeout: float = 15.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        if not base_url.startswith(("http://", "https://")):
            raise AdapterError("SONARQUBE_URL must be an http(s) URL")
        self.base_url = base_url.rstrip("/")
        self._token = token
        self.timeout = timeout
        self._transport = transport

    def _get(self, client: httpx.Client, path: str, params: dict[str, Any]) -> dict[str, Any]:
        try:
            response = client.get(path, params=params)
        except httpx.HTTPError as exc:
            raise AdapterError(f"SonarQube request failed: {type(exc).__name__}") from exc
        if response.status_code in (401, 403):
            raise AdapterError(f"SonarQube denied access (HTTP {response.status_code})")
        if response.status_code == 404:
            raise AdapterError("SonarQube project not found")
        if response.status_code >= 400:
            raise AdapterError(f"SonarQube API error (HTTP {response.status_code})")
        return response.json()

    def fetch_project_analysis(self, project_key: str, branch: str | None) -> dict[str, Any]:
        try:
            validate_sonar_project_key(project_key)
            if branch:
                validate_branch_name(branch)
        except ValidationError as exc:
            raise AdapterError(str(exc)) from exc
        headers = {"Authorization": f"Bearer {self._token}"} if self._token else {}
        branch_param = {"branch": branch} if branch else {}
        with httpx.Client(
            base_url=self.base_url,
            headers=headers,
            timeout=self.timeout,
            transport=self._transport,
            follow_redirects=False,
        ) as client:
            issues: list[dict[str, Any]] = []
            total = 0
            for page in range(1, self.max_pages + 1):
                payload = self._get(
                    client,
                    "/api/issues/search",
                    {
                        "componentKeys": project_key,
                        "resolved": "false",
                        "ps": self.page_size,
                        "p": page,
                        **branch_param,
                    },
                )
                issues.extend(payload.get("issues", []))
                total = int(payload.get("total", payload.get("paging", {}).get("total", 0)))
                if len(issues) >= total or not payload.get("issues"):
                    break
            gate = self._get(
                client,
                "/api/qualitygates/project_status",
                {"projectKey": project_key, **branch_param},
            )
            measures = self._get(
                client,
                "/api/measures/component",
                {"component": project_key, "metricKeys": MEASURE_KEYS, **branch_param},
            )
        return {
            "issues": {"total": total, "issues": issues},
            "quality_gate": gate,
            "measures": measures,
        }


class MockSonarQubeAdapter:
    mode = "mock"

    def fetch_project_analysis(self, project_key: str, branch: str | None) -> dict[str, Any]:
        try:
            validate_sonar_project_key(project_key)
        except ValidationError as exc:
            raise AdapterError(str(exc)) from exc
        catalogue = load_mock_json("sonarqube_catalogue.json")
        seed = int(hashlib.sha256(project_key.encode()).hexdigest()[:12], 16)
        rng = random.Random(seed)  # nosec B311 - deterministic mock data  # noqa: S311
        issues = []
        for idx, template in enumerate(catalogue["issues"]):
            if rng.random() < 0.6:
                issue = dict(template)
                issue["key"] = f"AY{seed % 10_000_000:07d}{idx:03d}"
                issue["component"] = f"{project_key}:{template['component']}"
                issue["project"] = project_key
                issues.append(issue)
        blocking = any(
            i.get("type") in ("VULNERABILITY", "BUG")
            and i.get("severity") in ("BLOCKER", "CRITICAL")
            for i in issues
        )
        coverage = round(55 + rng.random() * 40, 1)
        dup = round(rng.random() * 8, 1)
        gate = {
            "projectStatus": {
                "status": "ERROR" if blocking or coverage < 70 else "OK",
                "conditions": [
                    {
                        "status": "ERROR" if blocking else "OK",
                        "metricKey": "new_security_rating",
                        "comparator": "GT",
                        "errorThreshold": "1",
                        "actualValue": "4" if blocking else "1",
                    },
                    {
                        "status": "ERROR" if coverage < 70 else "OK",
                        "metricKey": "new_coverage",
                        "comparator": "LT",
                        "errorThreshold": "70",
                        "actualValue": str(coverage),
                    },
                    {
                        "status": "OK",
                        "metricKey": "new_duplicated_lines_density",
                        "comparator": "GT",
                        "errorThreshold": "10",
                        "actualValue": str(dup),
                    },
                ],
            }
        }
        counts = {
            t: sum(1 for i in issues if i.get("type") == t)
            for t in ("BUG", "VULNERABILITY", "CODE_SMELL")
        }
        measures = {
            "component": {
                "key": project_key,
                "measures": [
                    {"metric": "coverage", "value": str(coverage)},
                    {"metric": "duplicated_lines_density", "value": str(dup)},
                    {"metric": "ncloc", "value": str(3000 + seed % 40000)},
                    {"metric": "bugs", "value": str(counts["BUG"])},
                    {"metric": "vulnerabilities", "value": str(counts["VULNERABILITY"])},
                    {"metric": "code_smells", "value": str(counts["CODE_SMELL"])},
                ],
            }
        }
        return {
            "issues": {"total": len(issues), "issues": issues},
            "quality_gate": gate,
            "measures": measures,
        }
