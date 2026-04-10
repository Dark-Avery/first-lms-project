from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from sync.tasks import run_sync_events


class SyncTriggerAPIView(APIView):
    def post(self, request):
        try:
            task = run_sync_events.delay()
        except Exception:
            return Response(
                {"detail": "Sync queue is unavailable."},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        return Response(
            {"status": "queued", "task_id": task.id},
            status=status.HTTP_200_OK,
        )
