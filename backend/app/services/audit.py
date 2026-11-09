"""Audit logging for security-sensitive actions."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import Request
from sqlalchemy.orm import Session

from app.models import AuditLog, User

logger = logging.getLogger("audit")

_SENSITIVE_KEYS = {"password", "token", "secret", "authorization", "api_key"}


def _scrub(details: dict[str, Any]) -> dict[str, Any]:
    return {
        k: ("[REDACTED]" if any(s in k.lower() for s in _SENSITIVE_KEYS) else v)
        for k, v in details.items()
    }


def client_ip(request: Request | None) -> str:
    if request is None or request.client is None:
        return ""
    return request.client.host[:64]


def record(
    db: Session,
    action: str,
    *,
    actor: User | None = None,
    actor_email: str = "",
    resource_type: str = "",
    resource_id: str | int = "",
    outcome: str = "success",
    request: Request | None = None,
    details: dict[str, Any] | None = None,
    commit: bool = True,
) -> AuditLog:
    entry = AuditLog(
        actor_id=actor.id if actor else None,
        actor_email=(actor.email if actor else actor_email)[:320],
        action=action,
        resource_type=resource_type,
        resource_id=str(resource_id),
        outcome=outcome,
        ip_address=client_ip(request),
        details=_scrub(details or {}),
    )
    db.add(entry)
    if commit:
        db.commit()
    logger.info(
        "audit action=%s outcome=%s resource=%s:%s actor=%s",
        action,
        outcome,
        resource_type,
        resource_id,
        entry.actor_email or "-",
    )
    return entry
