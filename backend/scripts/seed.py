
import asyncio

from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models.order import Order, Payment, Shipment, Ticket


SCENARIOS = [
    {
        "order_number": "ORD-1001",
        "customer_name": "Demo Customer",
        "amount": 149900,
        "order_status": "delivered",
        "payment_status": "paid",
        "shipment_status": "delivered",
        "proof": False,
        "subject": "Delivered but not received",
        "description": (
            "My order shows delivered, but I have not "
            "received the package."
        ),
    },
    {
        "order_number": "ORD-1002",
        "customer_name": "Alex Morgan",
        "amount": 259900,
        "order_status": "placed",
        "payment_status": "paid",
        "shipment_status": "pending",
        "proof": False,
        "subject": "Possible duplicate payment",
        "description": (
            "I believe my payment was charged twice. "
            "Please investigate the transaction history."
        ),
    },
    {
        "order_number": "ORD-1003",
        "customer_name": "Sam Taylor",
        "amount": 89900,
        "order_status": "shipped",
        "payment_status": "paid",
        "shipment_status": "in_transit",
        "proof": False,
        "subject": "Shipment delayed",
        "description": (
            "My package has not arrived within the "
            "expected delivery window."
        ),
    },
    {
        "order_number": "ORD-1004",
        "customer_name": "Jordan Lee",
        "amount": 349900,
        "order_status": "cancelled",
        "payment_status": "paid",
        "shipment_status": "not_shipped",
        "proof": False,
        "subject": "Refund after cancellation",
        "description": (
            "My order was cancelled but I have not "
            "received a refund yet."
        ),
    },
]


async def seed_database():
    async with AsyncSessionLocal() as db:
        for scenario in SCENARIOS:
            result = await db.execute(
                select(Order).where(
                    Order.order_number == scenario["order_number"]
                )
            )

            order = result.scalar_one_or_none()

            if order is None:
                order = Order(
                    order_number=scenario["order_number"],
                    customer_name=scenario["customer_name"],
                    total_amount_paise=scenario["amount"],
                    status=scenario["order_status"],
                )
                db.add(order)
                await db.flush()

            payment = await db.scalar(
                select(Payment).where(Payment.order_id == order.id)
            )

            if payment is None:
                db.add(
                    Payment(
                        order_id=order.id,
                        status=scenario["payment_status"],
                        amount_paise=scenario["amount"],
                    )
                )

            shipment = await db.scalar(
                select(Shipment).where(Shipment.order_id == order.id)
            )

            if shipment is None:
                db.add(
                    Shipment(
                        order_id=order.id,
                        status=scenario["shipment_status"],
                        delivery_proof_available=scenario["proof"],
                    )
                )

            existing_ticket = await db.scalar(
                select(Ticket).where(
                    Ticket.order_id == order.id,
                    Ticket.subject == scenario["subject"],
                )
            )

            if existing_ticket is None:
                db.add(
                    Ticket(
                        order_id=order.id,
                        subject=scenario["subject"],
                        description=scenario["description"],
                        status="open",
                    )
                )

        await db.commit()
        print("Seed scenarios created successfully.")


if __name__ == "__main__":
    asyncio.run(seed_database())
