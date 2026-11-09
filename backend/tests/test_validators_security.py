from __future__ import annotations

import logging

import jwt
import pytest

from app.core import security
from app.core.logging import RedactingFilter, redact
from app.core.validators import (
    ValidationError,
    parse_github_repo_url,
    slugify,
    validate_branch_name,
    validate_image_ref,
    validate_slug,
    validate_sonar_project_key,
)

# ----------------------------------------------------------------------------- validators


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://github.com/acme/api", ("acme", "api")),
        ("https://github.com/a-b-c/repo.name_x-1", ("a-b-c", "repo.name_x-1")),
        ("https://github.com/A1/B", ("A1", "B")),
    ],
)
def test_valid_github_urls(url: str, expected: tuple[str, str]) -> None:
    assert parse_github_repo_url(url) == expected


@pytest.mark.parametrize(
    "url",
    [
        "http://github.com/acme/api",
        "https://github.com/acme/api/",
        "https://github.com/acme/api.git",
        "https://github.com/acme",
        "https://github.com/acme/api/tree/main",
        "https://gitlab.com/acme/api",
        "https://github.com.evil.com/acme/api",
        "https://github.com/-acme/api",
        "https://github.com/acme-/api",
        "https://github.com/ac--me/api",
        "https://github.com/acme/..",
        "https://github.com/acme/api;rm -rf /",
        "https://github.com/acme/api?x=1",
        "https://user@github.com/acme/api",
        " https://github.com/acme/api",
        "https://github.com/acme/api\n",
        "https://github.com/" + "a" * 40 + "/api",
    ],
)
def test_invalid_github_urls(url: str) -> None:
    with pytest.raises(ValidationError):
        parse_github_repo_url(url)


@pytest.mark.parametrize(
    "name", ["main", "develop", "release/2.x", "feature/ABC-123_fix", "v1.2.3"]
)
def test_valid_branches(name: str) -> None:
    assert validate_branch_name(name) == name


@pytest.mark.parametrize(
    "name",
    [
        "",
        "-rf",
        "/main",
        "main/",
        "a..b",
        "a//b",
        "x.lock",
        "foo/.hidden",
        "@",
        "a@{b",
        "has space",
        "semi;colon",
        "$(whoami)",
        "back`tick`",
        "a\\b",
        "x" * 201,
        ".dot",
        "end.",
    ],
)
def test_invalid_branches(name: str) -> None:
    with pytest.raises(ValidationError):
        validate_branch_name(name)


@pytest.mark.parametrize(
    "ref",
    [
        "python:3.11-slim",
        "nginx",
        "library/nginx:1.27",
        "ghcr.io/acme-demo/payments-api:1.8.2",
        "localhost:5000/team/app:latest",
        "gcr.io/distroless/python3-debian12:nonroot",
        "registry.example.com/a/b/c@sha256:" + "a" * 64,
        "app:1.0@sha256:" + "0" * 64,
    ],
)
def test_valid_image_refs(ref: str) -> None:
    assert validate_image_ref(ref) == ref


@pytest.mark.parametrize(
    "ref",
    [
        "",
        "--privileged",
        "-v",
        "UPPER/case",
        "nginx;rm -rf /",
        "nginx && id",
        "nginx|id",
        "nginx:$(id)",
        "nginx:`id`",
        "nginx latest",
        "nginx:",
        "nginx@sha256:short",
        "a" * 256,
        "ghcr.io/acme/app:tag\n",
        "../etc/passwd",
    ],
)
def test_invalid_image_refs(ref: str) -> None:
    with pytest.raises(ValidationError):
        validate_image_ref(ref)


def test_sonar_key_slug_and_slugify() -> None:
    assert validate_sonar_project_key("acme_payments-api") == "acme_payments-api"
    assert validate_sonar_project_key("org:proj.1") == "org:proj.1"
    for bad in ("12345", "has space", "a/b", ""):
        with pytest.raises(ValidationError):
            validate_sonar_project_key(bad)
    assert validate_slug("payments-api") == "payments-api"
    for bad in ("-x", "Upper", "a_b", "x-"):
        with pytest.raises(ValidationError):
            validate_slug(bad)
    assert slugify("Payments API (EU)!") == "payments-api-eu"
    assert slugify("!!!") == "project"


# ----------------------------------------------------------------------------- security


def test_password_hashing_roundtrip_and_long_passwords() -> None:
    hashed = security.hash_password("Correct-Horse-1")
    assert hashed != "Correct-Horse-1"
    assert security.verify_password("Correct-Horse-1", hashed)
    assert not security.verify_password("wrong", hashed)
    long_pw = "x1" * 100  # > 72 bytes: pre-hash keeps the full value significant
    long_hash = security.hash_password(long_pw)
    assert security.verify_password(long_pw, long_hash)
    assert not security.verify_password(long_pw[:-1] + "y", long_hash)
    assert not security.verify_password("x", "not-a-bcrypt-hash")


def test_jwt_roundtrip_and_tampering() -> None:
    token = security.create_access_token("42", {"role": "admin"})
    payload = security.decode_access_token(token)
    assert payload["sub"] == "42"
    assert payload["role"] == "admin"
    with pytest.raises(jwt.PyJWTError):
        security.decode_access_token(token[:-2] + ("A" if token[-1] != "A" else "B") + "x")
    forged = jwt.encode(
        {"sub": "1", "type": "access", "iat": 1, "exp": 9999999999},
        "another-secret-that-is-long-enough",
        algorithm="HS256",
    )
    with pytest.raises(jwt.PyJWTError):
        security.decode_access_token(forged)
    none_alg = jwt.encode({"sub": "1", "type": "access"}, key="", algorithm="none")
    with pytest.raises(jwt.PyJWTError):
        security.decode_access_token(none_alg)


def test_secret_encryption() -> None:
    token = "github_pat_" + "11" + "B" * 40 + "wxyz"  # built at runtime
    encrypted = security.encrypt_secret(token)
    assert token not in encrypted
    assert security.decrypt_secret(encrypted) == token
    assert security.secret_hint(token) == "****wxyz"
    assert security.secret_hint("short") == "****"


def test_github_signature_verification() -> None:
    body = b'{"action":"completed"}'
    sig = security.compute_github_signature("s3cret", body)
    assert sig.startswith("sha256=") and len(sig) == 71
    assert security.verify_github_signature("s3cret", body, sig)
    assert not security.verify_github_signature("s3cret", body + b" ", sig)
    assert not security.verify_github_signature("other", body, sig)
    assert not security.verify_github_signature("s3cret", body, None)
    assert not security.verify_github_signature("", body, sig)
    assert not security.verify_github_signature("s3cret", body, sig.replace("sha256=", "sha1="))
    assert not security.verify_github_signature("s3cret", body, "sha256=éé")


def test_log_redaction(caplog: pytest.LogCaptureFixture) -> None:
    text = (
        "token ghp_" + "a" * 36 + " and Authorization: Bearer abc.def.ghi and "
        "github_pat_" + "B" * 30
    )
    redacted = redact(text)
    assert "ghp_" not in redacted
    assert "abc.def.ghi" not in redacted
    assert "github_pat_" not in redacted
    record = logging.LogRecord(
        "t", logging.INFO, __file__, 1, "using %s", ("ghp_" + "z" * 36,), None
    )
    RedactingFilter().filter(record)
    assert "ghp_" not in record.getMessage()
