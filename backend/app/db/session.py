# AsyncGenerator:
# Yeh ek type hint hai jo batata hai ki function asynchronous generator hai.
# Async generator 'yield' ki help se value provide karta hai
# aur execution ko temporarily pause kar deta hai.
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,          # Database queries aur transactions handle karne wala async session object.
    async_sessionmaker,   # Session Factory: Naye AsyncSession objects create karta hai.
    create_async_engine,  # Database engine aur connection pool create/configure karta hai.
)

# Settings object import kar rahe hain.
# Isme .env file se database URL jaise configuration values milti hain.
from app.core.config import settings


# ============================================================
# 1. DATABASE ENGINE
# ============================================================

# Engine database ke saath communication manage karta hai.
# Yeh connection pool maintain karta hai jisme DB connections
# zarurat ke according acquire aur reuse kiye ja sakte hain.
#
# Engine create hone par actual database connection
# immediately open hona zaroori nahi hai.
# Connection usually first database operation par acquire hota hai.

engine = create_async_engine(
    settings.database_url,
    # Database URL settings se milta hai.
    # Example: postgresql+asyncpg://user:password@localhost:5432/resolveops

    pool_pre_ping=True,
    # Connection pool se connection lene se pehle check karta hai
    # ki connection abhi alive hai ya disconnect ho chuka hai.
    # Invalid connection ko reconnect/replace karne mein help karta hai.

    echo=False,
    # True  -> SQL queries terminal/logs mein show hongi.
    # False -> SQL queries automatically log nahi hongi.
    # Debugging ke liye True useful ho sakta hai.
)


# ============================================================
# 2. SESSION FACTORY
# ============================================================

# Factory ka matlab: Objects banane wali cheez.
#
# AsyncSessionLocal ek session factory hai.
# Jab bhi AsyncSessionLocal() call karenge,
# ek naya independent AsyncSession object create hoga.
#
# Example:
# session1 = AsyncSessionLocal()
# session2 = AsyncSessionLocal()
#
# session1 aur session2 alag session objects hain.
# Lekin dono same engine aur connection pool use kar sakte hain.
#
# Important:
# Session object aur actual database connection same nahi hote.
# Session zarurat padne par engine se connection acquire karta hai.

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    # Session ko upar create kiye gaye engine ke saath bind karta hai.

    class_=AsyncSession,
    # Factory AsyncSession type ke objects create karegi.
    # AsyncSession async database operations support karta hai.

    expire_on_commit=False,
    # Commit ke baad ORM object ke loaded attributes
    # automatically expire nahi honge.
    #
    # Example:
    # ticket = Ticket(title="Login Error")
    # session.add(ticket)
    # await session.commit()
    # print(ticket.title)
    #
    # Loaded title ko dobara query kiye bina access kar sakte hain.
    # Lekin iska matlab data hamesha database se synchronized nahi hai.
)


# ============================================================
# 3. DATABASE DEPENDENCY
# ============================================================

# Yeh function FastAPI routes ko database session provide karta hai.
#
# async def:
# Asynchronous function define karta hai.
#
# AsyncGenerator[AsyncSession, None]:
# Type hint hai jo batata hai ki function AsyncSession yield karega.
# None generator ke send-value type ko represent karta hai.
#
# async with:
# Session ka lifecycle manage karta hai.
# Block exit hone par session automatically close hota hai.
#
# yield:
# Session FastAPI ko provide karta hai aur generator pause hota hai.
# Dependency cleanup ke time generator resume hota hai.

async def get_db() -> AsyncGenerator[AsyncSession, None]:

    # Step 1: Session Factory se naya session create karo.
    # 'async with' session ko safely manage karega.
    async with AsyncSessionLocal() as session:

        # Step 2: Session FastAPI route ko provide karo.
        # Generator yahan temporarily pause ho jayega.
        yield session

        # Step 3:
        # Route processing ke baad FastAPI dependency ko resume karega.
        # 'async with' block exit hone par session close ho jayega.
        #
        # Note:
        # Session close hone se automatic commit nahi hota.
        # Database changes save karne ke liye
        # await session.commit() explicitly karna hota hai.


# ============================================================
# 4. FASTAPI ROUTE MEIN USE KAISE KARENGE?
# ============================================================

# Example:
#
# from fastapi import Depends
#
# @router.get("/tickets")
# async def get_tickets(
#     db: AsyncSession = Depends(get_db)
# ):
#     # db -> Database session variable
#     # AsyncSession -> Type hint
#     # Depends(get_db) -> FastAPI dependency injection
#
#     # FastAPI automatically get_db() execute karega
#     # aur yielded session 'db' parameter mein provide karega.
#
#     result = await db.execute(select(Ticket))
#     return result.scalars().all()
#
#
# ============================================================
# COMPLETE EXECUTION FLOW
# ============================================================
#
# 1. Frontend -> GET /tickets request bhejta hai.
#
# 2. FastAPI -> Depends(get_db) dekhta hai.
#
# 3. get_db() -> AsyncSessionLocal() se session create karta hai.
#
# 4. yield session -> Session API route ko provide karta hai.
#
# 5. API route -> db.execute() se database query execute karta hai.
#
# 6. API route -> Result return karta hai.
#
# 7. FastAPI -> Dependency cleanup execute karta hai.
#
# 8. async with -> Session automatically close karta hai.
#
# Note: Default request-scoped yield dependency mein cleanup
# normally response send hone ke baad hota hai.
#
# IMPORTANT:
# Engine  -> Database connection infrastructure manage karta hai.
# Factory -> Naye session objects create karti hai.
# Session -> Database queries aur transactions handle karta hai.
# get_db  -> FastAPI routes ko session provide karta hai.
# yield   -> Session provide karke generator pause karta hai.
# async with -> Session cleanup automatically handle karta hai.
# ============================================================