"""Celery application configuration and Beat schedule for background task execution.

Enforces zero AI dependencies, strict serialization, and process isolation.
"""

from __future__ import annotations

import logging
from celery import Celery

from backend.config import settings

logger = logging.getLogger(__name__)

celery_app = Celery("automation_worker")

celery_app.conf.update(
    broker_url=settings.celery_broker_url,
    result_backend=settings.celery_result_backend,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone=settings.default_timezone,
    enable_utc=True,
    task_track_started=True,
    task_time_limit=600,  # 10 minute hard limit for safety
    task_soft_time_limit=540,  # 9 minute soft warning limit
    worker_concurrency=settings.celery_worker_concurrency,
    task_always_eager=settings.celery_task_always_eager,
    task_eager_propagates=True,
    broker_connection_retry_on_startup=True,
)

# Periodic Celery Beat schedules
celery_app.conf.beat_schedule = {
    "evaluate-scheduled-automations-every-minute": {
        "task": "worker.schedule_checker",
        "schedule": 60.0,  # Run every 60 seconds
    },
    "daily-artifact-retention-cleanup": {
        "task": "worker.cleanup_retention",
        "schedule": 86400.0,  # Run once every 24 hours
        "args": (30,),  # 30 days retention policy
    },
}

celery_app.autodiscover_tasks(["backend.app.worker"])

