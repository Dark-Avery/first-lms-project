from __future__ import annotations

from uuid import UUID

from django.conf import settings
from django.core.cache import cache

from events.exceptions import EventNotFound, EventUnpublished
from events.models import Event
from events.selectors import get_event_by_id
from integrations.events_provider.client import EventsProviderClient


def build_event_seats_cache_key(event_id: UUID) -> str:
    return f"event-seats:{event_id}"


def invalidate_event_seats_cache(event_id: UUID) -> None:
    cache.delete(build_event_seats_cache_key(event_id))


def get_available_seats_for_event(
    event: Event,
    *,
    client: EventsProviderClient | None = None,
) -> list[str]:
    cache_key = build_event_seats_cache_key(event.id)
    cached_seats = cache.get(cache_key)
    if cached_seats is not None:
        return cached_seats

    seats_client = client or EventsProviderClient()
    available_seats = seats_client.seats(str(event.id))
    cache.set(cache_key, available_seats, timeout=settings.SEATS_CACHE_TIMEOUT_SECONDS)
    return available_seats


def get_available_seats(
    event_id: UUID,
    *,
    client: EventsProviderClient | None = None,
) -> list[str]:
    event = get_event_by_id(event_id=event_id)
    if event is None:
        raise EventNotFound
    if event.status != "published":
        raise EventUnpublished

    return get_available_seats_for_event(event, client=client)
