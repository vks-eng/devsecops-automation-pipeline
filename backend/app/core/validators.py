"""Strict input validators.

These validators are the first line of defence before any value reaches an external
API call or a scanner argv list. They are deliberately stricter than the underlying
tools: anything that is not explicitly allowed is rejected.
"""

from __future__ import annotations

import re

# https://github.com/<owner>/<repo>
#   owner: 1-39 chars, alphanumeric or single hyphens, cannot start/end with hyphen
#   repo:  1-100 chars of [A-Za-z0-9._-], not "." / ".." and no ".git" suffix
_GITHUB_REPO_RE = re.compile(
    r"^https://github\.com/"
    r"(?P<owner>[A-Za-z0-9](?:[A-Za-z0-9]|-(?=[A-Za-z0-9])){0,38})/"
    r"(?P<repo>[A-Za-z0-9._-]{1,100})$"
)

_BRANCH_ALLOWED_RE = re.compile(r"^[A-Za-z0-9._/-]{1,200}$")

_DOMAIN_COMPONENT = r"(?:[a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9-]*[a-zA-Z0-9])"
# A registry host must look like a host: contain a dot or a port, or be "localhost"
# (otherwise the first component is part of the repository path, as in Docker).
_PORT = r"(?::[0-9]{1,5})"
_DOMAIN = (
    rf"(?:localhost{_PORT}?"
    rf"|{_DOMAIN_COMPONENT}(?:\.{_DOMAIN_COMPONENT})+{_PORT}?"
    rf"|{_DOMAIN_COMPONENT}{_PORT})"
)
_PATH_COMPONENT = r"(?:[a-z0-9]+(?:(?:[._]|__|-+)[a-z0-9]+)*)"
_IMAGE_REF_RE = re.compile(
    rf"^(?:{_DOMAIN}/)?"
    rf"{_PATH_COMPONENT}(?:/{_PATH_COMPONENT})*"
    r"(?::[A-Za-z0-9_][A-Za-z0-9_.-]{0,127})?"
    r"(?:@sha256:[a-f0-9]{64})?$"
)

_SONAR_KEY_RE = re.compile(r"^(?=.*[A-Za-z_.:-])[A-Za-z0-9_.:-]{1,400}$")
_SLUG_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,62}[a-z0-9])?$")


class ValidationError(ValueError):
    """Raised when an input fails strict validation."""


def parse_github_repo_url(url: str) -> tuple[str, str]:
    """Validate a GitHub repository URL and return ``(owner, repo)``."""
    if not isinstance(url, str):
        raise ValidationError("Repository URL must be a string")
    match = _GITHUB_REPO_RE.fullmatch(url)
    if not match:
        raise ValidationError("Repository URL must match https://github.com/<owner>/<repo>")
    owner, repo = match.group("owner"), match.group("repo")
    if repo in {".", ".."} or repo.lower().endswith(".git"):
        raise ValidationError("Repository name is invalid (omit any .git suffix)")
    return owner, repo


def validate_branch_name(name: str) -> str:
    """Validate a git branch name (subset of ``git check-ref-format`` rules)."""
    if not isinstance(name, str) or not _BRANCH_ALLOWED_RE.fullmatch(name):
        raise ValidationError("Branch name contains invalid characters")
    if name.startswith(("-", "/", ".")) or name.endswith(("/", ".", ".lock")):
        raise ValidationError("Branch name has an invalid prefix or suffix")
    if ".." in name or "//" in name or "@{" in name or name == "@":
        raise ValidationError("Branch name contains an invalid sequence")
    if any(part.startswith(".") or part.endswith(".lock") for part in name.split("/")):
        raise ValidationError("Branch name has an invalid path component")
    return name


def validate_image_ref(ref: str) -> str:
    """Validate a container image reference (e.g. ``ghcr.io/org/app:1.2.3``)."""
    if not isinstance(ref, str) or not 1 <= len(ref) <= 255:
        raise ValidationError("Image reference length is invalid")
    if not _IMAGE_REF_RE.fullmatch(ref):
        raise ValidationError("Image reference is not a valid OCI reference")
    return ref


def validate_sonar_project_key(key: str) -> str:
    if not isinstance(key, str) or not _SONAR_KEY_RE.fullmatch(key):
        raise ValidationError("SonarQube project key is invalid")
    return key


def validate_slug(slug: str) -> str:
    if not isinstance(slug, str) or not _SLUG_RE.fullmatch(slug):
        raise ValidationError("Slug must be lowercase alphanumeric with hyphens (max 64)")
    return slug


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug[:64].strip("-") or "project"
