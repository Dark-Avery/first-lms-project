from unittest.mock import Mock, call

import pytest

from integrations.events_provider.exceptions import ProviderTemporaryError
from integrations.events_provider.paginator import EventsPaginator


def test_paginator_yields_single_page_results():
    client = Mock()
    client.events.return_value = {
        "next": None,
        "previous": None,
        "results": [{"id": "event-1"}, {"id": "event-2"}],
    }

    paginator = EventsPaginator(client, changed_at="2026-01-05")

    assert list(paginator) == [{"id": "event-1"}, {"id": "event-2"}]
    client.events.assert_called_once_with(changed_at="2026-01-05", page_url=None)


def test_paginator_follows_next_url_as_is():
    client = Mock()
    client.events.side_effect = [
        {
            "next": "http://provider.example/api/events/?changed_at=2026-01-05&cursor=abc",
            "previous": None,
            "results": [{"id": "event-1"}],
        },
        {
            "next": None,
            "previous": "http://provider.example/api/events/?changed_at=2026-01-05",
            "results": [{"id": "event-2"}],
        },
    ]

    paginator = EventsPaginator(client, changed_at="2026-01-05")

    assert list(paginator) == [{"id": "event-1"}, {"id": "event-2"}]
    assert client.events.call_args_list == [
        call(changed_at="2026-01-05", page_url=None),
        call(
            changed_at="2026-01-05",
            page_url="http://provider.example/api/events/?changed_at=2026-01-05&cursor=abc",
        ),
    ]


def test_paginator_returns_empty_sequence_for_empty_page():
    client = Mock()
    client.events.return_value = {
        "next": None,
        "previous": None,
        "results": [],
    }

    paginator = EventsPaginator(client, changed_at="2026-01-05")

    assert list(paginator) == []
    client.events.assert_called_once_with(changed_at="2026-01-05", page_url=None)


def test_paginator_preserves_provider_order_across_pages():
    client = Mock()
    client.events.side_effect = [
        {
            "next": "http://provider.example/api/events/?changed_at=2026-01-05&cursor=abc",
            "previous": None,
            "results": [{"id": "event-2"}, {"id": "event-4"}],
        },
        {
            "next": None,
            "previous": None,
            "results": [{"id": "event-5"}, {"id": "event-6"}],
        },
    ]

    paginator = EventsPaginator(client, changed_at="2026-01-05")

    assert [event["id"] for event in paginator] == [
        "event-2",
        "event-4",
        "event-5",
        "event-6",
    ]


def test_paginator_propagates_client_exceptions():
    client = Mock()
    client.events.side_effect = ProviderTemporaryError("boom")

    paginator = EventsPaginator(client, changed_at="2026-01-05")

    with pytest.raises(ProviderTemporaryError):
        list(paginator)
