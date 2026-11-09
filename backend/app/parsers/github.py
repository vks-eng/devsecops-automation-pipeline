"""Parsers for GitHub Actions API payloads and ``workflow_run`` webhook events."""

from __future__ import annotations

from typing import Any

from app.parsers.common import ParsedPipelineRun, ParseError, parse_iso8601, truncate


def parse_workflow_run(run: dict[str, Any]) -> ParsedPipelineRun:
    if not isinstance(run, dict) or "id" not in run:
        raise ParseError("workflow run must be an object with an id")
    status = str(run.get("status") or "queued")
    started = parse_iso8601(run.get("run_started_at") or run.get("created_at"))
    completed = parse_iso8601(run.get("updated_at")) if status == "completed" else None
    actor = run.get("actor") or run.get("triggering_actor") or {}
    return ParsedPipelineRun(
        external_id=truncate(run["id"], 64),
        workflow_name=truncate(run.get("name") or "workflow", 200),
        branch=truncate(run.get("head_branch") or "", 200),
        commit_sha=truncate(run.get("head_sha") or "", 64),
        event=truncate(run.get("event") or "", 50),
        status=truncate(status, 32),
        conclusion=truncate(run["conclusion"], 32) if run.get("conclusion") else None,
        actor=truncate(actor.get("login", "") if isinstance(actor, dict) else "", 100),
        html_url=truncate(run.get("html_url") or "", 500),
        started_at=started,
        completed_at=completed,
    )


def parse_workflow_runs(payload: dict[str, Any]) -> list[ParsedPipelineRun]:
    runs = payload.get("workflow_runs") if isinstance(payload, dict) else None
    if not isinstance(runs, list):
        raise ParseError("payload must contain a 'workflow_runs' list")
    return [parse_workflow_run(r) for r in runs]
