from django.db import models


class SyncState(models.Model):
    class Status(models.TextChoices):
        IDLE = "idle", "Idle"
        RUNNING = "running", "Running"
        FAILED = "failed", "Failed"
        SUCCESS = "success", "Success"

    id = models.PositiveSmallIntegerField(primary_key=True, default=1, editable=False)
    last_sync_time = models.DateTimeField(null=True, blank=True)
    last_changed_at = models.DateTimeField(null=True, blank=True)
    sync_status = models.CharField(max_length=32, choices=Status.choices, default=Status.IDLE)
    last_error = models.TextField(blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        self.id = 1
        if self._state.adding and SyncState.objects.filter(pk=1).exists():
            self._state.adding = False
        return super().save(*args, **kwargs)


class SyncRun(models.Model):
    class Status(models.TextChoices):
        RUNNING = "running", "Running"
        FAILED = "failed", "Failed"
        SUCCESS = "success", "Success"

    started_at = models.DateTimeField()
    finished_at = models.DateTimeField(null=True, blank=True)
    sync_status = models.CharField(max_length=32, choices=Status.choices, default=Status.RUNNING)
    last_changed_at = models.DateTimeField(null=True, blank=True)
    last_error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-started_at", "-id")
