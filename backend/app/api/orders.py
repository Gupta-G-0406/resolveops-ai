from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.order import OrderResponse
from app.services import order_service


# Orders ke sabhi API endpoints ka common prefix.
router = APIRouter(
    prefix="/api/orders",
    tags=["Orders"],
)


# Saare orders fetch karo (OrderResponse ki list return hogi).
@router.get("", response_model=list[OrderResponse])
async def list_orders(
    db: AsyncSession = Depends(get_db),
):
    return await order_service.list_orders(db)


# Order ID se single order fetch karo.
@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: int,
    db: AsyncSession = Depends(get_db),
):
    # Database logic Service Layer mein hai.
    order = await order_service.get_order_by_id(db, order_id)

    # Order nahi mila toh 404 error.
    if order is None:
        raise HTTPException(
            status_code=404,
            detail="Order not found",
        )

    return order