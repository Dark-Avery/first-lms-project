from django.db import models


class Ticket(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        CANCELLED = "cancelled", "Cancelled"

    ticket_id = models.UUIDField(db_index=True)
    event = models.ForeignKey("events.Event", on_delete=models.PROTECT, related_name="tickets")
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)
    email = models.EmailField()
    seat = models.CharField(max_length=32)
    status = models.CharField(max_length=32, choices=Status.choices, default=Status.ACTIVE)
    created_at = models.DateTimeField(auto_now_add=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-created_at", "-id")
