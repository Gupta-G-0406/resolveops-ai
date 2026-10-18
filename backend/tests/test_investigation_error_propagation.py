
from types import SimpleNamespace
from unittest.mock import ANY, AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from app.main import app
from app.db.session import get_db
from app.mcp.client_tools import (
    MCPConnectionError,
    MCPToolError,
)


# Mock database session.
fake_db = AsyncMock()

# SQLAlchemy AsyncSession.add() is synchronous.
fake_db.add = MagicMock()


async def override_get_db():
    yield fake_db


def make_ticket():
    return SimpleNamespace(
        id=2,
        order=SimpleNamespace(
            order_number="TEST-ORDER-001"
        ),
    )


def run_failure_test(exception, expected_status, expected_code):
    fake_db.reset_mock()

    app.dependency_overrides[get_db] = override_get_db

    try:
        with (
            patch(
                "app.api.investigations.ticket_service.get_ticket_details",
                new_callable=AsyncMock,
                return_value=make_ticket(),
            ),
            patch(
                "app.api.investigations.investigation_repository.create_run",
                new_callable=AsyncMock,
                return_value=SimpleNamespace(id=999),
            ),
            patch(
                "app.api.investigations.investigation_repository.acquire_investigation_lease",
                new_callable=AsyncMock,
                return_value=True,
            ) as mock_acquire_lease,
            patch(
                "app.api.investigations.investigation_service.investigate_ticket",
                new_callable=AsyncMock,
                side_effect=exception,
            ),
            patch(
                "app.api.investigations.investigation_repository.fail_run_owned",
                new_callable=AsyncMock,
            ) as mock_fail_run_owned,
            patch(
                "app.api.investigations.investigation_repository.complete_run_owned",
                new_callable=AsyncMock,
            ) as mock_complete_run_owned,
        ):
            # Avoid starting the real MCP subprocess.
            client = TestClient(
                app,
                raise_server_exceptions=False,
            )

            response = client.post(
                "/api/tickets/2/investigate"
            )

            # Original MCP HTTP error mapping must remain intact.
            assert response.status_code == expected_status
            assert response.json()["detail"]["code"] == expected_code

            # Worker must acquire a lease before investigation.
            mock_acquire_lease.assert_awaited_once_with(
                fake_db,
                run_id=999,
                worker_id=ANY,
            )

            # Failure must be persisted through the
            # ownership-safe repository function.
            mock_fail_run_owned.assert_awaited_once_with(
                fake_db,
                run_id=999,
                worker_id=ANY,
                error_type=type(exception).__name__,
            )

            # Failed investigations must never be completed.
            mock_complete_run_owned.assert_not_awaited()

            # The original transaction must be rolled back.
            fake_db.rollback.assert_awaited_once()

            # Both repository calls must use the same worker ID.
            acquired_worker_id = (
                mock_acquire_lease.await_args.kwargs["worker_id"]
            )

            failed_worker_id = (
                mock_fail_run_owned.await_args.kwargs["worker_id"]
            )

            assert acquired_worker_id == failed_worker_id
            assert isinstance(acquired_worker_id, str)
            assert acquired_worker_id

    finally:
        app.dependency_overrides.clear()


def test_investigation_mcp_connection_failure():
    run_failure_test(
        MCPConnectionError("Simulated MCP disconnection"),
        expected_status=503,
        expected_code="MCP_UNAVAILABLE",
    )


def test_investigation_mcp_tool_failure():
    run_failure_test(
        MCPToolError("Simulated MCP tool failure"),
        expected_status=502,
        expected_code="MCP_TOOL_FAILED",
    )
