from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.views import APIView

from events.exceptions import EventNotFound, EventUnpublished
from integrations.events_provider.client import EventsProviderClient
from integrations.events_provider.exceptions import EventsProviderError
from tickets.exceptions import RegistrationClosed, TicketSeatInvalid, TicketSeatUnavailable
from tickets.serializers import TicketCreateRequestSerializer, TicketCreateResponseSerializer
from tickets.usecases import CreateTicketUseCase


class TicketCreateAPIView(APIView):
    def post(self, request):
        request_serializer = TicketCreateRequestSerializer(data=request.data)
        request_serializer.is_valid(raise_exception=True)

        try:
            ticket_id = self._build_use_case().execute(
                **request_serializer.validated_data
            )
        except EventNotFound:
            raise NotFound(detail="Not found.")
        except EventUnpublished:
            return Response(
                {"detail": "Event is not published."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except RegistrationClosed:
            return Response(
                {"detail": "Registration is closed."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except TicketSeatInvalid:
            return Response(
                {"detail": "Seat is invalid."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except TicketSeatUnavailable:
            return Response(
                {"detail": "Seat is unavailable."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except EventsProviderError:
            return Response(
                {"detail": "Registration unavailable."},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        response_serializer = TicketCreateResponseSerializer({"ticket_id": ticket_id})
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    def _build_use_case(self) -> CreateTicketUseCase:
        return CreateTicketUseCase(EventsProviderClient())
