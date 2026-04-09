import pytest
from django.utils import timezone

from sync.models import SyncRun, SyncState


@pytest.mark.django_db
def test_sync_state_behaves_as_singleton_row():
    first = SyncState.objects.create()
    second = SyncState(sync_status=SyncState.Status.RUNNING)
    second.save()

    assert first.id == 1
    assert second.id == 1
    assert SyncState.objects.count() == 1
    assert SyncState.objects.get().sync_status == SyncState.Status.RUNNING


@pytest.mark.django_db
def test_sync_run_creates_append_only_history_rows():
    first = SyncRun.objects.create(started_at=timezone.now())
    second = SyncRun.objects.create(started_at=timezone.now())

    assert first.pk != second.pk
    assert SyncRun.objects.count() == 2
