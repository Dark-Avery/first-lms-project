from django.db import models


class Place(models.Model):
    id = models.UUIDField(primary_key=True)
    name = models.CharField(max_length=255)
    city = models.CharField(max_length=255)
    address = models.CharField(max_length=255)
    seats_pattern = models.CharField(max_length=255)
    created_at = models.DateTimeField()
    changed_at = models.DateTimeField()

    class Meta:
        ordering = ("name", "id")


class Event(models.Model):
    class Status(models.TextChoices):
        NEW = "new", "New"
        PUBLISHED = "published", "Published"

    id = models.UUIDField(primary_key=True)
    place = models.ForeignKey(Place, on_delete=models.PROTECT, related_name="events")
    name = models.CharField(max_length=255)
    event_time = models.DateTimeField(db_index=True)
    registration_deadline = models.DateTimeField()
    status = models.CharField(max_length=64, choices=Status.choices, db_index=True)
    number_of_visitors = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField()
    changed_at = models.DateTimeField(db_index=True)
    status_changed_at = models.DateTimeField()

    class Meta:
        ordering = ("event_time", "id")
