# ============================================================
# PYDANTIC RESPONSE SCHEMAS - RESOLVEOPS
# ============================================================

# BaseModel:
# Pydantic ki parent class hai.
# Isse inherit karke hum API data ka structure define karte hain.
# Yeh data validation aur serialization mein help karta hai.
#
# ConfigDict:
# Pydantic model ki configuration define karne ke liye use hota hai.

from pydantic import BaseModel, ConfigDict


# ============================================================
# 1. PAYMENT RESPONSE SCHEMA
# ============================================================

# PaymentResponse define karta hai ki API response mein
# payment ka data kis format mein return hoga.

class PaymentResponse(BaseModel):

    # from_attributes=True:
    # Pydantic ko SQLAlchemy ORM object ke attributes
    # read karne ki permission deta hai.
    #
    # Example:
    # payment.id
    # payment.status
    # payment.amount_paise
    #
    # In attributes ko read karke Pydantic model ban sakta hai.

    model_config = ConfigDict(from_attributes=True)

    # Payment ki unique ID.
    # int -> Integer value required.
    id: int

    # Payment ka current status.
    # Example: pending, paid, failed, refunded.
    # str -> String value.
    status: str

    # Payment amount paise mein store hota hai.
    # int -> Integer.
    #
    # Example:
    # 10000 paise = 100 rupees
    # 150000 paise = 1500 rupees
    amount_paise: int


# ============================================================
# 2. SHIPMENT RESPONSE SCHEMA
# ============================================================

# ShipmentResponse define karta hai ki API response mein
# delivery/shipment ka data kaisa hoga.

class ShipmentResponse(BaseModel):

    # SQLAlchemy Shipment object ke attributes read karne
    # ke liye configuration.
    model_config = ConfigDict(from_attributes=True)

    # Shipment ki unique ID.
    id: int

    # Shipment ka current status.
    # Example: pending, shipped, in_transit, delivered.
    status: str

    # Delivery proof available hai ya nahi.
    #
    # bool -> Boolean (True/False).
    #
    # True  -> Delivery proof available hai.
    # False -> Delivery proof available nahi hai.
    #
    # JSON response mein true/false aayega.
    delivery_proof_available: bool


# ============================================================
# 3. ORDER RESPONSE SCHEMA
# ============================================================

# OrderResponse main response schema hai.
#
# Isme Order ki information ke saath
# Payment aur Shipment ke nested objects bhi ho sakte hain.

class OrderResponse(BaseModel):

    # SQLAlchemy ORM object se attributes read karne ke liye.
    model_config = ConfigDict(from_attributes=True)

    # Order ki unique database ID.
    id: int

    # Order ka unique number.
    # Example: ORD-1001
    order_number: str

    # Customer ka naam.
    # Example: Rahul Sharma
    customer_name: str

    # Order ki total amount paise mein.
    #
    # Example:
    # 250000 paise = 2500 rupees
    total_amount_paise: int

    # Order ka current status.
    # Example: created, confirmed, completed, cancelled.
    status: str


    # ========================================================
    # 4. NESTED PAYMENT RELATIONSHIP
    # ========================================================

    # payment:
    # Order ke andar payment ka data represent karta hai.
    #
    # PaymentResponse:
    # Agar payment available hai toh PaymentResponse
    # schema ke according data validate hoga.
    #
    # | None:
    # Payment missing hone par None allowed hai.
    #
    # = None:
    # Agar payment field provide nahi ki gayi
    # toh default None hoga.
    #
    # JSON mein None -> null ban jayega.

    payment: PaymentResponse | None = None


    # ========================================================
    # 5. NESTED SHIPMENT RELATIONSHIP
    # ========================================================

    # shipment:
    # Order ke andar shipment ka data represent karta hai.
    #
    # ShipmentResponse:
    # Shipment available hone par nested object validate hoga.
    #
    # | None:
    # Shipment absent ho sakta hai.
    #
    # = None:
    # Default None hai.
    #
    # Shipment absent hone par JSON mein null aayega.

    shipment: ShipmentResponse | None = None