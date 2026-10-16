from sqlalchemy import BigInteger, ForeignKey, String, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


# Order Table: Customer ke orders save karne ke liye main table
class Order(Base):
    __tablename__ = "orders"

    # Primary Key (Unique ID har order ke liye)
    id: Mapped[int] = mapped_column(primary_key=True)
    
    # Order number unique hona chahiye aur index=True se search fast hoti hai
    order_number: Mapped[str] = mapped_column(
        String(50), unique=True, index=True
    )
    customer_name: Mapped[str] = mapped_column(String(150))
    
    # Amount hamesha paise (smallest unit) mein save karte hain to avoid calculation errors
    total_amount_paise: Mapped[int] = mapped_column(BigInteger)
    
    # Default status 'placed' set kiya hai
    status: Mapped[str] = mapped_column(String(30), default="placed")

    # --- Relationships ---
    # uselist=False ka matlab hai 1 Order ki sirf 1 hi Payment record hogi (One-to-One)
    payment: Mapped["Payment | None"] = relationship(
        back_populates="order", uselist=False
    )
    # 1 Order ki sirf 1 hi Shipment record hogi (One-to-One)
    shipment: Mapped["Shipment | None"] = relationship(
        back_populates="order", uselist=False
    )
    # 1 Order par multiple Tickets (complaints) ho sakti hain, isliye yahan list (One-to-Many) hai
    tickets: Mapped[list["Ticket"]] = relationship(
        back_populates="order"
    )


# Payment Table: Order ki payment information ke liye
class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True)
    
    # ForeignKey bata raha hai ki ye kis order ki payment hai.
    # unique=True lagaya hai kyunki ek order ki duplicate payment entry nahi honi chahiye (1-to-1).
    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id"), unique=True
    )
    status: Mapped[str] = mapped_column(String(30))
    amount_paise: Mapped[int] = mapped_column(BigInteger)

    # Order table ke sath reverse connection
    order: Mapped["Order"] = relationship(back_populates="payment")


# Shipment Table: Order delivery/tracking data ke liye
class Shipment(Base):
    __tablename__ = "shipments"

    id: Mapped[int] = mapped_column(primary_key=True)
    
    # Yahan bhi unique=True hai, taaki ek order ki ek hi active shipment ho (1-to-1)
    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id"), unique=True
    )
    status: Mapped[str] = mapped_column(String(30))
    
    # Boolean data type True (Haan) ya False (Naa) save karta hai
    delivery_proof_available: Mapped[bool] = mapped_column(
        Boolean, default=False
    )

    # Order table ke sath reverse connection
    order: Mapped["Order"] = relationship(back_populates="shipment")


# Ticket Table: Customer support queries/complaints ke liye
class Ticket(Base):
    __tablename__ = "tickets"

    id: Mapped[int] = mapped_column(primary_key=True)
    
    # Yahan unique=True NAHI lagaya hai! 
    # Matlab ek hi order_id par 2 ya 3 alag-alag support tickets ban sakti hain (1-to-Many).
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"))
    subject: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    
    # Nayi ticket humesha 'open' status ke sath start hogi
    status: Mapped[str] = mapped_column(
        String(30), default="open"
    )

    # Order table ke sath reverse connection
    order: Mapped["Order"] = relationship(back_populates="tickets")