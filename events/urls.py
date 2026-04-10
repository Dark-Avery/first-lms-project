from django.urls import path

from events.views import EventDetailAPIView, EventListAPIView, EventSeatsAPIView

urlpatterns = [
    path("events", EventListAPIView.as_view(), name="event-list"),
    path("events/<uuid:event_id>", EventDetailAPIView.as_view(), name="event-detail"),
    path("events/<uuid:event_id>/seats", EventSeatsAPIView.as_view(), name="event-seats"),
]
