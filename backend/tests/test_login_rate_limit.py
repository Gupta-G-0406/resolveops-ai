import pytest

from tests.test_auth_api_integration import (
    auth_client,
    login,
    PASSWORD,
)


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