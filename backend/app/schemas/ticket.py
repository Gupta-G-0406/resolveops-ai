# ============================================================
# PYDANTIC TICKET SCHEMAS - RESOLVEOPS
# ============================================================

# BaseModel:
# Pydantic ki parent class hai.
# API request aur response data validate karne ke liye use hoti hai.
#
# ConfigDict:
# Pydantic model ki configuration define karta hai.
#
# Field:
# Kisi field par validation rules lagane ke liye use hota hai.
# Example: minimum value, minimum length, maximum length.

from pydantic import BaseModel, ConfigDict, Field

# OrderResponse ko import kar rahe hain.
# TicketDetailResponse mein order ka nested data show karne ke liye.
from app.schemas.order import OrderResponse


# ============================================================
# 1. TICKET CREATE SCHEMA
# ============================================================

# Jab frontend POST /tickets API call karega,
# tab request body ko TicketCreate schema validate karega.

class TicketCreate(BaseModel):

    # order_id:
    # Ticket kis order ke liye create ho raha hai.
    #
    # int -> Integer required.
    #
    # Field(gt=0):
    # gt = Greater Than
    # order_id ki value 0 se badi honi chahiye.
    #
    # Valid: 1, 2, 100
    # Invalid: 0, -1, -5
    order_id: int = Field(gt=0)

    # subject:
    # Ticket ka title ya short issue summary.
    #
    # str -> String value.
    #
    # min_length=3:
    # Minimum 3 characters hone chahiye.
    #
    # max_length=200:
    # Maximum 200 characters allowed hain.
    #
    # Valid: "Payment failed"
    # Invalid: "Hi" (sirf 2 characters)
    subject: str = Field(
        min_length=3,
        max_length=200
    )

    # description:
    # Customer ki problem ka detailed explanation.
    #
    # min_length=10:
    # Minimum 10 characters hone chahiye.
    #
    # Example:
    # "Payment deducted but order not confirmed"
    description: str = Field(min_length=10)


# ============================================================
# 2. TICKET RESPONSE SCHEMA
# ============================================================

# Jab API ticket ka data return karegi,
# tab response TicketResponse ke structure mein hoga.
#
# Example:
# GET /tickets
# POST /tickets

class TicketResponse(BaseModel):

    # SQLAlchemy ORM object ke attributes read karne ke liye.
    #
    # Example:
    # ticket.id
    # ticket.order_id
    # ticket.subject
    model_config = ConfigDict(from_attributes=True)

    # Ticket ki unique database ID.
    id: int

    # Ticket kis order se related hai.
    order_id: int

    # Ticket ka subject.
    subject: str

    # Ticket ki detailed description.
    description: str

    # Ticket ka current status.
    #
    # Example:
    # open, in_progress, resolved, closed
    status: str


# ============================================================
# 3. TICKET DETAIL RESPONSE SCHEMA
# ============================================================

# TicketDetailResponse, TicketResponse ko inherit karta hai.
#
# Iska matlab TicketResponse ke saare fields
# automatically TicketDetailResponse mein available honge.
#
# Extra field:
# order -> OrderResponse
#
# Isse ticket ke saath uske related order ka data bhi milega.

class TicketDetailResponse(TicketResponse):

    # OrderResponse ek nested Pydantic schema hai.
    #
    # Ismein order ki details hongi:
    # id
    # order_number
    # customer_name
    # total_amount_paise
    # status
    # payment
    # shipment
    #
    # Yahan order required hai.
    # Agar order missing ya None hua,
    # toh response validation error aa sakta hai.
    order: OrderResponse