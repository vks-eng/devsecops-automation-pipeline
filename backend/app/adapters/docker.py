"""Docker image inspection adapters (image metadata recorded alongside container scans)."""

from __future__ import annotations

import hashlib
import json

from app.adapters.base import AdapterError, ImageMetadata
from app.adapters.process import ephemeral_workspace, minimal_env, resolve_binary, run_fixed_argv
from app.core.validators import ValidationError, validate_image_ref


def _checked(image_ref: str) -> str:
    try:
        return validate_image_ref(image_ref)
    except ValidationError as exc:
        raise AdapterError(str(exc)) from exc


class DockerCliAdapter:
    """Reads metadata of a *locally available* image via ``docker image inspect``.

    It never pulls or runs the image - inspection is read-only, so untrusted artifacts are
    neither executed nor deployed.
    """

    mode = "real"

    def __init__(self, binary: str = "docker", timeout: int = 30) -> None:
        self.binary = binary
        self.timeout = timeout

    @staticmethod
    def build_argv(docker_path: str, image_ref: str) -> list[str]:
        return [docker_path, "image", "inspect", "--format", "{{json .}}", "--", image_ref]

    def inspect_image(self, image_ref: str) -> ImageMetadata:
        image_ref = _checked(image_ref)
        docker_path = resolve_binary(self.binary)
        with ephemeral_workspace() as work:
            result = run_fixed_argv(
                self.build_argv(docker_path, image_ref),
                cwd=work,
                timeout=self.timeout,
                env=minimal_env(work),
                allowed_returncodes=(0, 1),
            )
        if result.returncode != 0:
            return ImageMetadata(image_ref, None, None, None, None, None, available_locally=False)
        try:
            data = json.loads(result.stdout.strip().splitlines()[0])
        except (json.JSONDecodeError, IndexError) as exc:
            raise AdapterError("Unexpected output from docker image inspect") from exc
        digests = data.get("RepoDigests") or []
        return ImageMetadata(
            image_ref=image_ref,
            digest=digests[0].split("@", 1)[1] if digests and "@" in digests[0] else None,
            size_bytes=data.get("Size"),
            created=data.get("Created"),
            os=data.get("Os"),
            architecture=data.get("Architecture"),
            available_locally=True,
        )


class MockDockerAdapter:
    mode = "mock"

    def inspect_image(self, image_ref: str) -> ImageMetadata:
        image_ref = _checked(image_ref)
        h = hashlib.sha256(("digest:" + image_ref).encode()).hexdigest()
        return ImageMetadata(
            image_ref=image_ref,
            digest=f"sha256:{h}",
            size_bytes=50_000_000 + int(h[:6], 16) % 400_000_000,
            created="2026-10-01T12:00:00Z",
            os="linux",
            architecture="amd64",
            available_locally=True,
        )
