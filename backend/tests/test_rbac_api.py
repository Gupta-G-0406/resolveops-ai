from uuid import uuid4
from unittest.mock import AsyncMock, patch

import httpx
import pytest
import pytest_asyncio

from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import (
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings
from app.core.security import hash_password
from app.db.session import get_db
from app.main import app
from app.models.user import User, UserRole


PASSWORD = "StrongTestPassword123!"
ORIGIN = "http://localhost:5173"


@pytest_asyncio.fixture
async def rbac_client():
    """Use real sessions against the isolated test database."""

    source_url = make_url(settings.database_url)

    if source_url.host not in ("localhost", "127.0.0.1"):
        raise RuntimeError("RBAC tests require local PostgreSQL")

    engine = create_async_engine(
        source_url.set(database="resolveops_test_db")
    )

    async with engine.connect() as connection:
        transaction = await connection.begin()

        session_factory = async_sessionmaker(
            bind=connection,
            expire_on_commit=False,
            join_transaction_mode="create_savepoint",
        )

        async def override_get_db():
            async with session_factory() as db:
                yield db

        if get_db in app.dependency_overrides:
            raise RuntimeError("Unexpected database override")

        app.dependency_overrides[get_db] = override_get_db

        try:
            credentials = {}

            async with session_factory() as db:
                for role in UserRole:
                    email = (
                        f"rbac-{role.value}-{uuid4().hex}"
                        "@example.com"
                    )

                    db.add(
                        User(
                            email=email,
                            full_name=f"RBAC {role.value}",
                            password_hash=hash_password(PASSWORD),
                            role=role.value,
                            is_active=True,
                        )
                    )

                    credentials[role] = email

                await db.commit()

            yield credentials

        finally:
            app.dependency_overrides.pop(get_db, None)
            await transaction.rollback()
            await engine.dispose()


async def make_logged_in_client(email):
    transport = httpx.ASGITransport(app=app)

    client = httpx.AsyncClient(
        transport=transport,
        base_url="https://localhost",
    )

    response = await client.post(
        "/api/auth/login",
        json={
            "email": email,
            "password": PASSWORD,
        },
        headers={"Origin": ORIGIN},
    )

    assert response.status_code == 200, response.text

    return client


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "path",
    [
        "/api/orders",
        "/api/tickets",
        "/api/investigations",
        "/api/investigations/stats",
        "/api/investigations/stale",
    ],
)
async def test_guest_cannot_access_business_apis(path):
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(
        transport=transport,
        base_url="https://localhost",
    ) as client:
        response = await client.get(path)

    assert response.status_code == 401


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "role,method,path",
    [
        (UserRole.AUDITOR, "POST", "/api/tickets"),
        (UserRole.AUDITOR, "POST", "/api/tickets/2/investigate"),
        (UserRole.SUPPORT_AGENT, "GET", "/api/investigations/stale"),
        (
            UserRole.SUPPORT_AGENT,
            "GET",
            "/api/investigations/17/audit-events",
        ),
    ],
)
async def test_forbidden_role_access(
    rbac_client,
    role,
    method,
    path,
):
    client = await make_logged_in_client(rbac_client[role])

    try:
        response = await client.request(method, path)

        assert response.status_code == 403
        assert response.json()["detail"] == (
            "Insufficient permissions"
        )
    finally:
        await client.aclose()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "role",
    [
        UserRole.ADMIN,
        UserRole.SUPERVISOR,
        UserRole.SUPPORT_AGENT,
        UserRole.AUDITOR,
    ],
)
async def test_all_roles_can_read_investigation_stats(
    rbac_client,
    role,
):
    expected = {
        "total": 0,
        "completed": 0,
        "needs_review": 0,
        "failed": 0,
        "running": 0,
        "success_rate": 0.0,
    }

    client = await make_logged_in_client(rbac_client[role])

    try:
        with patch(
            "app.api.investigations."
            "investigation_repository.get_investigation_stats",
            new_callable=AsyncMock,
            return_value=expected,
        ) as mock_stats:
            response = await client.get(
                "/api/investigations/stats"
            )

        assert response.status_code == 200
        assert response.json() == expected
        mock_stats.assert_awaited_once()

    finally:
        await client.aclose()