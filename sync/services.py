from __future__ import annotations

import logging
from typing import Any

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from events.models import Event, Place
from integrations.events_provider.client import EventsProviderClient
from integrations.events_provider.paginator import EventsPaginator
from sync.exceptions import SyncAlreadyRunning
from sync.models import SyncRun, SyncState

logger = logging.getLogger(__name__)


class SyncEventsService:
    def __init__(
        self,
        client: EventsProviderClient,
        *,
        paginator_cls: type[EventsPaginator] = EventsPaginator,
        sync_start_date: str | None = None,
    ) -> None:
        self.client = client
        self.paginator_cls = paginator_cls
        self.sync_start_date = sync_start_date or settings.DEFAULT_SYNC_START_DATE

    def run(self) -> SyncRun:
        with transaction.atomic():
            state = self._get_locked_state()
            if state.sync_status == SyncState.Status.RUNNING:
                raise SyncAlreadyRunning("Sync is already running.")

            started_at = timezone.now()
            changed_at = self._build_changed_at(state)
            sync_run = SyncRun.objects.create(
                started_at=started_at,
                sync_status=SyncRun.Status.RUNNING,
            )

            logger.info(
                "Sync started.",
                extra={
                    "sync_run_id": sync_run.id,
                    "changed_at": changed_at,
                },
            )

            state.sync_status = SyncState.Status.RUNNING
            state.started_at = started_at
            state.finished_at = None
            state.last_error = ""
            state.save()

        max_changed_at = state.last_changed_at

        try:
            for event_payload in self.paginator_cls(self.client, changed_at=changed_at):
                place = self._upsert_place(event_payload["place"])
                self._upsert_event(event_payload, place)

                event_changed_at = self._parse_datetime(
                    event_payload["changed_at"],
                    field_name="event.changed_at",
                )
                if max_changed_at is None or event_changed_at > max_changed_at:
                    max_changed_at = event_changed_at
        except Exception as error:
            finished_at = timezone.now()
            sync_run.finished_at = finished_at
            sync_run.sync_status = SyncRun.Status.FAILED
            sync_run.last_error = str(error)
            sync_run.save(update_fields=["finished_at", "sync_status", "last_error"])

            state.sync_status = SyncState.Status.FAILED
            state.finished_at = finished_at
            state.last_error = str(error)
            state.save(update_fields=["sync_status", "finished_at", "last_error"])
            logger.exception(
                "Sync failed.",
                extra={
                    "sync_run_id": sync_run.id,
                    "changed_at": changed_at,
                },
            )
            raise

        finished_at = timezone.now()
        sync_run.finished_at = finished_at
        sync_run.sync_status = SyncRun.Status.SUCCESS
        sync_run.last_changed_at = max_changed_at
        sync_run.last_error = ""
        sync_run.save(
            update_fields=["finished_at", "sync_status", "last_changed_at", "last_error"]
        )

        state.last_sync_time = finished_at
        state.last_changed_at = max_changed_at
        state.sync_status = SyncState.Status.SUCCESS
        state.finished_at = finished_at
        state.last_error = ""
        state.save(
            update_fields=[
                "last_sync_time",
                "last_changed_at",
                "sync_status",
                "finished_at",
                "last_error",
            ]
        )

        logger.info(
            "Sync finished successfully.",
            extra={
                "sync_run_id": sync_run.id,
                "changed_at": changed_at,
                "last_changed_at": max_changed_at.isoformat() if max_changed_at else None,
            },
        )
        return sync_run

    def _get_state(self) -> SyncState:
        state, _ = SyncState.objects.get_or_create(pk=1)
        return state

    def _get_locked_state(self) -> SyncState:
        self._get_state()
        return SyncState.objects.select_for_update().get(pk=1)

    def _build_changed_at(self, state: SyncState) -> str:
        if state.last_changed_at is None:
            return self.sync_start_date
        return state.last_changed_at.date().isoformat()

    def _upsert_place(self, payload: dict[str, Any]) -> Place:
        place, _ = Place.objects.update_or_create(
            id=payload["id"],
            defaults={
                "name": payload["name"],
                "city": payload["city"],
                "address": payload["address"],
                "seats_pattern": payload["seats_pattern"],
                "created_at": self._parse_datetime(
                    payload["created_at"],
                    field_name="place.created_at",
                ),
                "changed_at": self._parse_datetime(
                    payload["changed_at"],
                    field_name="place.changed_at",
                ),
            },
        )
        return place

    def _upsert_event(self, payload: dict[str, Any], place: Place) -> Event:
        event, _ = Event.objects.update_or_create(
            id=payload["id"],
            defaults={
                "place": place,
                "name": payload["name"],
                "event_time": self._parse_datetime(
                    payload["event_time"],
                    field_name="event.event_time",
                ),
                "registration_deadline": self._parse_datetime(
                    payload["registration_deadline"],
                    field_name="event.registration_deadline",
                ),
                "status": payload["status"],
                "number_of_visitors": payload["number_of_visitors"],
                "created_at": self._parse_datetime(
                    payload["created_at"],
                    field_name="event.created_at",
                ),
                "changed_at": self._parse_datetime(
                    payload["changed_at"],
                    field_name="event.changed_at",
                ),
                "status_changed_at": self._parse_datetime(
                    payload["status_changed_at"],
                    field_name="event.status_changed_at",
                ),
            },
        )
        return event

    def _parse_datetime(self, value: str, *, field_name: str) -> timezone.datetime:
        parsed = parse_datetime(value)
        if parsed is None:
            raise ValueError(f"Provider returned invalid datetime for {field_name}.")
        return parsed
