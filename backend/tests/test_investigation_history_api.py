
"""API tests for investigation history endpoints."""
import pytest_asyncio
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.db.session import get_db
from app.core.auth import get_current_user
from tests.rbac_test_helpers import override_current_user

NOW = datetime.now(timezone.utc)


@pytest.fixture
def fake_run():
    return SimpleNamespace(
        id=17,
        ticket_id=2,
        order_number="ORD-1001",
        status="completed",
        report="Investigation completed successfully.",
        selected_agents=["order", "shipment", "policy"],
        policy_ids=["POL-DELIVERY-001"],
        evidence={"order": {"found": True}},
        verification={"status": "passed"},
        created_at=NOW,
        completed_at=NOW,
    )


@pytest_asyncio.fixture
async def api_client():
    """Authenticated API client with mocked DB dependency."""

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
async def test_list_investigations(api_client, fake_run):
    with patch(
        "app.api.investigations."
        "investigation_repository.list_investigations",
        new_callable=AsyncMock,
    ) as mock_list:
        mock_list.return_value = ([fake_run], 17)

        response = await api_client.get(
            "/api/investigations",
            params={"limit": 5, "offset": 0},
        )

    assert response.status_code == 200

    data = response.json()

    assert data["total"] == 17
    assert data["limit"] == 5
    assert data["offset"] == 0
    assert len(data["items"]) == 1
    assert data["items"][0]["id"] == 17

    # Large fields should not appear in list responses.
    assert "report" not in data["items"][0]
    assert "evidence" not in data["items"][0]


@pytest.mark.asyncio
async def test_list_investigations_filters(api_client):
    with patch(
        "app.api.investigations."
        "investigation_repository.list_investigations",
        new_callable=AsyncMock,
    ) as mock_list:
        mock_list.return_value = ([], 0)

        response = await api_client.get(
            "/api/investigations",
            params={
                "ticket_id": 2,
                "status": "completed",
                "limit": 10,
                "offset": 5,
            },
        )

        assert response.status_code == 200

        kwargs = mock_list.await_args.kwargs

        assert kwargs["ticket_id"] == 2
        assert kwargs["status"] == "completed"
        assert kwargs["limit"] == 10
        assert kwargs["offset"] == 5


@pytest.mark.asyncio
async def test_investigation_detail(api_client, fake_run):
    with patch(
        "app.api.investigations."
        "investigation_repository.get_investigation",
        new_callable=AsyncMock,
    ) as mock_get:
        mock_get.return_value = fake_run

        response = await api_client.get(
            "/api/investigations/17"
        )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == 17
    assert data["status"] == "completed"
    assert data["evidence"]["order"]["found"] is True
    assert data["verification"]["status"] == "passed"


@pytest.mark.asyncio
async def test_missing_investigation_returns_404(api_client):
    with patch(
        "app.api.investigations."
        "investigation_repository.get_investigation",
        new_callable=AsyncMock,
    ) as mock_get:
        mock_get.return_value = None

        response = await api_client.get(
            "/api/investigations/99999"
        )

    assert response.status_code == 404
    assert response.json()["detail"] == (
        "Investigation not found"
    )


@pytest.mark.asyncio
async def test_invalid_pagination_returns_422(api_client):
    response = await api_client.get(
        "/api/investigations",
        params={"limit": 101, "offset": -1},
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_investigation_audit_events(api_client, fake_run):
    events = [
        SimpleNamespace(
            id=28,
            investigation_id=17,
            event_type="investigation_started",
            details={"order_number": "ORD-1001"},
            created_at=NOW,
        ),
        SimpleNamespace(
            id=30,
            investigation_id=17,
            event_type="investigation_completed",
            details={"status": "completed"},
            created_at=NOW,
        ),
    ]

    with (
        patch(
            "app.api.investigations."
            "investigation_repository.get_investigation",
            new_callable=AsyncMock,
            return_value=fake_run,
        ),
        patch(
            "app.api.investigations."
            "investigation_repository.list_audit_events",
            new_callable=AsyncMock,
            return_value=events,
        ),
    ):
        response = await api_client.get(
            "/api/investigations/17/audit-events"
        )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 2
    assert data[0]["event_type"] == "investigation_started"
    assert data[1]["event_type"] == "investigation_completed"


@pytest.mark.asyncio
async def test_missing_investigation_audit_returns_404(
    api_client,
):
    with patch(
        "app.api.investigations."
        "investigation_repository.get_investigation",
        new_callable=AsyncMock,
        return_value=None,
    ):
        response = await api_client.get(
            "/api/investigations/99999/audit-events"
        )

    assert response.status_code == 404



@pytest.mark.asyncio
async def test_stale_endpoint_route_order(api_client):
    """Static /stale route must not match /{investigation_id}."""

    with patch(
        "app.api.investigations."
        "investigation_repository.list_stale_investigations",
        new_callable=AsyncMock,
        return_value=[],
    ) as mock_stale:
        response = await api_client.get(
            "/api/investigations/stale",
            params={"timeout_minutes": 30},
        )

    assert response.status_code == 200
    assert response.json() == []
    mock_stale.assert_awaited_once()
    assert mock_stale.await_args.kwargs["timeout_minutes"] == 30
