from __future__ import annotations

from datetime import timedelta
from unittest.mock import Mock, patch
from uuid import UUID

import pytest
from django.core.cache import cache
from django.utils import timezone
from rest_framework.test import APIClient

from events.models import Event, Place
from events.services import build_event_seats_cache_key
from integrations.events_provider.exceptions import (
    ProviderBadResponseError,
    ProviderBusinessError,
)
from tickets.models import Ticket


def create_place(*, place_id: str, seats_pattern: str = "A1-100") -> Place:
    timestamp = timezone.now()
    return Place.objects.create(
        id=UUID(place_id),
        name="Hall",
        city="Moscow",
        address="Lenina 1",
        seats_pattern=seats_pattern,
        created_at=timestamp,
        changed_at=timestamp,
    )


def create_event(
    *,
    event_id: str,
    place: Place,
    status: str = Event.Status.PUBLISHED,
    registration_deadline=None,
) -> Event:
    event_time = timezone.now() + timedelta(days=10)
    return Event.objects.create(
        id=UUID(event_id),
        place=place,
        name="Python Conference",
        event_time=event_time,
        registration_deadline=registration_deadline or (event_time - timedelta(days=1)),
        status=status,
        number_of_visitors=5,
        created_at=event_time - timedelta(days=2),
        changed_at=event_time - timedelta(days=2),
        status_changed_at=event_time - timedelta(days=2),
    )


def build_payload(event_id: str, *, seat: str = "A10") -> dict[str, str]:
    return {
        "event_id": event_id,
        "first_name": "Ivan",
        "last_name": "Ivanov",
        "email": "ivan@example.com",
        "seat": seat,
    }


@pytest.mark.django_db
def test_ticket_create_returns_201_and_creates_local_ticket():
    cache.clear()
    client = APIClient()
    place = create_place(place_id="00000000-0000-0000-0000-000000000101")
    event = create_event(event_id="00000000-0000-0000-0000-000000000102", place=place)
    provider_client = Mock()
    provider_client.seats.return_value = ["A10", "A11"]
    provider_client.register.return_value = "00000000-0000-0000-0000-000000000199"
    cache.set(build_event_seats_cache_key(event.id), ["A10", "A11"], timeout=30)

    with patch("tickets.views.EventsProviderClient", return_value=provider_client):
        response = client.post("/api/tickets", build_payload(str(event.id)), format="json")

    assert response.status_code == 201
    assert response.json() == {"ticket_id": "00000000-0000-0000-0000-000000000199"}
    assert Ticket.objects.count() == 1
    ticket = Ticket.objects.get()
    assert str(ticket.ticket_id) == "00000000-0000-0000-0000-000000000199"
    assert ticket.status == Ticket.Status.ACTIVE
    assert cache.get(build_event_seats_cache_key(event.id)) is None
    provider_client.seats.assert_not_called()
    provider_client.register.assert_called_once_with(
        str(event.id),
        first_name="Ivan",
        last_name="Ivanov",
        email="ivan@example.com",
        seat="A10",
    )


@pytest.mark.django_db
def test_ticket_create_rejects_invalid_request_without_provider_call():
    client = APIClient()

    with patch("tickets.views.EventsProviderClient") as provider_cls:
        response = client.post(
            "/api/tickets",
            {"event_id": "broken", "email": "bad", "seat": "A10"},
            format="json",
        )

    assert response.status_code == 400
    provider_cls.assert_not_called()


@pytest.mark.django_db
def test_ticket_create_returns_404_for_missing_event():
    client = APIClient()

    with patch("tickets.views.EventsProviderClient") as provider_cls:
        response = client.post(
            "/api/tickets",
            build_payload("00000000-0000-0000-0000-000000000109"),
            format="json",
        )

    assert response.status_code == 404
    assert response.json() == {"detail": "Not found."}
    assert Ticket.objects.count() == 0
    provider_cls.assert_called_once()
    provider_cls.return_value.seats.assert_not_called()
    provider_cls.return_value.register.assert_not_called()


@pytest.mark.django_db
def test_ticket_create_rejects_unpublished_event_without_provider_calls():
    client = APIClient()
    place = create_place(place_id="00000000-0000-0000-0000-000000000111")
    event = create_event(
        event_id="00000000-0000-0000-0000-000000000112",
        place=place,
        status=Event.Status.NEW,
    )

    with patch("tickets.views.EventsProviderClient") as provider_cls:
        response = client.post("/api/tickets", build_payload(str(event.id)), format="json")

    assert response.status_code == 400
    assert response.json() == {"detail": "Event is not published."}
    assert Ticket.objects.count() == 0
    provider_cls.return_value.seats.assert_not_called()
    provider_cls.return_value.register.assert_not_called()


@pytest.mark.django_db
def test_ticket_create_rejects_closed_registration_without_provider_calls():
    client = APIClient()
    place = create_place(place_id="00000000-0000-0000-0000-000000000121")
    event = create_event(
        event_id="00000000-0000-0000-0000-000000000122",
        place=place,
        registration_deadline=timezone.now() - timedelta(minutes=1),
    )

    with patch("tickets.views.EventsProviderClient") as provider_cls:
        response = client.post("/api/tickets", build_payload(str(event.id)), format="json")

    assert response.status_code == 400
    assert response.json() == {"detail": "Registration is closed."}
    assert Ticket.objects.count() == 0
    provider_cls.return_value.seats.assert_not_called()
    provider_cls.return_value.register.assert_not_called()


@pytest.mark.django_db
def test_ticket_create_rejects_invalid_seat_pattern_without_provider_calls():
    client = APIClient()
    place = create_place(
        place_id="00000000-0000-0000-0000-000000000131",
        seats_pattern="A1-5",
    )
    event = create_event(event_id="00000000-0000-0000-0000-000000000132", place=place)

    with patch("tickets.views.EventsProviderClient") as provider_cls:
        response = client.post(
            "/api/tickets",
            build_payload(str(event.id), seat="B10"),
            format="json",
        )

    assert response.status_code == 400
    assert response.json() == {"detail": "Seat is invalid."}
    assert Ticket.objects.count() == 0
    provider_cls.return_value.seats.assert_not_called()
    provider_cls.return_value.register.assert_not_called()


@pytest.mark.django_db
def test_ticket_create_rejects_malformed_local_seat_pattern_without_provider_calls():
    client = APIClient()
    place = create_place(
        place_id="00000000-0000-0000-0000-000000000135",
        seats_pattern="A10-1",
    )
    event = create_event(event_id="00000000-0000-0000-0000-000000000136", place=place)

    with patch("tickets.views.EventsProviderClient") as provider_cls:
        response = client.post(
            "/api/tickets",
            build_payload(str(event.id), seat="A10"),
            format="json",
        )

    assert response.status_code == 400
    assert response.json() == {"detail": "Seat is invalid."}
    assert Ticket.objects.count() == 0
    provider_cls.return_value.seats.assert_not_called()
    provider_cls.return_value.register.assert_not_called()


@pytest.mark.django_db
def test_ticket_create_rejects_past_event_without_provider_calls():
    client = APIClient()
    place = create_place(place_id="00000000-0000-0000-0000-000000000133")
    event_time = timezone.now() - timedelta(minutes=5)
    event = Event.objects.create(
        id=UUID("00000000-0000-0000-0000-000000000134"),
        place=place,
        name="Past Conference",
        event_time=event_time,
        registration_deadline=timezone.now() + timedelta(minutes=5),
        status=Event.Status.PUBLISHED,
        number_of_visitors=5,
        created_at=event_time - timedelta(days=2),
        changed_at=event_time - timedelta(days=2),
        status_changed_at=event_time - timedelta(days=2),
    )

    with patch("tickets.views.EventsProviderClient") as provider_cls:
        response = client.post("/api/tickets", build_payload(str(event.id)), format="json")

    assert response.status_code == 400
    assert response.json() == {"detail": "Registration is closed."}
    assert Ticket.objects.count() == 0
    provider_cls.return_value.seats.assert_not_called()
    provider_cls.return_value.register.assert_not_called()


@pytest.mark.django_db
def test_ticket_create_rejects_unavailable_seat_without_register_call():
    cache.clear()
    client = APIClient()
    place = create_place(place_id="00000000-0000-0000-0000-000000000141")
    event = create_event(event_id="00000000-0000-0000-0000-000000000142", place=place)
    provider_client = Mock()
    provider_client.seats.return_value = ["A11", "A12"]

    with patch("tickets.views.EventsProviderClient", return_value=provider_client):
        response = client.post("/api/tickets", build_payload(str(event.id)), format="json")

    assert response.status_code == 400
    assert response.json() == {"detail": "Seat is unavailable."}
    provider_client.register.assert_not_called()
    assert Ticket.objects.count() == 0


@pytest.mark.django_db
def test_ticket_create_maps_provider_seats_failure_to_502_without_local_ticket():
    cache.clear()
    client = APIClient()
    place = create_place(place_id="00000000-0000-0000-0000-000000000143")
    event = create_event(event_id="00000000-0000-0000-0000-000000000144", place=place)
    provider_client = Mock()
    provider_client.seats.side_effect = ProviderBadResponseError("html")

    with patch("tickets.views.EventsProviderClient", return_value=provider_client):
        response = client.post("/api/tickets", build_payload(str(event.id)), format="json")

    assert response.status_code == 502
    assert response.json() == {"detail": "Registration unavailable."}
    assert Ticket.objects.count() == 0
    provider_client.register.assert_not_called()
    assert cache.get(build_event_seats_cache_key(event.id)) is None


@pytest.mark.django_db
def test_ticket_create_maps_provider_race_case_to_400_without_local_ticket():
    cache.clear()
    client = APIClient()
    place = create_place(place_id="00000000-0000-0000-0000-000000000151")
    event = create_event(event_id="00000000-0000-0000-0000-000000000152", place=place)
    provider_client = Mock()
    provider_client.seats.return_value = ["A10", "A11"]
    provider_client.register.side_effect = ProviderBusinessError("already sold")

    with patch("tickets.views.EventsProviderClient", return_value=provider_client):
        response = client.post("/api/tickets", build_payload(str(event.id)), format="json")

    assert response.status_code == 400
    assert response.json() == {"detail": "Seat is unavailable."}
    assert cache.get(build_event_seats_cache_key(event.id)) == ["A10", "A11"]
    assert Ticket.objects.count() == 0


@pytest.mark.django_db
def test_ticket_create_maps_provider_failure_to_502_without_cache_invalidation():
    cache.clear()
    client = APIClient()
    place = create_place(place_id="00000000-0000-0000-0000-000000000161")
    event = create_event(event_id="00000000-0000-0000-0000-000000000162", place=place)
    provider_client = Mock()
    provider_client.seats.return_value = ["A10", "A11"]
    provider_client.register.side_effect = ProviderBadResponseError("html")
    cache_key = build_event_seats_cache_key(event.id)
    cache.set(cache_key, ["A10"], timeout=30)

    with patch("tickets.views.EventsProviderClient", return_value=provider_client):
        response = client.post("/api/tickets", build_payload(str(event.id)), format="json")

    assert response.status_code == 502
    assert response.json() == {"detail": "Registration unavailable."}
    assert cache.get(cache_key) == ["A10"]
    assert Ticket.objects.count() == 0
