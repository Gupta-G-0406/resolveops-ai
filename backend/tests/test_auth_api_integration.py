from uuid import uuid4

import httpx
import pytest
import pytest_asyncio

from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import (
    async_sessionmaker,
    create_async_engine,
)

from app.main import app
from app.core.config import settings
from app.core.security import hash_password
from app.db.session import get_db
from app.models.user import User


TEST_DB_NAME = "resolveops_test_db"
ORIGIN = "http://localhost:5173"
PASSWORD = "StrongTestPassword123!"


@pytest_asyncio.fixture
async def auth_client():
    # Never use the development database for these tests.
    source_url = make_url(settings.database_url)

    if source_url.host not in ("localhost", "127.0.0.1"):
        raise RuntimeError(
            "Authentication integration tests require local PostgreSQL"
        )

    test_url = source_url.set(database=TEST_DB_NAME)

    engine = create_async_engine(test_url)

    try:
        async with engine.connect() as connection:
            outer_transaction = await connection.begin()

            session_factory = async_sessionmaker(
                bind=connection,
                expire_on_commit=False,
                join_transaction_mode="create_savepoint",
            )

            async def override_get_db():
                async with session_factory() as db:
                    yield db

            app.dependency_overrides[get_db] = override_get_db

            try:
                async with session_factory() as db:
                    user = User(
                        email=f"auth-{uuid4().hex}@example.com",
                        full_name="Auth Test User",
                        password_hash=hash_password(PASSWORD),
                        role="support_agent",
                        is_active=True,
                    )

                    db.add(user)
                    await db.commit()

                    user_id = user.id
                    email = user.email

                transport = httpx.ASGITransport(app=app)

                async with httpx.AsyncClient(
                    transport=transport,
                    base_url="https://localhost",
                ) as client:
                    yield client, user_id, email

            finally:
                app.dependency_overrides.pop(get_db, None)
                await outer_transaction.rollback()
    finally:
        await engine.dispose()


async def login(client, email, password=PASSWORD):
    return await client.post(
        "/api/auth/login",
        json={
            "email": email,
            "password": password,
        },
        headers={"Origin": ORIGIN},
    )


@pytest.mark.asyncio
async def test_login_success(auth_client):
    client, user_id, email = auth_client

    response = await login(client, email)

    assert response.status_code == 200
    assert response.json()["id"] == user_id
    assert response.json()["email"] == email
    assert "password_hash" not in response.json()

    cookie = response.headers["set-cookie"].lower()
    if settings.session_cookie_secure:
        assert "secure" in cookie

    assert "httponly" in cookie
    assert "samesite=lax" in cookie


@pytest.mark.asyncio
async def test_login_rejects_wrong_password(auth_client):
    client, _, email = auth_client

    response = await login(
        client,
        email,
        password="WrongPassword123!",
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_me_requires_authentication(auth_client):
    client, _, _ = auth_client

    response = await client.get("/api/auth/me")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_me_returns_authenticated_user(auth_client):
    client, user_id, email = auth_client

    login_response = await login(client, email)

    assert login_response.status_code == 200

    response = await client.get("/api/auth/me")

    assert response.status_code == 200
    assert response.json()["id"] == user_id


@pytest.mark.asyncio
async def test_logout_revokes_session(auth_client):
    client, _, email = auth_client

    assert (await login(client, email)).status_code == 200

    logout_response = await client.post(
        "/api/auth/logout",
        headers={"Origin": ORIGIN},
    )

    assert logout_response.status_code == 200

    me_response = await client.get("/api/auth/me")

    assert me_response.status_code == 401


@pytest.mark.asyncio
async def test_logout_all_revokes_multiple_sessions(auth_client):
    client_one, _, email = auth_client

    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(
        transport=transport,
        base_url="https://localhost",
    ) as client_two:

        assert (await login(client_one, email)).status_code == 200
        assert (await login(client_two, email)).status_code == 200

        response = await client_one.post(
            "/api/auth/logout-all",
            headers={"Origin": ORIGIN},
        )

        assert response.status_code == 200

        assert (
            await client_one.get("/api/auth/me")
        ).status_code == 401

        assert (
            await client_two.get("/api/auth/me")
        ).status_code == 401


@pytest.mark.asyncio
async def test_login_rejects_untrusted_origin(auth_client):
    client, _, email = auth_client

    response = await client.post(
        "/api/auth/login",
        json={
            "email": email,
            "password": PASSWORD,
        },
        headers={"Origin": "https://evil.example"},
    )

    assert response.status_code == 403