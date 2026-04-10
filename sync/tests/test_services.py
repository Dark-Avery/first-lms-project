from __future__ import annotations

from unittest.mock import Mock
from uuid import uuid4

import pytest
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from events.models import Event, Place
from sync.exceptions import SyncAlreadyRunning
from sync.models import SyncRun, SyncState
from sync.services import SyncEventsService


def build_event_payload(
    *,
    event_id: str | None = None,
    place_id: str | None = None,
    name: str = "Python Conference",
    place_name: str = "Main Hall",
    city: str = "Moscow",
    address: str = "Lenina 1",
    seats_pattern: str = "A1-100",
    event_time: str = "2026-01-11T17:00:00+03:00",
    registration_deadline: str = "2026-01-10T17:00:00+03:00",
    status: str = Event.Status.PUBLISHED,
    number_of_visitors: int = 5,
    changed_at: str = "2026-01-04T22:28:35+03:00",
    created_at: str = "2026-01-04T22:00:00+03:00",
    status_changed_at: str = "2026-01-04T22:28:35+03:00",
    place_changed_at: str = "2026-01-03T12:00:00+03:00",
    place_created_at: str = "2026-01-02T12:00:00+03:00",
) -> dict[str, object]:
    return {
        "id": event_id or str(uuid4()),
        "name": name,
        "place": {
            "id": place_id or str(uuid4()),
            "name": place_name,
            "city": city,
            "address": address,
            "seats_pattern": seats_pattern,
            "changed_at": place_changed_at,
            "created_at": place_created_at,
        },
        "event_time": event_time,
        "registration_deadline": registration_deadline,
        "status": status,
        "number_of_visitors": number_of_visitors,
        "changed_at": changed_at,
        "created_at": created_at,
        "status_changed_at": status_changed_at,
    }


@pytest.mark.django_db
def test_sync_uses_default_start_date_and_creates_place_and_event():
    client = Mock()
    payload = build_event_payload()
    paginator_cls = Mock(return_value=iter([payload]))
    service = SyncEventsService(
        client,
        paginator_cls=paginator_cls,
        sync_start_date="2000-01-01",
    )

    sync_run = service.run()

    paginator_cls.assert_called_once_with(client, changed_at="2000-01-01")
    state = SyncState.objects.get()
    event = Event.objects.get()
    place = Place.objects.get()

    assert sync_run.sync_status == SyncRun.Status.SUCCESS
    assert state.sync_status == SyncState.Status.SUCCESS
    assert state.last_changed_at == parse_datetime("2026-01-04T22:28:35+03:00")
    assert state.last_sync_time is not None
    assert str(event.id) == payload["id"]
    assert str(place.id) == payload["place"]["id"]


@pytest.mark.django_db
def test_sync_uses_existing_watermark_date_and_updates_records_without_duplicates():
    payload = build_event_payload(
        event_id=str(uuid4()),
        place_id=str(uuid4()),
        name="Updated Conference",
        place_name="Updated Hall",
        city="Saint Petersburg",
        address="Nevsky 1",
        seats_pattern="B1-50",
        number_of_visitors=12,
        changed_at="2026-01-07T15:30:00+03:00",
        place_changed_at="2026-01-06T12:00:00+03:00",
    )
    place = Place.objects.create(
        id=payload["place"]["id"],
        name="Old Hall",
        city="Old City",
        address="Old Address",
        seats_pattern="A1-10",
        created_at=parse_datetime("2026-01-01T12:00:00+03:00"),
        changed_at=parse_datetime("2026-01-01T12:00:00+03:00"),
    )
    Event.objects.create(
        id=payload["id"],
        place=place,
        name="Old Conference",
        event_time=parse_datetime("2026-01-11T17:00:00+03:00"),
        registration_deadline=parse_datetime("2026-01-10T17:00:00+03:00"),
        status=Event.Status.NEW,
        number_of_visitors=1,
        created_at=parse_datetime("2026-01-01T12:00:00+03:00"),
        changed_at=parse_datetime("2026-01-01T12:00:00+03:00"),
        status_changed_at=parse_datetime("2026-01-01T12:00:00+03:00"),
    )
    SyncState.objects.create(last_changed_at=parse_datetime("2026-01-07T09:00:00+03:00"))

    client = Mock()
    paginator_cls = Mock(return_value=iter([payload]))
    service = SyncEventsService(
        client,
        paginator_cls=paginator_cls,
        sync_start_date="2000-01-01",
    )

    service.run()

    paginator_cls.assert_called_once_with(client, changed_at="2026-01-07")
    assert Place.objects.count() == 1
    assert Event.objects.count() == 1

    updated_place = Place.objects.get()
    updated_event = Event.objects.get()
    assert updated_place.name == "Updated Hall"
    assert updated_place.city == "Saint Petersburg"
    assert updated_event.name == "Updated Conference"
    assert updated_event.status == Event.Status.PUBLISHED
    assert updated_event.number_of_visitors == 12


@pytest.mark.django_db
def test_sync_tracks_max_changed_at_and_creates_run_history():
    client = Mock()
    paginator_cls = Mock(
        return_value=iter(
            [
                build_event_payload(
                    changed_at="2026-01-04T10:00:00+03:00",
                    event_id=str(uuid4()),
                    place_id=str(uuid4()),
                ),
                build_event_payload(
                    changed_at="2026-01-05T15:30:00+03:00",
                    event_id=str(uuid4()),
                    place_id=str(uuid4()),
                ),
            ]
        )
    )
    service = SyncEventsService(
        client,
        paginator_cls=paginator_cls,
        sync_start_date="2000-01-01",
    )

    sync_run = service.run()
    state = SyncState.objects.get()

    assert SyncRun.objects.count() == 1
    assert sync_run.last_changed_at == parse_datetime("2026-01-05T15:30:00+03:00")
    assert state.last_changed_at == parse_datetime("2026-01-05T15:30:00+03:00")
    assert state.finished_at is not None


@pytest.mark.django_db
def test_failed_sync_marks_state_and_run_failed_without_advancing_watermark():
    old_changed_at = parse_datetime("2026-01-05T15:30:00+03:00")
    old_sync_time = timezone.now()
    SyncState.objects.create(
        last_changed_at=old_changed_at,
        last_sync_time=old_sync_time,
        sync_status=SyncState.Status.SUCCESS,
    )

    client = Mock()

    class FailingPaginator:
        def __iter__(self):
            raise RuntimeError("provider boom")

    paginator_cls = Mock(return_value=FailingPaginator())
    service = SyncEventsService(
        client,
        paginator_cls=paginator_cls,
        sync_start_date="2000-01-01",
    )

    with pytest.raises(RuntimeError, match="provider boom"):
        service.run()

    state = SyncState.objects.get()
    sync_run = SyncRun.objects.get()

    assert state.sync_status == SyncState.Status.FAILED
    assert state.last_error == "provider boom"
    assert state.last_changed_at == old_changed_at
    assert state.last_sync_time == old_sync_time
    assert sync_run.sync_status == SyncRun.Status.FAILED
    assert sync_run.last_error == "provider boom"


@pytest.mark.django_db
def test_sync_is_successful_when_provider_returns_no_events():
    client = Mock()
    paginator_cls = Mock(return_value=iter([]))
    service = SyncEventsService(
        client,
        paginator_cls=paginator_cls,
        sync_start_date="2000-01-01",
    )

    sync_run = service.run()
    state = SyncState.objects.get()

    assert sync_run.sync_status == SyncRun.Status.SUCCESS
    assert state.sync_status == SyncState.Status.SUCCESS
    assert state.last_changed_at is None
    assert Event.objects.count() == 0
    assert Place.objects.count() == 0


@pytest.mark.django_db
def test_sync_rejects_overlapping_run_without_creating_new_sync_run():
    SyncState.objects.create(sync_status=SyncState.Status.RUNNING)
    client = Mock()
    paginator_cls = Mock(return_value=iter([]))
    service = SyncEventsService(client, paginator_cls=paginator_cls)

    with pytest.raises(SyncAlreadyRunning, match="Sync is already running."):
        service.run()

    assert SyncRun.objects.count() == 0
    paginator_cls.assert_not_called()
