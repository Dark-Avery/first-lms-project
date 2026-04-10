from __future__ import annotations

from celery import shared_task

from integrations.events_provider.client import EventsProviderClient
from sync.exceptions import SyncAlreadyRunning
from sync.services import SyncEventsService


@shared_task(name="sync.run_sync_events")
def run_sync_events() -> dict[str, int | str]:
    service = SyncEventsService(EventsProviderClient())
    try:
        sync_run = service.run()
    except SyncAlreadyRunning:
        return {
            "sync_run_id": "",
            "sync_status": "skipped",
        }
    return {
        "sync_run_id": sync_run.id,
        "sync_status": sync_run.sync_status,
    }
