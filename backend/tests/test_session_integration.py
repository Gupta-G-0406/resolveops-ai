from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
import pytest_asyncio

from sqlalchemy import select
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import (
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings
from app.core.security import hash_password
from app.models.user import User
from app.models.user_session import UserSession
from app.services.session_service import (
    create_session,
    get_active_session,
    hash_session_token,
    revoke_session,
    revoke_all_user_sessions,
)


TEST_DATABASE_NAME = "resolveops_test_db"


@pytest_asyncio.fixture
async def test_db():
    # Always connect to the dedicated test database.
    url = make_url(settings.database_url).set(
        database=TEST_DATABASE_NAME
    )

    if url.database != TEST_DATABASE_NAME:
        raise RuntimeError("Refusing to use a non-test database")

    engine = create_async_engine(url)

    session_factory = async_sessionmaker(
        engine,
        expire_on_commit=False,
    )

    try:
        async with session_factory() as db:
            user = User(
                email=f"session-test-{uuid4().hex}@example.com",
                full_name="Session Test User",
                password_hash=hash_password("TestPassword123!"),
                role="support_agent",
                is_active=True,
            )

            db.add(user)
            await db.flush()

            try:
                yield db, user
            finally:
                await db.rollback()
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_create_session_stores_only_hash(test_db):
    db, user = test_db

    token = await create_session(db, user_id=user.id)

    result = await db.execute(
        select(UserSession).where(
            UserSession.user_id == user.id
        )
    )

    session = result.scalar_one()

    assert session.token_hash == hash_session_token(token)
    assert session.token_hash != token


@pytest.mark.asyncio
async def test_valid_session_can_be_retrieved(test_db):
    db, user = test_db

    token = await create_session(db, user_id=user.id)

    session = await get_active_session(db, token)

    assert session is not None
    assert session.user_id == user.id


@pytest.mark.asyncio
async def test_expired_session_is_rejected(test_db):
    db, user = test_db

    # Step 1: Create a valid session.
    token = await create_session(
        db,
        user_id=user.id,
    )

    session = await get_active_session(db, token)

    assert session is not None

    # Step 2: Simulate a session created 2 hours ago.
    now = datetime.now(timezone.utc)

    session.created_at = now - timedelta(hours=2)

    # Step 3: Session expired 1 hour ago.
    session.expires_at = now - timedelta(hours=1)

    # created_at < expires_at < now
    # So database constraint remains valid.

    await db.flush()

    # Step 4: Try retrieving expired session.
    expired = await get_active_session(db, token)

    assert expired is None

@pytest.mark.asyncio
async def test_revoked_session_is_rejected(test_db):
    db, user = test_db

    token = await create_session(db, user_id=user.id)

    await revoke_session(db, token)

    session = await get_active_session(db, token)

    assert session is None


@pytest.mark.asyncio
async def test_revoke_all_user_sessions(test_db):
    db, user = test_db

    first_token = await create_session(db, user_id=user.id)
    second_token = await create_session(db, user_id=user.id)

    await revoke_all_user_sessions(db, user.id)

    assert await get_active_session(db, first_token) is None
    assert await get_active_session(db, second_token) is None