
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.order import Order, Ticket
from app.schemas.ticket import TicketCreate, TicketResponse


router = APIRouter(prefix="/api/tickets", tags=["Tickets"])


@router.post("", response_model=TicketResponse, status_code=status.HTTP_201_CREATED)
async def create_ticket(payload: TicketCreate, db: AsyncSession = Depends(get_db)):
    # Step 1: Check karo ki jis Order par ticket ban raha hai, wo order database me hai ya nahi
    order = await db.get(Order, payload.order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")

    # Step 2: Payload (Pydantic) data ko dict me convert karke SQLAlchemy Ticket object banao
    ticket = Ticket(**payload.model_dump())
    db.add(ticket) # Database session me add karo

    # Step 3: Asliyat me database me save karo (commit) aur nayi ID fetch karo (refresh)
    await db.commit()
    await db.refresh(ticket)
    return ticket

@router.get("", response_model=list[TicketResponse])
async def list_tickets(db: AsyncSession = Depends(get_db)):
    # Database se latest 100 tickets uthao (descending order by ID)
    result = await db.execute(
        select(Ticket).order_by(Ticket.id.desc()).limit(100)
    )
    # result.scalars().all() list format me data wapas karta hai
    return result.scalars().all()


@router.get("/{ticket_id}", response_model=TicketResponse)
async def get_ticket(ticket_id: int, db: AsyncSession = Depends(get_db)):
    # Database se sirf wo ek ticket fetch karo
    ticket = await db.get(Ticket, ticket_id)

    # Agar ticket nahi mila, to 404 Error do
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")

    return ticket
