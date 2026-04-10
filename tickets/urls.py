from django.urls import path

from tickets.views import TicketCreateAPIView

urlpatterns = [
    path("tickets", TicketCreateAPIView.as_view(), name="ticket-create"),
]
