from __future__ import annotations

from datetime import timedelta
from unittest.mock import Mock, patch
from uuid import UUID

import pytest
from django.core.cache import cache
from django.utils import timezone
from rest_framework.test import APIClient

from events.models import Event, Place
from integrations.events_provider.exceptions import ProviderBadResponseError


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


def create_event(
    *, event_id: str, place: Place, status: str = Event.Status.PUBLISHED
) -> Event:
    event_time = timezone.now() + timedelta(days=10)
    return Event.objects.create(
        id=UUID(event_id),
        place=place,
        name="Python Conference",
        event_time=event_time,
        registration_deadline=event_time - timedelta(days=1),
        status=status,
        number_of_visitors=5,
        created_at=event_time - timedelta(days=2),
        changed_at=event_time - timedelta(days=2),
        status_changed_at=event_time - timedelta(days=2),
    )


@pytest.mark.django_db
def test_event_seats_returns_available_seats_for_published_event():
    cache.clear()
    client = APIClient()
    place = create_place(place_id="00000000-0000-0000-0000-000000000060")
    event = create_event(
        event_id="00000000-0000-0000-0000-000000000061",
        place=place,
    )

    provider_client = Mock()
    provider_client.seats.return_value = ["A1", "A3"]

    with patch("events.services.EventsProviderClient", return_value=provider_client):
        response = client.get(f"/api/events/{event.id}/seats")

    assert response.status_code == 200
    assert response.json() == {
        "event_id": "00000000-0000-0000-0000-000000000061",
        "available_seats": ["A1", "A3"],
    }
    provider_client.seats.assert_called_once_with("00000000-0000-0000-0000-000000000061")


@pytest.mark.django_db
def test_event_seats_returns_404_without_provider_call_for_missing_event():
    cache.clear()
    client = APIClient()

    with patch("events.services.EventsProviderClient") as provider_cls:
        response = client.get("/api/events/00000000-0000-0000-0000-000000000069/seats")

    assert response.status_code == 404
    assert response.json() == {"detail": "Not found."}
    provider_cls.assert_not_called()


@pytest.mark.django_db
def test_event_seats_returns_400_without_provider_call_for_unpublished_event():
    cache.clear()
    client = APIClient()
    place = create_place(place_id="00000000-0000-0000-0000-000000000070")
    event = create_event(
        event_id="00000000-0000-0000-0000-000000000071",
        place=place,
        status=Event.Status.NEW,
    )

    with patch("events.services.EventsProviderClient") as provider_cls:
        response = client.get(f"/api/events/{event.id}/seats")

    assert response.status_code == 400
    assert response.json() == {"detail": "Event is not published."}
    provider_cls.assert_not_called()


@pytest.mark.django_db
def test_event_seats_caches_successful_provider_response():
    cache.clear()
    client = APIClient()
    place = create_place(place_id="00000000-0000-0000-0000-000000000080")
    event = create_event(
        event_id="00000000-0000-0000-0000-000000000081",
        place=place,
    )

    provider_client = Mock()
    provider_client.seats.return_value = ["A1", "A3"]

    with patch("events.services.EventsProviderClient", return_value=provider_client):
        first_response = client.get(f"/api/events/{event.id}/seats")
        second_response = client.get(f"/api/events/{event.id}/seats")

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert provider_client.seats.call_count == 1


@pytest.mark.django_db
def test_event_seats_does_not_cache_provider_failure():
    cache.clear()
    client = APIClient()
    place = create_place(place_id="00000000-0000-0000-0000-000000000090")
    event = create_event(
        event_id="00000000-0000-0000-0000-000000000091",
        place=place,
    )

    provider_client = Mock()
    provider_client.seats.side_effect = ProviderBadResponseError("bad html")

    with patch("events.services.EventsProviderClient", return_value=provider_client):
        first_response = client.get(f"/api/events/{event.id}/seats")
        second_response = client.get(f"/api/events/{event.id}/seats")

    assert first_response.status_code == 502
    assert first_response.json() == {"detail": "Seats unavailable."}
    assert second_response.status_code == 502
    assert provider_client.seats.call_count == 2
