"""
Celery application configuration for LABORA.
"""
import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "labora.settings")

app = Celery("labora")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
