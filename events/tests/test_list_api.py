from __future__ import annotations

from datetime import timedelta
from uuid import UUID

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from events.models import Event, Place


def create_place(*, place_id: str, name: str = "Hall") -> Place:
    timestamp = timezone.now()
    return Place.objects.create(
        id=UUID(place_id),
        name=name,
        city="Moscow",
        address="Lenina 1",
        seats_pattern="A1-100",
        created_at=timestamp,
        changed_at=timestamp,
    )


def create_event(
    *,
    event_id: str,
    place: Place,
    name: str,
    event_time,
    number_of_visitors: int = 0,
) -> Event:
    return Event.objects.create(
        id=UUID(event_id),
        place=place,
        name=name,
        event_time=event_time,
        registration_deadline=event_time - timedelta(days=1),
        status=Event.Status.PUBLISHED,
        number_of_visitors=number_of_visitors,
        created_at=event_time - timedelta(days=2),
        changed_at=event_time - timedelta(days=2),
        status_changed_at=event_time - timedelta(days=2),
    )


@pytest.mark.django_db
def test_event_list_returns_paginated_results_with_place_summary():
    client = APIClient()
    place = create_place(place_id="00000000-0000-0000-0000-000000000010")
    event_time = timezone.now() + timedelta(days=10)
    create_event(
        event_id="00000000-0000-0000-0000-000000000001",
        place=place,
        name="Python Conference",
        event_time=event_time,
        number_of_visitors=5,
    )

    response = client.get("/api/events")

    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 1
    assert payload["next"] is None
    assert payload["previous"] is None
    assert payload["results"] == [
        {
            "id": "00000000-0000-0000-0000-000000000001",
            "name": "Python Conference",
            "place": {
                "id": "00000000-0000-0000-0000-000000000010",
                "name": "Hall",
                "city": "Moscow",
                "address": "Lenina 1",
            },
            "event_time": event_time.isoformat().replace("+00:00", "Z"),
            "registration_deadline": (
                event_time - timedelta(days=1)
            ).isoformat().replace("+00:00", "Z"),
            "status": "published",
            "number_of_visitors": 5,
        }
    ]
    assert "seats_pattern" not in payload["results"][0]["place"]


@pytest.mark.django_db
def test_event_list_filters_by_date_from():
    client = APIClient()
    place = create_place(place_id="00000000-0000-0000-0000-000000000020")
    base_time = timezone.now().replace(hour=12, minute=0, second=0, microsecond=0)
    create_event(
        event_id="00000000-0000-0000-0000-000000000021",
        place=place,
        name="Old Event",
        event_time=base_time,
    )
    create_event(
        event_id="00000000-0000-0000-0000-000000000022",
        place=place,
        name="New Event",
        event_time=base_time + timedelta(days=2),
    )

    response = client.get(
        "/api/events",
        {"date_from": (base_time + timedelta(days=1)).date().isoformat()},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 1
    assert [item["name"] for item in payload["results"]] == ["New Event"]


@pytest.mark.django_db
def test_event_list_orders_by_event_time_then_id():
    client = APIClient()
    place = create_place(place_id="00000000-0000-0000-0000-000000000030")
    same_time = timezone.now() + timedelta(days=3)
    later_time = same_time + timedelta(hours=1)

    create_event(
        event_id="00000000-0000-0000-0000-000000000032",
        place=place,
        name="Later UUID",
        event_time=same_time,
    )
    create_event(
        event_id="00000000-0000-0000-0000-000000000031",
        place=place,
        name="Earlier UUID",
        event_time=same_time,
    )
    create_event(
        event_id="00000000-0000-0000-0000-000000000033",
        place=place,
        name="Later Time",
        event_time=later_time,
    )

    response = client.get("/api/events")

    assert response.status_code == 200
    assert [item["id"] for item in response.json()["results"]] == [
        "00000000-0000-0000-0000-000000000031",
        "00000000-0000-0000-0000-000000000032",
        "00000000-0000-0000-0000-000000000033",
    ]


@pytest.mark.django_db
def test_event_list_supports_page_and_page_size():
    client = APIClient()
    place = create_place(place_id="00000000-0000-0000-0000-000000000040")
    base_time = timezone.now() + timedelta(days=5)

    for index in range(3):
        create_event(
            event_id=f"00000000-0000-0000-0000-00000000004{index + 1}",
            place=place,
            name=f"Event {index + 1}",
            event_time=base_time + timedelta(hours=index),
        )

    response = client.get("/api/events", {"page_size": 1, "page": 2})

    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 3
    assert payload["previous"] is not None
    assert payload["next"] is not None
    assert [item["name"] for item in payload["results"]] == ["Event 2"]


@pytest.mark.django_db
def test_event_list_rejects_invalid_date_from():
    client = APIClient()

    response = client.get("/api/events", {"date_from": "invalid-date"})

    assert response.status_code == 400
    payload = response.json()
    assert list(payload) == ["date_from"]
    assert len(payload["date_from"]) == 1
