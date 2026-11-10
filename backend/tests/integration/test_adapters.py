from __future__ import annotations

import json
import sys
from pathlib import Path

import httpx
import pytest

from app.adapters import registry
from app.adapters.base import AdapterError
from app.adapters.docker import DockerCliAdapter, MockDockerAdapter
from app.adapters.github_actions import (
    GitHubActionsAdapter,
    MockGitHubActionsAdapter,
    validate_repo_path,
)
from app.adapters.pip_audit import MockPipAuditAdapter, PipAuditCliAdapter, sanitize_requirements
from app.adapters.process import ephemeral_workspace, minimal_env, run_fixed_argv
from app.adapters.sonarqube import MockSonarQubeAdapter, SonarQubeAdapter
from app.adapters.trivy import MockTrivyAdapter, TrivyBinaryAdapter, TrivyDockerAdapter
from app.parsers.github import parse_workflow_runs
from app.parsers.pip_audit import parse_pip_audit_report
from app.parsers.sonarqube import parse_sonar_results
from app.parsers.trivy import parse_trivy_report
from tests.conftest import load_fixture

# ----------------------------------------------------------------------------- argv safety


def test_trivy_binary_argv_is_fixed_list(tmp_path: Path) -> None:
    argv = TrivyBinaryAdapter(timeout=120).build_argv(
        "/usr/bin/trivy", "ghcr.io/acme/app:1.0", tmp_path / "r.json", tmp_path / "c"
    )
    assert argv[:2] == ["/usr/bin/trivy", "image"]
    assert argv[-2:] == ["--", "ghcr.io/acme/app:1.0"]
    assert "--format" in argv and argv[argv.index("--format") + 1] == "json"
    assert all(isinstance(a, str) for a in argv)


def test_trivy_docker_argv_is_hardened(tmp_path: Path) -> None:
    argv = TrivyDockerAdapter().build_argv("/usr/bin/docker", "nginx:1.27", tmp_path)
    for flag in ("--rm", "--read-only", "--cap-drop", "ALL", "no-new-privileges"):
        assert flag in argv
    assert argv[-2:] == ["--", "nginx:1.27"]


@pytest.mark.parametrize("bad", ["nginx;id", "--privileged", "$(id)", "a b"])
def test_scanners_reject_unsafe_image_refs(bad: str, tmp_path: Path) -> None:
    with pytest.raises(AdapterError):
        TrivyBinaryAdapter().scan_image(bad)
    with pytest.raises(AdapterError):
        TrivyDockerAdapter().build_argv("docker", bad, tmp_path)
    with pytest.raises(AdapterError):
        MockTrivyAdapter().scan_image(bad)
    with pytest.raises(AdapterError):
        DockerCliAdapter().inspect_image(bad)


def test_docker_and_pip_audit_argv() -> None:
    assert DockerCliAdapter.build_argv("docker", "nginx:1") == [
        "docker",
        "image",
        "inspect",
        "--format",
        "{{json .}}",
        "--",
        "nginx:1",
    ]
    argv = PipAuditCliAdapter.build_argv("pip-audit", "/tmp/r.txt", "/tmp/o.json")
    assert "--no-deps" in argv and "--disable-pip" in argv
    assert argv[argv.index("--requirement") + 1] == "/tmp/r.txt"


def test_missing_binary_raises_adapter_error() -> None:
    with pytest.raises(AdapterError, match="not found"):
        TrivyBinaryAdapter(binary="definitely-not-a-real-trivy-binary").scan_image("nginx:1")
    with pytest.raises(AdapterError, match="not found"):
        PipAuditCliAdapter(binary="definitely-not-pip-audit").audit_requirements("x==1\n")


def test_run_fixed_argv_never_uses_a_shell(tmp_path: Path) -> None:
    with pytest.raises(AdapterError):
        run_fixed_argv("echo hi", cwd=tmp_path, timeout=5, env={})  # type: ignore[arg-type]
    # Shell metacharacters are passed literally as a single argument.
    result = run_fixed_argv(
        [sys.executable, "-c", "import sys; print(sys.argv[1])", "x; echo pwned"],
        cwd=tmp_path,
        timeout=30,
        env=minimal_env(tmp_path),
    )
    assert result.stdout.strip() == "x; echo pwned"
    with pytest.raises(AdapterError, match="exited with code 3"):
        run_fixed_argv(
            [sys.executable, "-c", "import sys; sys.exit(3)"],
            cwd=tmp_path,
            timeout=30,
            env=minimal_env(tmp_path),
        )
    with pytest.raises(AdapterError, match="timed out"):
        run_fixed_argv(
            [sys.executable, "-c", "import time; time.sleep(5)"],
            cwd=tmp_path,
            timeout=1,
            env=minimal_env(tmp_path),
        )


def test_minimal_env_excludes_secrets(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_secret")
    monkeypatch.setenv("DATABASE_URL", "postgresql://x")
    env = minimal_env(tmp_path)
    assert "GITHUB_TOKEN" not in env and "DATABASE_URL" not in env
    assert env["HOME"] == str(tmp_path)


def test_ephemeral_workspace_is_removed() -> None:
    with ephemeral_workspace() as work:
        (work / "f.txt").write_text("x")
        path = work
    assert not path.exists()


# ----------------------------------------------------------------------------- requirements


def test_sanitize_requirements_accepts_pins() -> None:
    text = (
        "# comment\nrequests==2.31.0\nJinja2[i18n] == 3.1.4 ; python_version >= '3.8'\n\n"
        "urllib3==2.2.3  # trailing\n"
    )
    assert sanitize_requirements(text) == [
        ("requests", "2.31.0"),
        ("Jinja2", "3.1.4"),
        ("urllib3", "2.2.3"),
    ]


@pytest.mark.parametrize(
    "line",
    [
        "--index-url https://evil.example/simple",
        "-e git+https://github.com/x/y#egg=y",
        "-r other.txt",
        "--extra-index-url=https://evil",
        "requests>=2.0",
        "requests",
        "git+https://github.com/x/y",
        "./local/path",
        "https://evil.example/pkg.whl",
        "requests==2.0 \\",
    ],
)
def test_sanitize_requirements_rejects_unsafe(line: str) -> None:
    with pytest.raises(AdapterError):
        sanitize_requirements(f"fastapi==0.115.0\n{line}\n")


def test_mock_pip_audit_matches_advisories() -> None:
    report = MockPipAuditAdapter().audit_requirements(
        "requests==2.28.2\njinja2==3.1.4\nlegacy-crypto-helper==0.3.1\nunknown==1.0\n"
    )
    parsed = parse_pip_audit_report(report)
    ids = {f.rule_id for f in parsed.findings}
    assert {"GHSA-j8r2-6x86-q33q", "GHSA-9wx4-h78v-vm56", "PYSEC-0000-DEMO"} <= ids
    assert not any(f.component == "jinja2" for f in parsed.findings)  # patched version
    assert len(parsed.dependencies) == 4
    assert report["fixes"] == [
        {"name": "requests", "old_version": "2.28.2", "new_version": "2.32.0"}
    ]


# ----------------------------------------------------------------------------- mocks


def test_mock_trivy_is_deterministic_and_parseable() -> None:
    a = MockTrivyAdapter().scan_image("ghcr.io/acme/app:1.0")
    b = MockTrivyAdapter().scan_image("ghcr.io/acme/app:1.0")
    assert a == b
    parsed = parse_trivy_report(a)
    assert parsed.metadata["artifact_name"] == "ghcr.io/acme/app:1.0"
    hardened = parse_trivy_report(
        MockTrivyAdapter().scan_image("gcr.io/distroless/python3-debian12:nonroot")
    )
    assert (
        len(hardened.findings)
        <= len(parse_trivy_report(MockTrivyAdapter().scan_image("python:3.11-slim")).findings) + 1
    )


def test_mock_sonar_and_docker() -> None:
    raw = MockSonarQubeAdapter().fetch_project_analysis("acme_app", "main")
    parsed = parse_sonar_results(raw["issues"], raw["quality_gate"], raw["measures"])
    assert parsed.quality_gate_status in {"passed", "failed"}
    assert all(f.component.startswith("acme_app:") for f in parsed.findings)
    with pytest.raises(AdapterError):
        MockSonarQubeAdapter().fetch_project_analysis("bad key", None)
    meta = MockDockerAdapter().inspect_image("nginx:1.27")
    assert meta.digest and meta.digest.startswith("sha256:")


def test_mock_github_runs_and_files() -> None:
    adapter = MockGitHubActionsAdapter()
    payload = adapter.list_workflow_runs("acme", "api", None, limit=10)
    runs = parse_workflow_runs(payload)
    assert len(runs) == 10
    assert len({r.external_id for r in runs}) == 10
    again = adapter.list_workflow_runs("acme", "api", None, limit=10)
    assert [r["id"] for r in payload["workflow_runs"]] == [r["id"] for r in again["workflow_runs"]]
    assert "==" in adapter.get_file("acme", "api", "requirements.txt", "main", None)
    with pytest.raises(AdapterError):
        adapter.get_file("acme", "api", "../../etc/passwd", "main", None)
    with pytest.raises(AdapterError):
        adapter.list_workflow_runs("acme;id", "api", None)
    assert adapter.check_repo_access("acme", "api", None).can_read


def test_validate_repo_path() -> None:
    assert validate_repo_path("services/api/requirements.txt")
    for bad in ("/etc/passwd", "a/../b", "a b.txt", ""):
        with pytest.raises(AdapterError):
            validate_repo_path(bad)


# ----------------------------------------------------------------------------- real HTTP adapters


def test_real_github_adapter_request_shape() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        if request.url.path.endswith("/actions/runs"):
            return httpx.Response(200, json=load_fixture("github_workflow_runs.json"))
        if "/contents/" in request.url.path:
            return httpx.Response(200, text="requests==2.31.0\n")
        return httpx.Response(
            200,
            json={
                "full_name": "acme/api",
                "private": True,
                "permissions": {"pull": True, "push": False},
            },
        )

    adapter = GitHubActionsAdapter(
        "https://api.github.test", transport=httpx.MockTransport(handler)
    )
    runs = parse_workflow_runs(adapter.list_workflow_runs("acme", "api", "tok_secret", "main", 5))
    assert len(runs) == 3
    assert seen[0].headers["Authorization"] == "Bearer tok_secret"
    assert seen[0].headers["X-GitHub-Api-Version"] == "2022-11-28"
    assert seen[0].url.params["branch"] == "main"
    assert seen[0].url.params["per_page"] == "5"
    access = adapter.check_repo_access("acme", "api", "tok_secret")
    assert access.private and access.can_read
    assert adapter.get_file("acme", "api", "requirements.txt", "main", None) == "requests==2.31.0\n"
    assert "Authorization" not in seen[-1].headers
    assert seen[-1].url.params["ref"] == "main"


@pytest.mark.parametrize(
    ("code", "match"), [(401, "denied"), (403, "denied"), (404, "not found"), (500, "HTTP 500")]
)
def test_real_github_adapter_errors(code: int, match: str) -> None:
    adapter = GitHubActionsAdapter(
        transport=httpx.MockTransport(lambda r: httpx.Response(code, json={"message": "x"}))
    )
    with pytest.raises(AdapterError, match=match) as exc:
        adapter.list_workflow_runs("acme", "api", "ghp_" + "s" * 36)
    assert "ghp_" not in str(exc.value)


def test_real_github_adapter_network_error() -> None:
    def boom(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("unreachable")

    adapter = GitHubActionsAdapter(transport=httpx.MockTransport(boom))
    with pytest.raises(AdapterError, match="ConnectError"):
        adapter.check_repo_access("acme", "api", None)


def test_real_sonarqube_adapter_paginates() -> None:
    issues = load_fixture("sonar_issues.json")["issues"]
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        path = request.url.path
        if path == "/api/issues/search":
            page = int(request.url.params["p"])
            chunk = issues[(page - 1) * 3 : page * 3]
            return httpx.Response(200, json={"total": len(issues), "issues": chunk})
        if path == "/api/qualitygates/project_status":
            return httpx.Response(200, json=load_fixture("sonar_quality_gate.json"))
        return httpx.Response(200, json=load_fixture("sonar_measures.json"))

    adapter = SonarQubeAdapter(
        "http://sonar.test", "squ_token", transport=httpx.MockTransport(handler)
    )
    adapter.page_size = 3
    raw = adapter.fetch_project_analysis("acme_payments-api", "main")
    assert len(raw["issues"]["issues"]) == 5
    assert seen[0].headers["Authorization"] == "Bearer squ_token"
    assert seen[0].url.params["componentKeys"] == "acme_payments-api"
    assert seen[0].url.params["branch"] == "main"
    parsed = parse_sonar_results(raw["issues"], raw["quality_gate"], raw["measures"])
    assert parsed.quality_gate_status == "failed"


def test_real_sonarqube_adapter_errors() -> None:
    with pytest.raises(AdapterError):
        SonarQubeAdapter("ftp://sonar", "t")
    adapter = SonarQubeAdapter(
        "http://sonar.test", "t", transport=httpx.MockTransport(lambda r: httpx.Response(401))
    )
    with pytest.raises(AdapterError, match="denied"):
        adapter.fetch_project_analysis("acme_app", None)
    with pytest.raises(AdapterError):
        adapter.fetch_project_analysis("bad key", None)


# ----------------------------------------------------------------------------- registry


def test_registry_defaults_to_mock_and_supports_real(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.config import get_settings

    assert registry.get_ci_provider().mode == "mock"
    assert registry.get_container_scanner().mode == "mock"
    statuses = {i["key"]: i["mode"] for i in registry.integration_status()}
    assert set(statuses.values()) == {"mock"}
    for key, value in {
        "GITHUB_MODE": "real",
        "SONARQUBE_MODE": "real",
        "TRIVY_MODE": "docker",
        "DOCKER_MODE": "real",
        "PIP_AUDIT_MODE": "real",
    }.items():
        monkeypatch.setenv(key, value)
    get_settings.cache_clear()
    try:
        assert isinstance(registry.get_ci_provider(), GitHubActionsAdapter)
        assert isinstance(registry.get_code_quality_provider(), SonarQubeAdapter)
        assert isinstance(registry.get_container_scanner(), TrivyDockerAdapter)
        assert isinstance(registry.get_image_inspector(), DockerCliAdapter)
        assert isinstance(registry.get_dependency_auditor(), PipAuditCliAdapter)
        monkeypatch.setenv("TRIVY_MODE", "binary")
        get_settings.cache_clear()
        assert isinstance(registry.get_container_scanner(), TrivyBinaryAdapter)
        # Integration status never exposes secrets.
        assert "token" not in json.dumps(registry.integration_status()).lower().replace(
            "configured", ""
        )
    finally:
        monkeypatch.undo()
        get_settings.cache_clear()
