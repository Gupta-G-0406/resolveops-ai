from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings

# 1. Engine: Yeh actual connection pool banata hai database ke sath.
engine = create_async_engine(
    settings.database_url, # .env se URL le raha hai (e.g., postgresql+asyncpg://...)
    pool_pre_ping=True,    # Connection use karne se pehle check karta hai ki DB zinda hai ya disconnect ho gaya
    echo=False,            # True karne par terminal mein saari SQL queries print hoti hain (debugging ke liye)
)

# 2. Session Factory: Har API request ke liye ek naya database session (connection window) banati hai.
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False, # Commit hone ke baad object ka data memory mein barkarar rakhta hai
)

# 3. DB Dependency: Yeh function FastAPI routes mein use hoga.
# Jab bhi API hit hogi, yeh DB session open karega aur kaam khatam hone par automatically close kar dega.
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session # API ko session de do. Kaam khatam hone par 'async with' ise khud close kar dega.