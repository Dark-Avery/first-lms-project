from __future__ import annotations

from celery.schedules import crontab
from django.conf import settings

from config.celery import app as celery_app


def test_run_sync_events_task_is_registered_in_celery_app():
    assert "sync.run_sync_events" in celery_app.tasks


def test_daily_sync_schedule_targets_sync_task():
    schedule_entry = settings.CELERY_BEAT_SCHEDULE["daily-events-sync"]

    assert schedule_entry["task"] == "sync.run_sync_events"
    assert isinstance(schedule_entry["schedule"], crontab)
    assert settings.CELERY_TIMEZONE == settings.TIME_ZONE
