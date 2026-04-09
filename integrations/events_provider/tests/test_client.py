from unittest.mock import Mock

import pytest
import requests

from integrations.events_provider.client import EventsProviderClient
from integrations.events_provider.exceptions import (
    ProviderAuthError,
    ProviderBadResponseError,
    ProviderBusinessError,
    ProviderNotFoundError,
    ProviderRateLimitError,
    ProviderTemporaryError,
)


def make_response(*, status_code=200, json_data=None, headers=None):
    response = Mock(spec=requests.Response)
    response.status_code = status_code
    response.headers = headers or {"Content-Type": "application/json"}
    response.json = Mock(return_value=json_data)
    return response


def test_events_request_uses_trailing_slash_and_api_key_header():
    session = Mock()
    session.request.return_value = make_response(
        json_data={"next": None, "previous": None, "results": []}
    )
    client = EventsProviderClient(
        base_url="http://provider.example",
        api_key="secret",
        timeout=5,
        session=session,
    )

    payload = client.events(changed_at="2026-01-05")

    assert payload == {"next": None, "previous": None, "results": []}
    session.request.assert_called_once_with(
        "GET",
        "http://provider.example/api/events/",
        headers={"x-api-key": "secret"},
        timeout=5,
        params={"changed_at": "2026-01-05"},
    )


def test_events_request_uses_next_page_url_as_is():
    session = Mock()
    session.request.return_value = make_response(
        json_data={"next": None, "previous": None, "results": []}
    )
    client = EventsProviderClient(base_url="http://provider.example", session=session)

    client.events(
        changed_at="2026-01-05",
        page_url="http://provider.example/api/events/?changed_at=2026-01-05&cursor=abc",
    )

    session.request.assert_called_once_with(
        "GET",
        "http://provider.example/api/events/?changed_at=2026-01-05&cursor=abc",
        headers={"x-api-key": ""},
        timeout=10,
        params=None,
    )


def test_seats_returns_available_seats_list():
    session = Mock()
    session.request.return_value = make_response(json_data={"seats": ["A1", "B2"]})
    client = EventsProviderClient(base_url="http://provider.example", session=session)

    assert client.seats("event-1") == ["A1", "B2"]

    session.request.assert_called_once_with(
        "GET",
        "http://provider.example/api/events/event-1/seats/",
        headers={"x-api-key": ""},
        timeout=10,
        params=None,
    )


def test_register_returns_provider_ticket_id():
    session = Mock()
    session.request.return_value = make_response(json_data={"ticket_id": "ticket-1"})
    client = EventsProviderClient(base_url="http://provider.example", session=session)

    assert (
        client.register(
            "event-1",
            first_name="Ivan",
            last_name="Ivanov",
            email="ivan@example.com",
            seat="A10",
        )
        == "ticket-1"
    )

    session.request.assert_called_once_with(
        "POST",
        "http://provider.example/api/events/event-1/register/",
        headers={"x-api-key": ""},
        timeout=10,
        json={
            "first_name": "Ivan",
            "last_name": "Ivanov",
            "email": "ivan@example.com",
            "seat": "A10",
        },
        params=None,
    )


def test_unregister_sends_ticket_id_in_delete_body():
    session = Mock()
    session.request.return_value = make_response(json_data={"success": True})
    client = EventsProviderClient(base_url="http://provider.example", session=session)

    assert client.unregister("event-1", ticket_id="ticket-1") is True

    session.request.assert_called_once_with(
        "DELETE",
        "http://provider.example/api/events/event-1/unregister/",
        headers={"x-api-key": ""},
        timeout=10,
        json={"ticket_id": "ticket-1"},
        params=None,
    )


@pytest.mark.parametrize(
    ("status_code", "exception_type"),
    [
        (401, ProviderAuthError),
        (404, ProviderNotFoundError),
        (429, ProviderRateLimitError),
    ],
)
def test_client_maps_specific_status_codes(status_code, exception_type):
    session = Mock()
    session.request.return_value = make_response(
        status_code=status_code,
        json_data={"detail": "error"},
    )
    client = EventsProviderClient(base_url="http://provider.example", session=session)

    with pytest.raises(exception_type):
        client.seats("event-1")


def test_client_maps_html_500_to_bad_response():
    session = Mock()
    session.request.return_value = make_response(
        status_code=500,
        json_data=None,
        headers={"Content-Type": "text/html"},
    )
    client = EventsProviderClient(base_url="http://provider.example", session=session)

    with pytest.raises(ProviderBadResponseError):
        client.seats("event-1")


@pytest.mark.parametrize("error_type", [requests.Timeout, requests.ConnectionError])
def test_client_maps_network_error_to_temporary_error(error_type):
    session = Mock()
    session.request.side_effect = error_type("boom")
    client = EventsProviderClient(base_url="http://provider.example", session=session)

    with pytest.raises(ProviderTemporaryError):
        client.events(changed_at="2026-01-05")


def test_client_maps_provider_business_error_from_json_list():
    session = Mock()
    session.request.return_value = make_response(
        status_code=400,
        json_data=["This ticket is not available (already sold)."],
    )
    client = EventsProviderClient(base_url="http://provider.example", session=session)

    with pytest.raises(ProviderBusinessError) as error:
        client.register(
            "event-1",
            first_name="Ivan",
            last_name="Ivanov",
            email="ivan@example.com",
            seat="A10",
        )

    assert "already sold" in str(error.value)


def test_client_maps_invalid_json_success_response_to_bad_response():
    session = Mock()
    response = make_response(json_data={"unexpected": "payload"})
    response.json.side_effect = ValueError("invalid json")
    session.request.return_value = response
    client = EventsProviderClient(base_url="http://provider.example", session=session)

    with pytest.raises(ProviderBadResponseError):
        client.seats("event-1")


def test_client_maps_malformed_events_payload_to_bad_response():
    session = Mock()
    session.request.return_value = make_response(
        json_data={"next": None, "previous": None, "results": "not-a-list"}
    )
    client = EventsProviderClient(base_url="http://provider.example", session=session)

    with pytest.raises(ProviderBadResponseError):
        client.events(changed_at="2026-01-05")
