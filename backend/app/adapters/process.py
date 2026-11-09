"""Hardened subprocess execution for scanner binaries.

Rules enforced here (see README "Security considerations"):

* argv is always a fixed ``list[str]`` assembled by the platform - never a shell string;
  ``shell=False`` is always used, so shell metacharacters have no meaning.
* every invocation runs inside a fresh, private temporary directory that is deleted
  afterwards (ephemeral workspace, no shared state between scans);
* a minimal environment is passed (no inherited secrets such as tokens or DB URLs);
* a hard timeout is applied.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess  # nosec B404 - used with fixed argv lists and shell=False only
import tempfile
from collections.abc import Callable, Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from app.adapters.base import AdapterError

logger = logging.getLogger(__name__)

_SAFE_ENV_KEYS = ("PATH", "SYSTEMROOT", "TEMP", "TMP", "HOME", "USERPROFILE", "LANG")


@dataclass(slots=True)
class ProcessResult:
    returncode: int
    stdout: str
    stderr: str


@contextmanager
def ephemeral_workspace(prefix: str = "dsp-scan-") -> Iterator[Path]:
    path = Path(tempfile.mkdtemp(prefix=prefix))
    try:
        os.chmod(path, 0o700)
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


def minimal_env(workdir: Path, extra: dict[str, str] | None = None) -> dict[str, str]:
    env = {k: os.environ[k] for k in _SAFE_ENV_KEYS if k in os.environ}
    env["HOME"] = str(workdir)
    env["TMPDIR"] = str(workdir)
    if extra:
        env.update(extra)
    return env


def resolve_binary(name: str) -> str:
    resolved = shutil.which(name)
    if not resolved:
        raise AdapterError(f"Required binary '{name}' was not found on PATH")
    return resolved


Runner = Callable[..., ProcessResult]


def run_fixed_argv(
    argv: Sequence[str],
    *,
    cwd: Path,
    timeout: int,
    env: dict[str, str],
    allowed_returncodes: tuple[int, ...] = (0,),
) -> ProcessResult:
    if isinstance(argv, str) or not all(isinstance(a, str) for a in argv):
        raise AdapterError("argv must be a list of strings")
    logger.info("Executing scanner: %s", Path(argv[0]).name)
    try:
        completed = subprocess.run(  # nosec B603 - fixed argv, shell=False, validated args  # noqa: S603
            list(argv),
            cwd=str(cwd),
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
            shell=False,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise AdapterError(f"{Path(argv[0]).name} timed out after {timeout}s") from exc
    except OSError as exc:
        raise AdapterError(f"Failed to execute {Path(argv[0]).name}: {exc.strerror}") from exc
    if completed.returncode not in allowed_returncodes:
        tail = (completed.stderr or "").strip().splitlines()[-5:]
        raise AdapterError(
            f"{Path(argv[0]).name} exited with code {completed.returncode}: " + " | ".join(tail)
        )
    return ProcessResult(completed.returncode, completed.stdout, completed.stderr)
