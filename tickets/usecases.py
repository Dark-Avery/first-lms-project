from __future__ import annotations

from uuid import UUID

from django.utils import timezone

from events.exceptions import EventNotFound, EventUnpublished, SeatPatternError
from events.seat_patterns import seat_exists
from events.selectors import get_event_by_id
from events.services import (
    get_available_seats_for_event,
    invalidate_event_seats_cache,
)
from integrations.events_provider.client import EventsProviderClient
from integrations.events_provider.exceptions import ProviderBusinessError
from tickets.exceptions import RegistrationClosed, TicketSeatInvalid, TicketSeatUnavailable
from tickets.models import Ticket


class CreateTicketUseCase:
    def __init__(self, client: EventsProviderClient) -> None:
        self.client = client

    def execute(
        self,
        *,
        event_id: UUID,
        first_name: str,
        last_name: str,
        email: str,
        seat: str,
    ) -> str:
        event = get_event_by_id(event_id=event_id)
        if event is None:
            raise EventNotFound
        if event.status != "published":
            raise EventUnpublished
        now = timezone.now()
        if now >= event.registration_deadline or now >= event.event_time:
            raise RegistrationClosed

        try:
            if not seat_exists(event.place.seats_pattern, seat):
                raise TicketSeatInvalid
        except SeatPatternError as error:
            raise TicketSeatInvalid from error

        available_seats = get_available_seats_for_event(event, client=self.client)
        if seat not in available_seats:
            raise TicketSeatUnavailable

        try:
            ticket_id = self.client.register(
                str(event.id),
                first_name=first_name,
                last_name=last_name,
                email=email,
                seat=seat,
            )
        except ProviderBusinessError as error:
            raise TicketSeatUnavailable from error

        Ticket.objects.create(
            ticket_id=ticket_id,
            event=event,
            first_name=first_name,
            last_name=last_name,
            email=email,
            seat=seat,
        )
        invalidate_event_seats_cache(event.id)
        return ticket_id
