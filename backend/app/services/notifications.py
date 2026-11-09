"""In-app notifications plus optional outbound channels (generic webhook, SMTP e-mail).

Outbound channels are disabled unless configured and are strictly best-effort: a failure
to deliver never breaks scan processing.
"""

from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import Notification, NotificationType, Project, User
from app.services.access import project_recipients

logger = logging.getLogger(__name__)


def notify_project(
    db: Session,
    project: Project,
    ntype: NotificationType,
    title: str,
    message: str,
    severity: str = "info",
    link: str = "",
) -> list[Notification]:
    created: list[Notification] = []
    for user_id in project_recipients(db, project):
        n = Notification(
            user_id=user_id,
            project_id=project.id,
            type=ntype.value,
            severity=severity,
            title=title[:300],
            message=message,
            link=link[:300],
        )
        db.add(n)
        created.append(n)
    db.flush()
    _dispatch_external(db, project, ntype, title, message, severity)
    return created


def _dispatch_external(
    db: Session,
    project: Project,
    ntype: NotificationType,
    title: str,
    message: str,
    severity: str,
) -> None:
    settings = get_settings()
    # Only alert-worthy events leave the platform.
    if ntype == NotificationType.SCAN_COMPLETED:
        return
    payload = {
        "event": ntype.value,
        "severity": severity,
        "project": project.slug,
        "title": title,
        "message": message,
    }
    if settings.notification_webhook_url.startswith("https://") or (
        settings.environment != "production"
        and settings.notification_webhook_url.startswith("http://")
    ):
        try:
            httpx.post(
                settings.notification_webhook_url,
                json=payload,
                timeout=settings.http_timeout_seconds,
            )
        except httpx.HTTPError as exc:
            logger.warning("Notification webhook delivery failed: %s", type(exc).__name__)
    if settings.smtp_host:
        recipients = list(
            db.scalars(select(User.email).where(User.id.in_(project_recipients(db, project))))
        )
        _send_email(recipients, f"[DevSecOps] {title}", message)


def _send_email(recipients: list[str], subject: str, body: str) -> None:
    settings = get_settings()
    if not recipients:
        return
    msg = EmailMessage()
    msg["From"] = settings.smtp_from
    msg["To"] = ", ".join(recipients)
    msg["Subject"] = subject[:200]
    msg.set_content(body)
    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
            if settings.smtp_use_tls:
                smtp.starttls()
            if settings.smtp_username:
                smtp.login(settings.smtp_username, settings.smtp_password)
            smtp.send_message(msg)
    except (OSError, smtplib.SMTPException) as exc:
        logger.warning("E-mail notification failed: %s", type(exc).__name__)
