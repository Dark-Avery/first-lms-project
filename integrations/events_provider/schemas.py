from typing import Any
from uuid import UUID


def validate_events_page(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise TypeError("Provider response must be a JSON object.")

    next_url = payload.get("next")
    previous_url = payload.get("previous")
    results = payload.get("results")

    if next_url is not None and not isinstance(next_url, str):
        raise TypeError("Provider response field 'next' must be a string or null.")
    if previous_url is not None and not isinstance(previous_url, str):
        raise TypeError("Provider response field 'previous' must be a string or null.")
    if not isinstance(results, list):
        raise TypeError("Provider response field 'results' must be a list.")

    return {
        "next": next_url,
        "previous": previous_url,
        "results": results,
    }


def validate_seats_response(payload: dict[str, Any]) -> list[str]:
    if not isinstance(payload, dict):
        raise TypeError("Provider response must be a JSON object.")

    seats = payload.get("seats")
    if not isinstance(seats, list) or any(not isinstance(seat, str) for seat in seats):
        raise TypeError("Provider response field 'seats' must be a list of strings.")

    return seats


def validate_ticket_response(payload: dict[str, Any]) -> str:
    if not isinstance(payload, dict):
        raise TypeError("Provider response must be a JSON object.")

    ticket_id = payload.get("ticket_id")
    if not isinstance(ticket_id, str) or not ticket_id:
        raise TypeError("Provider response field 'ticket_id' must be a non-empty string.")

    try:
        UUID(ticket_id)
    except (TypeError, ValueError) as error:
        raise TypeError(
            "Provider response field 'ticket_id' must be a valid UUID string."
        ) from error

    return ticket_id


def validate_success_response(payload: dict[str, Any]) -> bool:
    if not isinstance(payload, dict):
        raise TypeError("Provider response must be a JSON object.")

    success = payload.get("success")
    if not isinstance(success, bool):
        raise TypeError("Provider response field 'success' must be a boolean.")

    return success
