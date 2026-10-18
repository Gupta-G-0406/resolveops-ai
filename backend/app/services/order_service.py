from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.order import Order


# Order ID se order fetch karo, payment aur shipment ke saath.
async def get_order_by_id(
    db: AsyncSession,
    order_id: int,
) -> Order | None:
    result = await db.execute(
        select(Order)
        .options(
            selectinload(Order.payment),
            selectinload(Order.shipment),
        )
        .where(Order.id == order_id)
    )
    return result.scalar_one_or_none()


# Latest orders fetch karo (default maximum 100).
async def list_orders(
    db: AsyncSession,
    limit: int = 100,
) -> list[Order]:
    result = await db.execute(
        select(Order)
        .options(
            selectinload(Order.payment),
            selectinload(Order.shipment),
        )
        .order_by(Order.id.desc())  # Latest IDs first
        .limit(limit)
    )
    return list(result.scalars().all())


# Order number se order fetch karo, payment aur shipment ke saath.
async def get_order_by_number(
    db: AsyncSession,
    order_number: str,
) -> Order | None:
    result = await db.execute(
        select(Order)
        .options(
            selectinload(Order.payment),
            selectinload(Order.shipment),
        )
        .where(Order.order_number == order_number)
    )
    return result.scalar_one_or_none()