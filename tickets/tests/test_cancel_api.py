from __future__ import annotations

from datetime import timedelta
from unittest.mock import Mock, patch
from uuid import UUID, uuid4

import pytest
from django.core.cache import cache
from django.utils import timezone
from rest_framework.test import APIClient

from events.models import Event, Place
from events.services import build_event_seats_cache_key
from integrations.events_provider.exceptions import ProviderBadResponseError
from tickets.models import Ticket


def create_event(*, event_time=None) -> Event:
    now = timezone.now()
    place = Place.objects.create(
        id=uuid4(),
        name="Main Hall",
        city="Moscow",
        address="Lenina 1",
        seats_pattern="A1-100",
        created_at=now - timedelta(days=1),
        changed_at=now,
    )
    actual_event_time = event_time or (now + timedelta(days=3))
    return Event.objects.create(
        id=uuid4(),
        place=place,
        name="Python Meetup",
        event_time=actual_event_time,
        registration_deadline=actual_event_time - timedelta(days=1),
        status=Event.Status.PUBLISHED,
        number_of_visitors=10,
        created_at=now - timedelta(days=1),
        changed_at=now,
        status_changed_at=now,
    )


def create_ticket(
    *,
    event: Event,
    provider_ticket_id: UUID,
    status: str = Ticket.Status.ACTIVE,
    created_at=None,
) -> Ticket:
    ticket = Ticket.objects.create(
        ticket_id=provider_ticket_id,
        event=event,
        first_name="Ivan",
        last_name="Ivanov",
        email="ivan@example.com",
        seat="A10",
        status=status,
    )
    if created_at is not None:
        Ticket.objects.filter(id=ticket.id).update(created_at=created_at)
        ticket.refresh_from_db()
    return ticket


@pytest.mark.django_db
def test_ticket_cancel_returns_200_and_marks_ticket_cancelled():
    cache.clear()
    client = APIClient()
    event = create_event()
    ticket = create_ticket(
        event=event,
        provider_ticket_id=UUID("00000000-0000-0000-0000-000000000201"),
    )
    provider_client = Mock()
    provider_client.unregister.return_value = True
    cache_key = build_event_seats_cache_key(event.id)
    cache.set(cache_key, ["A10"], timeout=30)

    with patch("tickets.views.EventsProviderClient", return_value=provider_client):
        response = client.delete(f"/api/tickets/{ticket.ticket_id}")

    assert response.status_code == 200
    assert response.json() == {"success": True}
    ticket.refresh_from_db()
    assert ticket.status == Ticket.Status.CANCELLED
    assert ticket.cancelled_at is not None
    assert cache.get(cache_key) is None
    provider_client.unregister.assert_called_once_with(
        str(event.id),
        ticket_id=str(ticket.ticket_id),
    )


@pytest.mark.django_db
def test_ticket_cancel_returns_404_for_missing_ticket():
    client = APIClient()

    with patch("tickets.views.EventsProviderClient") as provider_cls:
        response = client.delete("/api/tickets/00000000-0000-0000-0000-000000000202")

    assert response.status_code == 404
    assert response.json() == {"detail": "Not found."}
    provider_cls.assert_called_once()
    provider_cls.return_value.unregister.assert_not_called()


@pytest.mark.django_db
def test_ticket_cancel_rejects_already_cancelled_ticket_without_provider_call():
    client = APIClient()
    event = create_event()
    ticket = create_ticket(
        event=event,
        provider_ticket_id=UUID("00000000-0000-0000-0000-000000000203"),
        status=Ticket.Status.CANCELLED,
    )

    with patch("tickets.views.EventsProviderClient") as provider_cls:
        response = client.delete(f"/api/tickets/{ticket.ticket_id}")

    assert response.status_code == 400
    assert response.json() == {"detail": "Ticket is already cancelled."}
    provider_cls.assert_called_once()
    provider_cls.return_value.unregister.assert_not_called()


@pytest.mark.django_db
def test_ticket_cancel_rejects_past_event_without_provider_call():
    client = APIClient()
    event = create_event(event_time=timezone.now() - timedelta(minutes=1))
    ticket = create_ticket(
        event=event,
        provider_ticket_id=UUID("00000000-0000-0000-0000-000000000204"),
    )

    with patch("tickets.views.EventsProviderClient") as provider_cls:
        response = client.delete(f"/api/tickets/{ticket.ticket_id}")

    assert response.status_code == 400
    assert response.json() == {"detail": "Ticket cancellation is closed."}
    ticket.refresh_from_db()
    assert ticket.status == Ticket.Status.ACTIVE
    assert ticket.cancelled_at is None
    provider_cls.assert_called_once()
    provider_cls.return_value.unregister.assert_not_called()


@pytest.mark.django_db
def test_ticket_cancel_prefers_active_ticket_when_provider_ticket_id_is_reused():
    client = APIClient()
    event = create_event()
    provider_ticket_id = UUID("00000000-0000-0000-0000-000000000205")
    create_ticket(
        event=event,
        provider_ticket_id=provider_ticket_id,
        status=Ticket.Status.CANCELLED,
        created_at=timezone.now() - timedelta(days=1),
    )
    active_ticket = create_ticket(
        event=event,
        provider_ticket_id=provider_ticket_id,
        status=Ticket.Status.ACTIVE,
    )
    provider_client = Mock()
    provider_client.unregister.return_value = True

    with patch("tickets.views.EventsProviderClient", return_value=provider_client):
        response = client.delete(f"/api/tickets/{provider_ticket_id}")

    assert response.status_code == 200
    active_ticket.refresh_from_db()
    assert active_ticket.status == Ticket.Status.CANCELLED
    provider_client.unregister.assert_called_once_with(
        str(event.id),
        ticket_id=str(provider_ticket_id),
    )


@pytest.mark.django_db
def test_ticket_cancel_maps_provider_failure_to_502_without_local_changes():
    cache.clear()
    client = APIClient()
    event = create_event()
    ticket = create_ticket(
        event=event,
        provider_ticket_id=UUID("00000000-0000-0000-0000-000000000206"),
    )
    provider_client = Mock()
    provider_client.unregister.side_effect = ProviderBadResponseError("html")
    cache_key = build_event_seats_cache_key(event.id)
    cache.set(cache_key, ["A10"], timeout=30)

    with patch("tickets.views.EventsProviderClient", return_value=provider_client):
        response = client.delete(f"/api/tickets/{ticket.ticket_id}")

    assert response.status_code == 502
    assert response.json() == {"detail": "Cancellation unavailable."}
    ticket.refresh_from_db()
    assert ticket.status == Ticket.Status.ACTIVE
    assert ticket.cancelled_at is None
    assert cache.get(cache_key) == ["A10"]
