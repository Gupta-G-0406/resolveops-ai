import asyncio
from uuid import uuid4

import httpx
import pytest
from sqlalchemy import delete, select
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import (
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings
from app.core.security import hash_password
from app.db.session import get_db
from app.main import app
from app.models.login_attempt import LoginAttempt
from app.models.user import User
from app.services.login_rate_limit_service import get_login_keys


TEST_DB_NAME = "resolveops_test_db"
ORIGIN = "http://localhost:5173"
PASSWORD = "StrongTestPassword123!"


@pytest.mark.asyncio
async def test_concurrent_logins_respect_account_limit():
    # Safety: never use development/production database.
    source_url = make_url(settings.database_url)

    if source_url.host not in ("localhost", "127.0.0.1"):
        raise RuntimeError(
            "Concurrency tests require local PostgreSQL"
        )

    test_url = source_url.set(database=TEST_DB_NAME)

    engine = create_async_engine(
        test_url,
        pool_size=15,
        max_overflow=5,
        pool_timeout=20,
    )

    session_factory = async_sessionmaker(
        engine,
        expire_on_commit=False,
    )

    email = f"concurrent-{uuid4().hex}@example.com"
    user_id = None

    # Existing dependency overrides must not interfere.
    if get_db in app.dependency_overrides:
        await engine.dispose()
        raise RuntimeError(
            "Database dependency override already active"
        )

    async def override_get_db():
        async with session_factory() as db:
            yield db

    try:
        # Create user in the isolated test database.
        async with session_factory() as db:
            user = User(
                email=email,
                full_name="Concurrency Test User",
                password_hash=hash_password(PASSWORD),
                role="support_agent",
                is_active=True,
            )

            db.add(user)
            await db.commit()

            user_id = user.id

        app.dependency_overrides[get_db] = override_get_db

        async def attempt_login(index: int):
            # Each request uses a different simulated IP.
            ip = f"192.0.2.{index + 10}"

            transport = httpx.ASGITransport(
                app=app,
                client=(ip, 50000 + index),
            )

            async with httpx.AsyncClient(
                transport=transport,
                base_url="https://localhost",
                timeout=30.0,
            ) as client:
                response = await client.post(
                    "/api/auth/login",
                    json={
                        "email": email,
                        "password": "IncorrectPassword123!",
                    },
                    headers={"Origin": ORIGIN},
                )

                return response.status_code

        # Launch requests concurrently.
        results = await asyncio.gather(
            *[
                attempt_login(index)
                for index in range(10)
            ]
        )

        # Account-level rate limit must apply across IPs.
        assert results.count(401) == 5, results
        assert results.count(429) == 5, results

        # Confirm only five failures were persisted.
        _, account_key = get_login_keys(
            client_ip="unused",
            email=email,
        )

        async with session_factory() as db:
            result = await db.execute(
                select(LoginAttempt)
                .where(
                    LoginAttempt.account_key == account_key,
                    LoginAttempt.succeeded.is_(False),
                )
            )

            recorded_failures = result.scalars().all()

        assert len(recorded_failures) == 5

    finally:
        app.dependency_overrides.pop(get_db, None)

        # Clean up only data created by this test.
        _, account_key = get_login_keys(
            client_ip="unused",
            email=email,
        )

        try:
            async with session_factory() as db:
                await db.execute(
                    delete(LoginAttempt).where(
                        LoginAttempt.account_key == account_key
                    )
                )

                if user_id is not None:
                    await db.execute(
                        delete(User).where(
                            User.id == user_id
                        )
                    )

                await db.commit()
        finally:
            await engine.dispose()