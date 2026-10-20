import os
from pathlib import Path

from celery import Celery
from dotenv import load_dotenv


ENV_PATH = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(ENV_PATH, override=False)

celery_app = Celery(
    "rag0",
    broker=os.getenv(
        "CELERY_BROKER_URL",
        "redis://127.0.0.1:6379/1",
    ),
    backend=os.getenv(
        "CELERY_RESULT_BACKEND",
        "redis://127.0.0.1:6379/2",
    ),
    include=["app.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_default_queue="rag0",
    task_track_started=True,
    result_expires=86400,
    broker_connection_retry_on_startup=True,
    worker_prefetch_multiplier=1,
)