
"""Tests for ResolveOps AI investigation analytics."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.db.session import get_db
from app.services.investigation_repository import (
    get_investigation_stats,
)

from app.core.auth import get_current_user
from tests.rbac_test_helpers import override_current_user

@pytest_asyncio.fixture
async def api_client():
    """Authenticated API client without PostgreSQL access."""

    async def override_get_db():
        yield object()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = (
        override_current_user
    )

    try:
        transport = ASGITransport(app=app)

        async with AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as client:
            yield client

    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_user, None)

@pytest.mark.asyncio
async def test_stats_api_success(api_client):
    """API should return valid investigation statistics."""

    expected = {
        "total": 17,
        "completed": 13,
        "needs_review": 0,
        "failed": 1,
        "running": 3,
        "success_rate": 76.47,
    }

    with patch(
        "app.api.investigations."
        "investigation_repository.get_investigation_stats",
        new_callable=AsyncMock,
        return_value=expected,
    ) as mock_stats:

        response = await api_client.get(
            "/api/investigations/stats"
        )

    assert response.status_code == 200
    assert response.json() == expected
    mock_stats.assert_awaited_once()


@pytest.mark.asyncio
async def test_stats_api_empty_database(api_client):
    """Empty database should produce zero counts."""

    expected = {
        "total": 0,
        "completed": 0,
        "needs_review": 0,
        "failed": 0,
        "running": 0,
        "success_rate": 0.0,
    }

    with patch(
        "app.api.investigations."
        "investigation_repository.get_investigation_stats",
        new_callable=AsyncMock,
        return_value=expected,
    ):
        response = await api_client.get(
            "/api/investigations/stats"
        )

    assert response.status_code == 200
    assert response.json() == expected


@pytest.mark.asyncio
async def test_stats_repository_calculation():
    """Repository should calculate counts and completion rate."""

    mock_db = AsyncMock()

    mock_result = MagicMock()
    mock_result.all.return_value = [
        ("completed", 13),
        ("running", 3),
        ("failed", 1),
    ]

    mock_db.execute.return_value = mock_result

    stats = await get_investigation_stats(mock_db)

    assert stats["total"] == 17
    assert stats["completed"] == 13
    assert stats["running"] == 3
    assert stats["failed"] == 1
    assert stats["needs_review"] == 0
    assert stats["success_rate"] == 76.47

    mock_db.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_stats_repository_empty_database():
    """Repository should handle an empty result set."""

    mock_db = AsyncMock()

    mock_result = MagicMock()
    mock_result.all.return_value = []

    mock_db.execute.return_value = mock_result

    stats = await get_investigation_stats(mock_db)

    assert stats["total"] == 0
    assert stats["completed"] == 0
    assert stats["success_rate"] == 0.0


@pytest.mark.asyncio
async def test_stats_repository_all_statuses():
    """All supported statuses should be counted."""

    mock_db = AsyncMock()

    mock_result = MagicMock()
    mock_result.all.return_value = [
        ("completed", 6),
        ("needs_review", 2),
        ("failed", 1),
        ("running", 1),
    ]

    mock_db.execute.return_value = mock_result

    stats = await get_investigation_stats(mock_db)

    assert stats == {
        "total": 10,
        "completed": 6,
        "needs_review": 2,
        "failed": 1,
        "running": 1,
        "success_rate": 60.0,
    }


@pytest.mark.asyncio
async def test_stats_api_response_validation(api_client):
    """FastAPI should validate the analytics response."""

    invalid_stats = {
        "total": "not-a-number",
        "completed": 5,
        "needs_review": 0,
        "failed": 0,
        "running": 0,
        "success_rate": 100.0,
    }

    with patch(
        "app.api.investigations."
        "investigation_repository.get_investigation_stats",
        new_callable=AsyncMock,
        return_value=invalid_stats,
    ):
        with pytest.raises(Exception) as exc_info:
            await api_client.get(
                "/api/investigations/stats"
            )

    assert "ResponseValidationError" in (
        type(exc_info.value).__name__
    )
