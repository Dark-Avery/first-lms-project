from django.urls import path

from health.views import HealthCheckAPIView

urlpatterns = [
    path("health", HealthCheckAPIView.as_view(), name="health-check"),
]
