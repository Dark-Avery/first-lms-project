from __future__ import annotations

from typing import Any

import requests
from django.conf import settings

from integrations.events_provider.exceptions import (
    ProviderAuthError,
    ProviderBadResponseError,
    ProviderBusinessError,
    ProviderNotFoundError,
    ProviderRateLimitError,
    ProviderTemporaryError,
)
from integrations.events_provider.schemas import (
    validate_events_page,
    validate_seats_response,
    validate_success_response,
    validate_ticket_response,
)


class EventsProviderClient:
    def __init__(
        self,
        *,
        base_url: str | None = None,
        api_key: str | None = None,
        timeout: int | None = None,
        session: requests.Session | None = None,
    ) -> None:
        self.base_url = (base_url or settings.EVENTS_PROVIDER_BASE_URL).rstrip("/")
        self.api_key = api_key if api_key is not None else settings.EVENTS_PROVIDER_API_KEY
        self.timeout = timeout if timeout is not None else settings.PROVIDER_TIMEOUT_SECONDS
        self.session = session or requests.Session()

    def events(self, *, changed_at: str, page_url: str | None = None) -> dict[str, Any]:
        url = page_url or self._build_url("/api/events/")
        response = self._request(
            "GET",
            url,
            params=None if page_url else {"changed_at": changed_at},
        )
        try:
            payload = response.json()
            return validate_events_page(payload)
        except (ValueError, TypeError) as error:
            raise ProviderBadResponseError(
                "Provider returned an invalid events response."
            ) from error

    def seats(self, event_id: str) -> list[str]:
        response = self._request("GET", self._build_url(f"/api/events/{event_id}/seats/"))
        try:
            payload = response.json()
            return validate_seats_response(payload)
        except (ValueError, TypeError) as error:
            raise ProviderBadResponseError(
                "Provider returned an invalid seats response."
            ) from error

    def register(
        self,
        event_id: str,
        *,
        first_name: str,
        last_name: str,
        email: str,
        seat: str,
    ) -> str:
        response = self._request(
            "POST",
            self._build_url(f"/api/events/{event_id}/register/"),
            json={
                "first_name": first_name,
                "last_name": last_name,
                "email": email,
                "seat": seat,
            },
        )
        try:
            payload = response.json()
            return validate_ticket_response(payload)
        except (ValueError, TypeError) as error:
            raise ProviderBadResponseError(
                "Provider returned an invalid register response."
            ) from error

    def unregister(self, event_id: str, *, ticket_id: str) -> bool:
        response = self._request(
            "DELETE",
            self._build_url(f"/api/events/{event_id}/unregister/"),
            json={"ticket_id": ticket_id},
        )
        try:
            payload = response.json()
            return validate_success_response(payload)
        except (ValueError, TypeError) as error:
            raise ProviderBadResponseError(
                "Provider returned an invalid unregister response."
            ) from error

    def _build_url(self, path: str) -> str:
        return f"{self.base_url}/{path.lstrip('/')}"

    def _request(self, method: str, url: str, **kwargs: Any) -> requests.Response:
        request_kwargs = {
            "headers": {"x-api-key": self.api_key},
            "timeout": self.timeout,
            **kwargs,
        }

        if "params" not in request_kwargs:
            request_kwargs["params"] = None

        try:
            response = self.session.request(method, url, **request_kwargs)
        except requests.RequestException as error:
            raise ProviderTemporaryError("Provider request failed.") from error

        self._raise_for_status(response)
        return response

    def _raise_for_status(self, response: requests.Response) -> None:
        status_code = response.status_code
        content_type = response.headers.get("Content-Type", "")

        if 200 <= status_code < 300:
            return

        if status_code == 401:
            raise ProviderAuthError("Provider authentication failed.")
        if status_code == 404:
            raise ProviderNotFoundError("Provider resource was not found.")
        if status_code == 429:
            raise ProviderRateLimitError("Provider rate limit exceeded.")
        if status_code >= 500:
            if "text/html" in content_type.lower():
                raise ProviderBadResponseError("Provider returned an HTML error response.")
            raise ProviderTemporaryError("Provider returned a server error.")
        if status_code == 400:
            message = self._extract_business_error(response)
            raise ProviderBusinessError(message)

        raise ProviderBadResponseError(f"Unexpected provider status code: {status_code}.")

    def _extract_business_error(self, response: requests.Response) -> str:
        try:
            payload = response.json()
        except ValueError as error:
            raise ProviderBadResponseError(
                "Provider returned a non-JSON business error."
            ) from error

        if isinstance(payload, list):
            return "; ".join(str(item) for item in payload)
        if isinstance(payload, dict):
            if "detail" in payload:
                return str(payload["detail"])
            return "; ".join(f"{key}: {value}" for key, value in payload.items())

        raise ProviderBadResponseError("Provider returned an unsupported business error format.")
