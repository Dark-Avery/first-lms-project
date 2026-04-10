from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from integrations.events_provider.client import EventsProviderClient


class EventsPaginator:
    def __init__(self, client: EventsProviderClient, *, changed_at: str) -> None:
        self.client = client
        self.changed_at = changed_at

    def __iter__(self) -> Iterator[dict[str, Any]]:
        next_page_url: str | None = None

        while True:
            page = self.client.events(
                changed_at=self.changed_at,
                page_url=next_page_url,
            )

            for event in page["results"]:
                yield event

            next_page_url = page["next"]
            if next_page_url is None:
                break
