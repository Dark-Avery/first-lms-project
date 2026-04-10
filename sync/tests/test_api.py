from unittest.mock import Mock, patch

import pytest
from rest_framework.test import APIClient

from integrations.events_provider.exceptions import ProviderTemporaryError


@pytest.mark.django_db
def test_sync_trigger_returns_success_and_calls_service():
    client = APIClient()
    service = Mock()

    with patch("sync.views.SyncEventsService", return_value=service) as service_cls:
        response = client.post("/api/sync/trigger")

    assert response.status_code == 200
    assert response.json() == {"success": True}
    service_cls.assert_called_once()
    service.run.assert_called_once_with()


@pytest.mark.django_db
def test_sync_trigger_returns_json_error_when_service_fails():
    client = APIClient()
    service = Mock()
    service.run.side_effect = ProviderTemporaryError("provider unavailable")

    with patch("sync.views.SyncEventsService", return_value=service):
        response = client.post("/api/sync/trigger")

    assert response.status_code == 502
    assert response.json() == {"detail": "Sync failed."}
