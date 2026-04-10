from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from events.exceptions import EventNotFound, EventUnpublished
from events.pagination import EventListPagination
from events.selectors import get_event_by_id, list_events
from events.serializers import (
    EventDetailSerializer,
    EventListQuerySerializer,
    EventListSerializer,
    EventSeatsSerializer,
)
from events.services import get_available_seats
from integrations.events_provider.exceptions import EventsProviderError


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


class EventSeatsAPIView(APIView):
    def get(self, request, event_id):
        try:
            available_seats = get_available_seats(event_id)
        except EventNotFound:
            raise NotFound(detail="Not found.")
        except EventUnpublished:
            return Response(
                {"detail": "Event is not published."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except EventsProviderError:
            return Response(
                {"detail": "Seats unavailable."},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        serializer = EventSeatsSerializer(
            {"event_id": event_id, "available_seats": available_seats}
        )
        return Response(serializer.data, status=status.HTTP_200_OK)
