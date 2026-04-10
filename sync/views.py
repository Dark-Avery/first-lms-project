from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from integrations.events_provider.client import EventsProviderClient
from integrations.events_provider.exceptions import EventsProviderError
from sync.services import SyncEventsService


class SyncTriggerAPIView(APIView):
    def post(self, request):
        service = self._build_service()

        try:
            service.run()
        except (EventsProviderError, ValueError):
            return Response({"detail": "Sync failed."}, status=status.HTTP_502_BAD_GATEWAY)

        return Response({"success": True}, status=status.HTTP_200_OK)

    def _build_service(self) -> SyncEventsService:
        return SyncEventsService(EventsProviderClient())
