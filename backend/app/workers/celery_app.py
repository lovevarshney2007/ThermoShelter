"""
Celery Application
==================

Configures the Celery app with Redis as both broker and result backend.
"""

from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "thermoshelter",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.workers.simulation_tasks",
        "app.workers.optimization_tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,                     # Re-queue on worker crash
    worker_prefetch_multiplier=1,            # One task at a time per worker
    task_soft_time_limit=600,                # 10 min soft limit
    task_time_limit=700,                     # 11.5 min hard limit
    result_expires=86400,                    # Keep results 24h
)
