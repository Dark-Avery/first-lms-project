from unittest.mock import Mock, patch

import pytest
from rest_framework.test import APIClient


@pytest.mark.django_db
def test_sync_trigger_returns_queued_response_and_enqueues_task():
    client = APIClient()
    task = Mock(id="task-123")

    with patch("sync.views.run_sync_events.delay", return_value=task) as delay_mock:
        response = client.post("/api/sync/trigger")

    assert response.status_code == 200
    assert response.json() == {"status": "queued", "task_id": "task-123"}
    delay_mock.assert_called_once_with()


@pytest.mark.django_db
def test_sync_trigger_returns_json_error_when_queue_is_unavailable():
    client = APIClient()

    with patch("sync.views.run_sync_events.delay", side_effect=RuntimeError("queue down")):
        response = client.post("/api/sync/trigger")

    assert response.status_code == 502
    assert response.json() == {"detail": "Sync queue is unavailable."}
