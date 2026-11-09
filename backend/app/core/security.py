"""Password hashing, JWT handling, secret encryption and webhook signature verification."""

from __future__ import annotations

import base64
import hashlib
import hmac
from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
import jwt
from cryptography.fernet import Fernet, InvalidToken

from app.core.config import get_settings

# bcrypt only considers the first 72 bytes; we pre-hash to support long passphrases safely.


def _prehash(password: str) -> bytes:
    return base64.b64encode(hashlib.sha256(password.encode("utf-8")).digest())


def hash_password(password: str) -> str:
    return bcrypt.hashpw(_prehash(password), bcrypt.gensalt(rounds=12)).decode("ascii")


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(_prehash(password), hashed.encode("ascii"))
    except ValueError:
        return False


def create_access_token(subject: str, extra: dict[str, Any] | None = None) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": subject,
        "iat": now,
        "nbf": now,
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
        "type": "access",
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    payload = jwt.decode(
        token,
        settings.secret_key,
        algorithms=[settings.jwt_algorithm],
        options={"require": ["exp", "sub", "iat"]},
    )
    if payload.get("type") != "access":
        raise jwt.InvalidTokenError("wrong token type")
    return payload


# --------------------------------------------------------------------------------------
# Secret encryption (integration tokens are encrypted at rest and never returned by API)
# --------------------------------------------------------------------------------------


def _fernet() -> Fernet:
    settings = get_settings()
    key = settings.token_encryption_key
    if not key:
        # Dev fallback: derive a stable key from SECRET_KEY. Production should set
        # TOKEN_ENCRYPTION_KEY explicitly (see .env.example).
        key = base64.urlsafe_b64encode(
            hashlib.sha256(("token-enc:" + settings.secret_key).encode()).digest()
        ).decode()
    return Fernet(key.encode() if isinstance(key, str) else key)


def encrypt_secret(plaintext: str) -> str:
    return _fernet().encrypt(plaintext.encode("utf-8")).decode("ascii")


def decrypt_secret(ciphertext: str) -> str:
    try:
        return _fernet().decrypt(ciphertext.encode("ascii")).decode("utf-8")
    except InvalidToken as exc:  # pragma: no cover - key rotation / corruption
        raise ValueError("Unable to decrypt stored secret") from exc


def secret_hint(plaintext: str) -> str:
    """Return a non-sensitive hint (last 4 chars) for display purposes."""
    return f"****{plaintext[-4:]}" if len(plaintext) >= 8 else "****"


# --------------------------------------------------------------------------------------
# GitHub webhook signature verification (HMAC-SHA256, constant-time comparison)
# --------------------------------------------------------------------------------------


def compute_github_signature(secret: str, body: bytes) -> str:
    digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def verify_github_signature(secret: str, body: bytes, signature_header: str | None) -> bool:
    if not secret or not signature_header:
        return False
    if not signature_header.startswith("sha256="):
        return False
    expected = compute_github_signature(secret, body)
    return hmac.compare_digest(expected.encode("ascii"), signature_header.encode("ascii", "ignore"))
