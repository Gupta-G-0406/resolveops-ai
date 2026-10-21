import pytest
import httpx
from app.core.config import settings
from tests.test_auth_api_integration import (
    auth_client,
    login,
    PASSWORD,
)
from datetime import datetime, timedelta, timezone

from sqlalchemy import update

from app.models.login_attempt import LoginAttempt
from app.services.login_rate_limit_service import get_login_keys
from app.db.session import get_db
from app.main import app


@pytest.mark.asyncio
async def test_account_rate_limit_after_five_failures(
    auth_client,
):
    client, user_id, email = auth_client

    for attempt in range(5):
        response = await login(
            client,
            email,
            password="IncorrectPassword123!",
        )

        assert response.status_code == 401

    response = await login(
        client,
        email,
        password=PASSWORD,
    )

    assert response.status_code == 429
    assert "Retry-After" in response.headers


@pytest.mark.asyncio
async def test_client_rate_limit_after_ten_attempts(
    auth_client,
):
    client, user_id, email = auth_client

    # Different accounts prevent the per-account
    # limit from triggering first.
    for attempt in range(10):
        response = await login(
            client,
            f"unknown-{attempt}@example.com",
            password="IncorrectPassword123!",
        )

        assert response.status_code == 401

    response = await login(
        client,
        email,
        password=PASSWORD,
    )

    assert response.status_code == 429
    assert "Retry-After" in response.headers



@pytest.mark.asyncio
async def test_expired_account_failures_do_not_block_login(
    auth_client,
):
    client, _, email = auth_client

    # Create five failed attempts.
    for _ in range(5):
        response = await login(
            client,
            email,
            password="IncorrectPassword123!",
        )
        assert response.status_code == 401

    # Verify the account is initially blocked.
    blocked = await login(client, email, password=PASSWORD)
    assert blocked.status_code == 429

    # Move account attempts outside the active window.
    _, account_key= get_login_keys(
        client_ip="unused",
        email=email,
    )

    # The fixture overrides get_db, so reuse that dependency.
    db_override = app.dependency_overrides[get_db]

    async for db in db_override():
        await db.execute(
            update(LoginAttempt)
            .where(LoginAttempt.account_key == account_key)
            .values(
                created_at=(
                    datetime.now(timezone.utc)
                    - timedelta(minutes=16)
                )
            )
        )
        await db.commit()

    # The old failures should no longer count.
    allowed = await login(client, email, password=PASSWORD)
    assert allowed.status_code == 200

@pytest.mark.asyncio
async def test_retry_after_uses_remaining_window(auth_client):
    client, _, email = auth_client

    # Generate five failed attempts.
    for _ in range(5):
        response = await login(
            client,
            email,
            password="IncorrectPassword123!",
        )
        assert response.status_code == 401

    _, account_key = get_login_keys(
        client_ip="unused",
        email=email,
    )

    # Make failures approximately 14 minutes old.
    db_override = app.dependency_overrides[get_db]

    async for db in db_override():
        await db.execute(
            update(LoginAttempt)
            .where(LoginAttempt.account_key == account_key)
            .values(
                created_at=(
                    datetime.now(timezone.utc)
                    - timedelta(minutes=14)
                )
            )
        )
        await db.commit()

    # The account remains blocked, but only ~1 minute remains.
    response = await login(
        client,
        email,
        password=PASSWORD,
    )

    assert response.status_code == 429

    retry_after = int(response.headers["Retry-After"])

    assert 1 <= retry_after <= 90



@pytest.mark.asyncio
async def test_successful_login_resets_account_failure_count(
    auth_client,
):
    client, _, email = auth_client

    # Four failed attempts, below account limit.
    for _ in range(4):
        response = await login(
            client,
            email,
            password="IncorrectPassword123!",
        )
        assert response.status_code == 401

    # Successful login creates a reset boundary.
    response = await login(
        client,
        email,
        password=PASSWORD,
    )
    assert response.status_code == 200

    # Four more failures should be allowed.
    for _ in range(4):
        response = await login(
            client,
            email,
            password="IncorrectPassword123!",
        )
        assert response.status_code == 401

    # Account now has four failures after its latest success.
    # But the client has already made nine attempts.
    # The next request is the tenth admitted client attempt.
    response = await login(
        client,
        email,
        password="IncorrectPassword123!",
    )
    assert response.status_code == 401

    # Now the client limit should apply.
    response = await login(
        client,
        email,
        password=PASSWORD,
    )
    assert response.status_code == 429


@pytest.mark.asyncio
async def test_account_reset_across_different_client_ips(
    auth_client,
):
    _, _, email = auth_client

    async def attempt_from_ip(
        ip: str,
        password: str,
    ):
        transport = httpx.ASGITransport(
            app=app,
            client=(ip, 50000),
        )

        async with httpx.AsyncClient(
            transport=transport,
            base_url="https://localhost",
        ) as client:
            return await login(
                client,
                email,
                password=password,
            )

    # Four failures from IP A.
    for _ in range(4):
        response = await attempt_from_ip(
            "192.0.2.10",
            "IncorrectPassword123!",
        )
        assert response.status_code == 401

    # Successful login from IP B resets account failures.
    response = await attempt_from_ip(
        "192.0.2.20",
        PASSWORD,
    )
    assert response.status_code == 200

    # Four more failures from IP C.
    for _ in range(4):
        response = await attempt_from_ip(
            "192.0.2.30",
            "IncorrectPassword123!",
        )
        assert response.status_code == 401

    # Fifth failure after reset is accepted.
    response = await attempt_from_ip(
        "192.0.2.40",
        "IncorrectPassword123!",
    )
    assert response.status_code == 401

    # Next attempt must be blocked by account limit,
    # even though it comes from a different IP.
    response = await attempt_from_ip(
        "192.0.2.50",
        PASSWORD,
    )
    assert response.status_code == 429