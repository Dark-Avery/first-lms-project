from rest_framework.generics import ListAPIView

from events.pagination import EventListPagination
from events.selectors import list_events
from events.serializers import EventListQuerySerializer, EventListSerializer


class EventListAPIView(ListAPIView):
    serializer_class = EventListSerializer
    pagination_class = EventListPagination

    def get_queryset(self):
        query_serializer = EventListQuerySerializer(data=self.request.query_params)
        query_serializer.is_valid(raise_exception=True)
        return list_events(date_from=query_serializer.validated_data.get("date_from"))
