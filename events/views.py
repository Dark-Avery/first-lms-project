from rest_framework.exceptions import NotFound
from rest_framework.generics import ListAPIView, RetrieveAPIView

from events.pagination import EventListPagination
from events.selectors import get_event_by_id, list_events
from events.serializers import (
    EventDetailSerializer,
    EventListQuerySerializer,
    EventListSerializer,
)


class EventListAPIView(ListAPIView):
    serializer_class = EventListSerializer
    pagination_class = EventListPagination

    def get_queryset(self):
        query_serializer = EventListQuerySerializer(data=self.request.query_params)
        query_serializer.is_valid(raise_exception=True)
        return list_events(date_from=query_serializer.validated_data.get("date_from"))


class EventDetailAPIView(RetrieveAPIView):
    serializer_class = EventDetailSerializer

    def get_object(self):
        event = get_event_by_id(event_id=self.kwargs["event_id"])
        if event is None:
            raise NotFound(detail="Not found.")
        return event
