"""Encrypted integration credentials. Plaintext tokens only exist transiently in memory."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import decrypt_secret, encrypt_secret, secret_hint
from app.models import IntegrationCredential

ALLOWED_PROVIDERS = {"github"}


def set_token(
    db: Session, project_id: int, provider: str, token: str, user_id: int | None
) -> IntegrationCredential:
    if provider not in ALLOWED_PROVIDERS:
        raise ValueError("Unsupported provider")
    cred = db.scalar(
        select(IntegrationCredential).where(
            IntegrationCredential.project_id == project_id,
            IntegrationCredential.provider == provider,
        )
    )
    if cred is None:
        cred = IntegrationCredential(project_id=project_id, provider=provider)
        db.add(cred)
    cred.encrypted_token = encrypt_secret(token)
    cred.token_hint = secret_hint(token)
    cred.created_by_id = user_id
    return cred


def get_credential(db: Session, project_id: int, provider: str) -> IntegrationCredential | None:
    return db.scalar(
        select(IntegrationCredential).where(
            IntegrationCredential.project_id == project_id,
            IntegrationCredential.provider == provider,
        )
    )


def get_token(db: Session, project_id: int, provider: str) -> str | None:
    cred = get_credential(db, project_id, provider)
    return decrypt_secret(cred.encrypted_token) if cred else None


def delete_token(db: Session, project_id: int, provider: str) -> bool:
    cred = get_credential(db, project_id, provider)
    if cred is None:
        return False
    db.delete(cred)
    return True
