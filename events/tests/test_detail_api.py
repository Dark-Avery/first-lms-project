from __future__ import annotations

from datetime import timedelta
from uuid import UUID

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from events.models import Event, Place


def create_place(*, place_id: str) -> Place:
    timestamp = timezone.now()
    return Place.objects.create(
        id=UUID(place_id),
        name="Hall",
        city="Moscow",
        address="Lenina 1",
        seats_pattern="A1-100",
        created_at=timestamp,
        changed_at=timestamp,
    )


def create_event(*, event_id: str, place: Place, event_time) -> Event:
    return Event.objects.create(
        id=UUID(event_id),
        place=place,
        name="Python Conference",
        event_time=event_time,
        registration_deadline=event_time - timedelta(days=1),
        status=Event.Status.PUBLISHED,
        number_of_visitors=5,
        created_at=event_time - timedelta(days=2),
        changed_at=event_time - timedelta(days=2),
        status_changed_at=event_time - timedelta(days=2),
    )


@pytest.mark.django_db
def test_event_detail_returns_event_with_place_seats_pattern():
    client = APIClient()
    place = create_place(place_id="00000000-0000-0000-0000-000000000050")
    event_time = timezone.now() + timedelta(days=10)
    event = create_event(
        event_id="00000000-0000-0000-0000-000000000051",
        place=place,
        event_time=event_time,
    )

    response = client.get(f"/api/events/{event.id}")

    assert response.status_code == 200
    assert response.json() == {
        "id": "00000000-0000-0000-0000-000000000051",
        "name": "Python Conference",
        "place": {
            "id": "00000000-0000-0000-0000-000000000050",
            "name": "Hall",
            "city": "Moscow",
            "address": "Lenina 1",
            "seats_pattern": "A1-100",
        },
        "event_time": event_time.isoformat().replace("+00:00", "Z"),
        "registration_deadline": (
            event_time - timedelta(days=1)
        ).isoformat().replace("+00:00", "Z"),
        "status": "published",
        "number_of_visitors": 5,
    }


@pytest.mark.django_db
def test_event_detail_returns_404_for_missing_event():
    client = APIClient()

    response = client.get("/api/events/00000000-0000-0000-0000-000000000099")

    assert response.status_code == 404
    assert response.json() == {"detail": "Not found."}
