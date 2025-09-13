from __future__ import annotations

from celery import Celery
from src.core.config import get_settings


settings = get_settings()
app = Celery(
    "transcriber",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["src.tasks.tasks"],
)

