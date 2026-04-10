from django.urls import path

from sync.views import SyncTriggerAPIView

urlpatterns = [
    path("sync/trigger", SyncTriggerAPIView.as_view(), name="sync-trigger"),
]
