from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.ticket import (
    TicketCreate,
    TicketResponse,
    TicketDetailResponse,
)
from app.services import order_service, ticket_service


# Tickets ke sabhi API endpoints ka common prefix.
router = APIRouter(
    prefix="/api/tickets",
    tags=["Tickets"],
)


# Naya ticket create karo (201 Created).
@router.post(
    "",
    response_model=TicketResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_ticket(
    payload: TicketCreate,
    db: AsyncSession = Depends(get_db),
):
    # Ticket create karne se pehle Order exist karta hai ya nahi check karo.
    order = await order_service.get_order_by_id(
        db, payload.order_id
    )

    if order is None:
        raise HTTPException(
            status_code=404,
            detail="Order not found",
        )

    # Ticket creation logic Service Layer mein handle hoga.
    return await ticket_service.create_ticket(db, payload)


# Latest tickets fetch karo.
@router.get("", response_model=list[TicketResponse])
async def list_tickets(
    db: AsyncSession = Depends(get_db),
):
    return await ticket_service.list_tickets(db)


# Ticket ID se complete details (Order, Payment, Shipment) fetch karo.
@router.get(
    "/{ticket_id}",
    response_model=TicketDetailResponse,
)
async def get_ticket(
    ticket_id: int,
    db: AsyncSession = Depends(get_db),
):
    ticket = await ticket_service.get_ticket_details(
        db, ticket_id
    )

    if ticket is None:
        raise HTTPException(
            status_code=404,
            detail="Ticket not found",
        )

    return ticket