from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select, text

from app.adapters.registry import integration_status
from app.api.deps import AdminUser, CurrentUser, DbSession
from app.core.config import get_settings
from app.models import AuditLog
from app.schemas import AuditLogOut

router = APIRouter(tags=["system"])


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/ready")
def ready(db: DbSession) -> dict[str, str]:
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "database unavailable") from None
    return {"status": "ready", "database": "ok"}


@router.get("/settings/integrations")
def integrations(_: CurrentUser) -> dict[str, Any]:
    s = get_settings()
    return {
        "integrations": integration_status(),
        "background_processing": "eager (in-process)"
        if s.celery_task_always_eager
        else "celery worker (redis)",
        "notification_channels": {
            "in_app": True,
            "webhook": bool(s.notification_webhook_url),
            "email": bool(s.smtp_host),
        },
        "registration_open": s.allow_registration,
    }


@router.get("/audit-logs", response_model=list[AuditLogOut])
def audit_logs(
    db: DbSession,
    _: AdminUser,
    action: str | None = Query(None, max_length=100),
    limit: int = Query(100, ge=1, le=500),
) -> list[AuditLog]:
    stmt = select(AuditLog)
    if action:
        stmt = stmt.where(AuditLog.action == action)
    return list(
        db.scalars(stmt.order_by(AuditLog.created_at.desc(), AuditLog.id.desc()).limit(limit))
    )
