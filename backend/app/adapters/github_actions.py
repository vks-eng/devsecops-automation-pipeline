"""GitHub Actions / repository adapters.

Real adapter notes
------------------
* Uses the REST API with ``Authorization: Bearer <token>``; the token is decrypted only
  in memory for the duration of a call and is never logged or returned.
* Minimum permissions for a fine-grained PAT: **Actions: read**, **Contents: read**,
  **Metadata: read** on the selected repositories only.
"""

from __future__ import annotations

import hashlib
import random
import re
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import quote

import httpx

from app.adapters.base import AdapterError, RepoAccess
from app.core.validators import ValidationError, validate_branch_name

_SAFE_PATH_RE = re.compile(r"^(?!/)(?!.*\.\.)[A-Za-z0-9._/-]{1,200}$")
_NAME_RE = re.compile(r"^[A-Za-z0-9._-]{1,100}$")


def validate_repo_path(path: str) -> str:
    if not _SAFE_PATH_RE.fullmatch(path):
        raise AdapterError("Repository file path is invalid")
    return path


def _check_names(owner: str, repo: str) -> None:
    if not (_NAME_RE.fullmatch(owner) and _NAME_RE.fullmatch(repo)):
        raise AdapterError("Invalid repository coordinates")


class GitHubActionsAdapter:
    mode = "real"

    def __init__(
        self,
        api_url: str = "https://api.github.com",
        timeout: float = 15.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.api_url = api_url.rstrip("/")
        self.timeout = timeout
        self._transport = transport

    def _client(self, token: str | None) -> httpx.Client:
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "devsecops-automation-platform",
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return httpx.Client(
            base_url=self.api_url,
            headers=headers,
            timeout=self.timeout,
            transport=self._transport,
            follow_redirects=False,
        )

    def _get(self, token: str | None, path: str, **kwargs: Any) -> httpx.Response:
        try:
            with self._client(token) as client:
                response = client.get(path, **kwargs)
        except httpx.HTTPError as exc:
            raise AdapterError(f"GitHub API request failed: {type(exc).__name__}") from exc
        if response.status_code in (401, 403):
            raise AdapterError(f"GitHub API denied access (HTTP {response.status_code})")
        if response.status_code == 404:
            raise AdapterError("GitHub repository or resource not found (or token lacks access)")
        if response.status_code >= 400:
            raise AdapterError(f"GitHub API error (HTTP {response.status_code})")
        return response

    def list_workflow_runs(
        self, owner: str, repo: str, token: str | None, branch: str | None = None, limit: int = 30
    ) -> dict[str, Any]:
        _check_names(owner, repo)
        params: dict[str, Any] = {"per_page": max(1, min(limit, 100))}
        if branch:
            try:
                params["branch"] = validate_branch_name(branch)
            except ValidationError as exc:
                raise AdapterError(str(exc)) from exc
        return self._get(token, f"/repos/{owner}/{repo}/actions/runs", params=params).json()

    def check_repo_access(self, owner: str, repo: str, token: str | None) -> RepoAccess:
        _check_names(owner, repo)
        data = self._get(token, f"/repos/{owner}/{repo}").json()
        perms = data.get("permissions") or {}
        return RepoAccess(
            full_name=data.get("full_name", f"{owner}/{repo}"),
            private=bool(data.get("private")),
            can_read=bool(perms.get("pull", not data.get("private"))),
            permissions={k: bool(v) for k, v in perms.items()},
        )

    def get_file(self, owner: str, repo: str, path: str, ref: str, token: str | None) -> str:
        _check_names(owner, repo)
        validate_repo_path(path)
        try:
            validate_branch_name(ref)
        except ValidationError as exc:
            raise AdapterError(str(exc)) from exc
        response = self._get(
            token,
            f"/repos/{owner}/{repo}/contents/{quote(path)}",
            params={"ref": ref},
            headers={"Accept": "application/vnd.github.raw+json"},
        )
        if len(response.content) > 512_000:
            raise AdapterError("Repository file is too large to audit")
        return response.text


_MOCK_WORKFLOWS = ["CI", "Security Scan", "Build & Push Image", "Release"]
_MOCK_ACTORS = ["alice-dev", "bob-sec", "carol-ops", "dependabot[bot]"]
_MOCK_EVENTS = ["push", "pull_request", "schedule", "workflow_dispatch"]

# (package, vulnerable pin, patched pin) - the mock repo pins one or the other per repo.
MOCK_PINS = [
    ("fastapi", "0.110.0", "0.115.6"),
    ("requests", "2.28.2", "2.32.3"),
    ("jinja2", "3.1.2", "3.1.4"),
    ("flask", "2.2.2", "3.0.3"),
    ("urllib3", "1.26.15", "2.2.3"),
    ("gunicorn", "21.2.0", "23.0.0"),
    ("pyyaml", "5.3.1", "6.0.2"),
    ("werkzeug", "2.2.2", "3.0.6"),
    ("sqlalchemy", "2.0.29", "2.0.36"),
    ("pydantic", "2.6.4", "2.9.2"),
    ("legacy-crypto-helper", "0.3.1", None),
]


def mock_requirements(full_name: str) -> str:
    """Illustrative pinned requirements.txt, deterministic per repository."""
    seed = int(hashlib.sha256(full_name.encode()).hexdigest()[:8], 16)
    rng = random.Random(seed)  # nosec B311 - mock data only  # noqa: S311
    hygiene = 0.3 + (seed % 60) / 100  # share of packages already patched
    lines = ["# Illustrative requirements returned by the mock GitHub adapter"]
    for name, vulnerable, patched in MOCK_PINS:
        if patched is None:
            if rng.random() < 0.4:
                lines.append(f"{name}=={vulnerable}")
            continue
        lines.append(f"{name}=={patched if rng.random() < hygiene else vulnerable}")
    return "\n".join(lines) + "\n"


class MockGitHubActionsAdapter:
    """Deterministic, time-relative workflow history per repository."""

    mode = "mock"

    def list_workflow_runs(
        self, owner: str, repo: str, token: str | None, branch: str | None = None, limit: int = 30
    ) -> dict[str, Any]:
        _check_names(owner, repo)
        full = f"{owner}/{repo}"
        seed = int(hashlib.sha256(full.encode()).hexdigest()[:8], 16)
        failure_rate = 0.05 + (seed % 25) / 100  # 5% .. 29% per repo
        slot_hours = 5
        now = datetime.now(UTC).replace(minute=0, second=0, microsecond=0)
        current_slot = int(now.timestamp()) // (slot_hours * 3600)
        runs: list[dict[str, Any]] = []
        for i in range(min(limit, 100)):
            slot = current_slot - i
            rng = random.Random(seed * 100_003 + slot)  # nosec B311 - mock data only  # noqa: S311
            started = datetime.fromtimestamp(slot * slot_hours * 3600, UTC) + timedelta(
                minutes=rng.randint(0, 240)
            )
            if started > datetime.now(UTC):
                started = datetime.now(UTC) - timedelta(minutes=5)
            duration = rng.randint(90, 1100)
            run_branch = branch or rng.choice(["main", "main", "main", "develop", "feature/api"])
            in_progress = i == 0 and rng.random() < 0.3
            conclusion = None
            if not in_progress:
                roll = rng.random()
                conclusion = (
                    "failure"
                    if roll < failure_rate
                    else "cancelled"
                    if roll < failure_rate + 0.03
                    else "success"
                )
            run_id = 9_000_000_000 + (seed % 1_000_000) * 10_000 + (slot % 10_000)
            runs.append(
                {
                    "id": run_id,
                    "name": rng.choice(_MOCK_WORKFLOWS),
                    "head_branch": run_branch,
                    "head_sha": hashlib.sha1(  # nosec B324 - fake commit sha for mock data  # noqa: S324
                        f"{full}:{slot}".encode()
                    ).hexdigest(),
                    "event": rng.choice(_MOCK_EVENTS),
                    "status": "in_progress" if in_progress else "completed",
                    "conclusion": conclusion,
                    "html_url": f"https://github.com/{full}/actions/runs/{run_id}",
                    "run_started_at": started.isoformat().replace("+00:00", "Z"),
                    "created_at": started.isoformat().replace("+00:00", "Z"),
                    "updated_at": (started + timedelta(seconds=duration))
                    .isoformat()
                    .replace("+00:00", "Z"),
                    "actor": {"login": rng.choice(_MOCK_ACTORS)},
                }
            )
        return {"total_count": len(runs), "workflow_runs": runs}

    def check_repo_access(self, owner: str, repo: str, token: str | None) -> RepoAccess:
        _check_names(owner, repo)
        return RepoAccess(
            full_name=f"{owner}/{repo}",
            private=False,
            can_read=True,
            permissions={"pull": True, "push": False, "admin": False},
        )

    def get_file(self, owner: str, repo: str, path: str, ref: str, token: str | None) -> str:
        _check_names(owner, repo)
        validate_repo_path(path)
        if not path.endswith(".txt"):
            raise AdapterError("Mock repository only contains requirements*.txt files")
        return mock_requirements(f"{owner}/{repo}")
