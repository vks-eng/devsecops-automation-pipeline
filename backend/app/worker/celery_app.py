"""Celery application.

With ``CELERY_TASK_ALWAYS_EAGER=true`` (default for local dev and tests) tasks run
in-process and no Redis broker is required. docker-compose sets it to ``false`` and runs
a dedicated worker container backed by Redis.
"""

from __future__ import annotations

from celery import Celery

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "devsecops",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.worker.tasks"],
)
celery_app.conf.update(
    task_always_eager=settings.celery_task_always_eager,
    task_eager_propagates=False,
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_time_limit=settings.trivy_timeout_seconds + 300,
    broker_connection_retry_on_startup=True,
    beat_schedule={
        "sync-pipelines-every-15-minutes": {
            "task": "app.worker.tasks.sync_all_pipelines",
            "schedule": 900.0,
        }
    },
)
