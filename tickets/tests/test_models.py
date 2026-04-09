from datetime import timedelta
from uuid import uuid4

import pytest
from django.utils import timezone

from events.models import Event, Place
from tickets.models import Ticket


def create_event():
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
        status="published",
        number_of_visitors=10,
        created_at=now - timedelta(days=1),
        changed_at=now,
        status_changed_at=now,
    )


@pytest.mark.django_db
def test_ticket_id_can_be_reused_in_local_history():
    event = create_event()
    provider_ticket_id = uuid4()
    first = Ticket.objects.create(
        ticket_id=provider_ticket_id,
        event=event,
        first_name="Ivan",
        last_name="Ivanov",
        email="ivan@example.com",
        seat="A10",
    )
    second = Ticket.objects.create(
        ticket_id=provider_ticket_id,
        event=event,
        first_name="Petr",
        last_name="Petrov",
        email="petr@example.com",
        seat="A11",
    )

    assert first.ticket_id == second.ticket_id
    assert Ticket.objects.count() == 2
