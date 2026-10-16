from sqlalchemy.orm import DeclarativeBase

# Yeh humari sabhi database tables (models) ka foundation (parent class) hai.
# Aage chalkar Ticket, User jaisi saari classes isi 'Base' ko inherit karengi,
# jisse SQLAlchemy ko pata chalega ki inki tables database mein banani hain.
class Base(DeclarativeBase):
    pass