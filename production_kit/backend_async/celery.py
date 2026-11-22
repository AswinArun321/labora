"""
LABORA Celery Application Configuration
"""
import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "labora.settings")

app = Celery("labora")

# Load configuration from Django settings, namespace with CELERY_
app.config_from_object("django.conf:settings", namespace="CELERY")

# Automatic task discovery across all registered Django apps
app.autodiscover_tasks()

app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Kolkata",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=120,          # Hard limit 2 minutes per task
    task_soft_time_limit=90,     # Soft limit 90 seconds
    worker_concurrency=8,        # Process up to 8 parallel execution tasks per worker
    worker_prefetch_multiplier=1 # Fair task distribution among workers
)
