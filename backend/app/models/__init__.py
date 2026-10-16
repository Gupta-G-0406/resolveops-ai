# Andar ki file (order.py) se saare models ko bahar (is file mein) laa rahe hain.
# Iska fayda yeh hai ki baaki project ko andar ki files ka rasta yaad rakhne ki zaroorat nahi.
from app.models.order import Order, Payment, Shipment, Ticket

# __all__ Python ka ek special variable hai.
# Yeh batata hai ki agar koi dusri file se 'from app.models import *' likhe, 
# toh use sirf ye 4 cheezein hi milengi, koi faltu background kachra (clutter) nahi.
__all__ = ["Order", "Payment", "Shipment", "Ticket"]