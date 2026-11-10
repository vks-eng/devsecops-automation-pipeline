"""Trivy container image scanner adapters.

* ``TrivyBinaryAdapter`` - runs a local ``trivy`` binary (used inside the worker
  container, which ships the official Trivy binary).
* ``TrivyDockerAdapter`` - runs Trivy in a throw-away ``aquasec/trivy`` container
  (``--rm``, all capabilities dropped, no-new-privileges, read-only root FS).
* ``MockTrivyAdapter`` - deterministic, realistic report generated from a catalogue.
"""

from __future__ import annotations

import hashlib
import json
import random
from pathlib import Path
from typing import Any

from app.adapters.base import AdapterError
from app.adapters.mock_data import load_mock_json
from app.adapters.process import ephemeral_workspace, minimal_env, resolve_binary, run_fixed_argv
from app.core.validators import ValidationError, validate_image_ref

# Trivy exits 0 (no findings above threshold); we never pass --exit-code so non-zero = error.
_TRIVY_FLAGS = ["--format", "json", "--quiet", "--scanners", "vuln"]


def _read_report(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AdapterError("Trivy did not produce a valid JSON report") from exc


def _checked(image_ref: str) -> str:
    try:
        return validate_image_ref(image_ref)
    except ValidationError as exc:
        raise AdapterError(str(exc)) from exc


class TrivyBinaryAdapter:
    mode = "binary"

    def __init__(self, binary: str = "trivy", timeout: int = 600) -> None:
        self.binary = binary
        self.timeout = timeout

    def build_argv(self, binary_path: str, image_ref: str, output: Path, cache: Path) -> list[str]:
        return [
            binary_path,
            "image",
            *_TRIVY_FLAGS,
            "--timeout",
            f"{self.timeout}s",
            "--cache-dir",
            str(cache),
            "--output",
            str(output),
            "--",
            _checked(image_ref),
        ]

    def scan_image(self, image_ref: str) -> dict[str, Any]:
        image_ref = _checked(image_ref)
        binary_path = resolve_binary(self.binary)
        with ephemeral_workspace() as work:
            output = work / "report.json"
            argv = self.build_argv(binary_path, image_ref, output, work / "cache")
            run_fixed_argv(argv, cwd=work, timeout=self.timeout + 30, env=minimal_env(work))
            return _read_report(output)


class TrivyDockerAdapter:
    mode = "docker"

    def __init__(
        self,
        docker_binary: str = "docker",
        trivy_image: str = "aquasec/trivy:0.58.1",
        timeout: int = 600,
    ) -> None:
        self.docker_binary = docker_binary
        self.trivy_image = _checked(trivy_image)
        self.timeout = timeout

    def build_argv(self, docker_path: str, image_ref: str, workdir: Path) -> list[str]:
        return [
            docker_path,
            "run",
            "--rm",
            "--read-only",
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges",
            "--tmpfs",
            "/tmp:rw,size=512m",  # noqa: S108  # nosec B108 - tmpfs inside throw-away container
            "-v",
            f"{workdir}:/out",
            "-v",
            "dsp-trivy-cache:/root/.cache/trivy",
            self.trivy_image,
            "image",
            *_TRIVY_FLAGS,
            "--timeout",
            f"{self.timeout}s",
            "--output",
            "/out/report.json",
            "--",
            _checked(image_ref),
        ]

    def scan_image(self, image_ref: str) -> dict[str, Any]:
        image_ref = _checked(image_ref)
        docker_path = resolve_binary(self.docker_binary)
        with ephemeral_workspace() as work:
            argv = self.build_argv(docker_path, image_ref, work)
            run_fixed_argv(argv, cwd=work, timeout=self.timeout + 60, env=minimal_env(work))
            return _read_report(work / "report.json")


class MockTrivyAdapter:
    """Builds a schema-v2 Trivy report from a catalogue, deterministically per image ref."""

    mode = "mock"

    def scan_image(self, image_ref: str) -> dict[str, Any]:
        image_ref = _checked(image_ref)
        catalogue = load_mock_json("trivy_catalogue.json")
        seed = int(hashlib.sha256(image_ref.encode()).hexdigest()[:12], 16)
        rng = random.Random(seed)  # nosec B311 - deterministic mock data, not crypto  # noqa: S311
        hardened = any(k in image_ref for k in ("distroless", "chainguard", "scratch"))
        keep_ratio = 0.15 if hardened else (0.45 if "alpine" in image_ref else 0.75)

        results: list[dict[str, Any]] = []
        for target in catalogue["targets"]:
            vulns = [dict(v) for v in target["vulnerabilities"] if rng.random() < keep_ratio]
            if hardened and target["class"] == "os-pkgs":
                vulns = vulns[:1]
            results.append(
                {
                    "Target": target["target"].format(image=image_ref),
                    "Class": target["class"],
                    "Type": target["type"],
                    "Vulnerabilities": vulns,
                }
            )
        digest = hashlib.sha256(("digest:" + image_ref).encode()).hexdigest()
        repo = (
            image_ref.split("@")[0].rsplit(":", 1)[0]
            if ":" in image_ref.split("/")[-1]
            else (image_ref.split("@")[0])
        )
        return {
            "SchemaVersion": 2,
            "ArtifactName": image_ref,
            "ArtifactType": "container_image",
            "Metadata": {
                "OS": {"Family": "debian", "Name": "12.5"},
                "ImageID": f"sha256:{hashlib.sha256(image_ref.encode()).hexdigest()}",
                "RepoDigests": [f"{repo}@sha256:{digest}"],
            },
            "Results": results,
        }
