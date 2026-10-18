from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.order import Order, Ticket
from app.schemas.ticket import TicketCreate


async def get_ticket_details(
    db: AsyncSession,
    ticket_id: int,
) -> Ticket | None:
    query = (
        select(Ticket)
        .options(
            selectinload(Ticket.order).selectinload(Order.payment),
            selectinload(Ticket.order).selectinload(Order.shipment),
        )
        .where(Ticket.id == ticket_id)
    )

    result = await db.execute(query)

    return result.scalar_one_or_none()




async def get_ticket_by_id(
    db: AsyncSession,
    ticket_id: int,
) -> Ticket | None:
    return await db.get(Ticket, ticket_id)


async def list_tickets(
    db: AsyncSession,
    limit: int = 100,
) -> list[Ticket]:
    result = await db.execute(
        select(Ticket)
        .order_by(Ticket.id.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def create_ticket(
    db: AsyncSession,
    payload: TicketCreate,
) -> Ticket:
    ticket = Ticket(**payload.model_dump())

    db.add(ticket)
    await db.commit()
    await db.refresh(ticket)

    return ticket
