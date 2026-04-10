from __future__ import annotations

from unittest.mock import Mock, patch

import pytest

from integrations.events_provider.exceptions import ProviderBadResponseError
from sync.tasks import run_sync_events


def test_run_sync_events_task_delegates_to_service():
    sync_run = Mock(id=7, sync_status="success")

    with patch("sync.tasks.EventsProviderClient") as client_cls:
        with patch("sync.tasks.SyncEventsService") as service_cls:
            service_cls.return_value.run.return_value = sync_run

            result = run_sync_events()

    client_cls.assert_called_once_with()
    service_cls.assert_called_once_with(client_cls.return_value)
    service_cls.return_value.run.assert_called_once_with()
    assert result == {
        "sync_run_id": 7,
        "sync_status": "success",
    }


def test_run_sync_events_task_propagates_service_errors():
    with patch("sync.tasks.EventsProviderClient"):
        with patch("sync.tasks.SyncEventsService") as service_cls:
            service_cls.return_value.run.side_effect = ProviderBadResponseError("html")

            with pytest.raises(ProviderBadResponseError):
                run_sync_events()
