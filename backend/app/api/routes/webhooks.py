"""GitHub webhook receiver. Every request must carry a valid X-Hub-Signature-256."""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Request, status

from app.api.deps import DbSession
from app.core.config import get_settings
from app.core.security import verify_github_signature
from app.parsers.common import ParseError
from app.services import audit
from app.services.pipelines import handle_workflow_run_event

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

MAX_BODY_BYTES = 1_000_000


@router.post("/github", status_code=202)
async def github_webhook(
    request: Request,
    db: DbSession,
    x_github_event: str = Header(default="", max_length=64),
    x_hub_signature_256: str | None = Header(default=None, max_length=100),
    x_github_delivery: str = Header(default="", max_length=64),
) -> dict[str, Any]:
    secret = get_settings().github_webhook_secret
    if not secret:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "Webhook receiver is not configured"
        )
    body = await request.body()
    if len(body) > MAX_BODY_BYTES:
        raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, "Payload too large")
    if not verify_github_signature(secret, body, x_hub_signature_256):
        audit.record(
            db,
            "webhook.github",
            outcome="rejected",
            resource_type="webhook",
            resource_id=x_github_delivery,
            request=request,
            details={"event": x_github_event, "reason": "invalid signature"},
        )
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid signature")
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid JSON") from None
    if not isinstance(payload, dict):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid payload")

    if x_github_event == "ping":
        return {"status": "pong"}
    if x_github_event != "workflow_run":
        return {"status": "ignored", "event": x_github_event}
    try:
        run = handle_workflow_run_event(db, payload)
    except ParseError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from None
    audit.record(
        db,
        "webhook.github",
        resource_type="pipeline_run",
        resource_id=run.id if run else "",
        request=request,
        details={
            "event": x_github_event,
            "delivery": x_github_delivery,
            "tracked": run is not None,
        },
    )
    return {"status": "processed" if run else "ignored_unregistered_repository"}
