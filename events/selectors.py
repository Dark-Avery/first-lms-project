from __future__ import annotations

from datetime import date

from django.db.models import QuerySet

from events.models import Event


def list_events(*, date_from: date | None) -> QuerySet[Event]:
    queryset = Event.objects.select_related("place").order_by("event_time", "id")

    if date_from is not None:
        queryset = queryset.filter(event_time__date__gte=date_from)

    return queryset
