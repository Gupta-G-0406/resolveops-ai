from sqlalchemy import BigInteger, ForeignKey, String, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


# ============================================================
# 1. ORDER MODEL - Main customer orders table
# ============================================================

class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Unique order number, indexed for faster lookup.
    order_number: Mapped[str] = mapped_column(
        String(50), unique=True, index=True
    )

    customer_name: Mapped[str] = mapped_column(String(150))

    # Amount paise mein store hota hai to avoid floating-point errors.
    total_amount_paise: Mapped[int] = mapped_column(BigInteger)

    status: Mapped[str] = mapped_column(
        String(30), default="placed"
    )

    # One Order -> Maximum one Payment.
    payment: Mapped["Payment | None"] = relationship(
        back_populates="order",
        uselist=False
    )

    # One Order -> Maximum one Shipment.
    shipment: Mapped["Shipment | None"] = relationship(
        back_populates="order",
        uselist=False
    )

    # One Order -> Multiple Tickets.
    tickets: Mapped[list["Ticket"]] = relationship(
        back_populates="order"
    )


# ============================================================
# 2. PAYMENT MODEL - Order payment information
# ============================================================

class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Foreign key + unique constraint enforce one-to-one relation.
    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id"),
        unique=True
    )

    status: Mapped[str] = mapped_column(String(30))
    amount_paise: Mapped[int] = mapped_column(BigInteger)

    # Reverse relationship: Payment -> Order.
    order: Mapped["Order"] = relationship(
        back_populates="payment"
    )


# ============================================================
# 3. SHIPMENT MODEL - Delivery tracking information
# ============================================================

class Shipment(Base):
    __tablename__ = "shipments"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Each Order can have maximum one Shipment record.
    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id"),
        unique=True
    )

    status: Mapped[str] = mapped_column(String(30))

    # True = Proof available, False = Not available.
    delivery_proof_available: Mapped[bool] = mapped_column(
        Boolean,
        default=False
    )

    # Reverse relationship: Shipment -> Order.
    order: Mapped["Order"] = relationship(
        back_populates="shipment"
    )


# ============================================================
# 4. TICKET MODEL - Customer support tickets
# ============================================================

class Ticket(Base):
    __tablename__ = "tickets"

    id: Mapped[int] = mapped_column(primary_key=True)

    # No unique constraint: Multiple tickets per Order allowed.
    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id")
    )

    subject: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)

    # New tickets start with "open" status.
    status: Mapped[str] = mapped_column(
        String(30),
        default="open"
    )

    # Reverse relationship: Ticket -> Order.
    order: Mapped["Order"] = relationship(
        back_populates="tickets"
    )