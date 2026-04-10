from __future__ import annotations

from uuid import UUID

from tickets.models import Ticket


def get_active_ticket_by_provider_ticket_id(*, ticket_id: UUID) -> Ticket | None:
    return (
        Ticket.objects.select_related("event")
        .filter(ticket_id=ticket_id, status=Ticket.Status.ACTIVE)
        .order_by("-created_at", "-id")
        .first()
    )


def has_cancelled_ticket_with_provider_ticket_id(*, ticket_id: UUID) -> bool:
    return Ticket.objects.filter(
        ticket_id=ticket_id,
        status=Ticket.Status.CANCELLED,
    ).exists()
