from __future__ import annotations

import time
from datetime import timedelta
from unittest.mock import Mock
from uuid import uuid4

import pytest
from django.core.cache import cache
from django.test import override_settings
from django.utils import timezone

from events.models import Event, Place
from events.services import (
    build_event_seats_cache_key,
    get_available_seats_for_event,
)


def create_event(*, status: str = Event.Status.PUBLISHED) -> Event:
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
    return Event.objects.create(
        id=uuid4(),
        place=place,
        name="Python Meetup",
        event_time=now + timedelta(days=3),
        registration_deadline=now + timedelta(days=2),
        status=status,
        number_of_visitors=10,
        created_at=now - timedelta(days=1),
        changed_at=now,
        status_changed_at=now,
    )


@pytest.mark.django_db
def test_get_available_seats_for_event_uses_cache_before_provider_call():
    cache.clear()
    event = create_event()
    cache.set(build_event_seats_cache_key(event.id), ["A10", "A11"], timeout=30)
    client = Mock()

    seats = get_available_seats_for_event(event, client=client)

    assert seats == ["A10", "A11"]
    client.seats.assert_not_called()


@pytest.mark.django_db
@override_settings(SEATS_CACHE_TIMEOUT_SECONDS=1)
def test_get_available_seats_for_event_refreshes_cache_after_timeout():
    cache.clear()
    event = create_event()
    client = Mock()
    client.seats.side_effect = [["A10"], ["A11"]]

    first_seats = get_available_seats_for_event(event, client=client)
    time.sleep(1.1)
    second_seats = get_available_seats_for_event(event, client=client)

    assert first_seats == ["A10"]
    assert second_seats == ["A11"]
    assert client.seats.call_count == 2
