from django.urls import path

from tickets.views import TicketCancelAPIView, TicketCreateAPIView

urlpatterns = [
    path("tickets", TicketCreateAPIView.as_view(), name="ticket-create"),
    path("tickets/<uuid:ticket_id>", TicketCancelAPIView.as_view(), name="ticket-cancel"),
]
