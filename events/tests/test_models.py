from datetime import timedelta
from uuid import uuid4

import pytest
from django.utils import timezone

from events.models import Event, Place


@pytest.mark.django_db
def test_event_can_be_created_with_place():
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

    event = Event.objects.create(
        id=uuid4(),
        place=place,
        name="Python Meetup",
        event_time=now + timedelta(days=3),
        registration_deadline=now + timedelta(days=2),
        status=Event.Status.PUBLISHED,
        number_of_visitors=10,
        created_at=now - timedelta(days=1),
        changed_at=now,
        status_changed_at=now,
    )

    assert event.place == place
    assert event.status == Event.Status.PUBLISHED
