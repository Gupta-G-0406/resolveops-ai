
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.investigation_repository import (
    InvestigationLeaseLostError,
    complete_run_owned,
    fail_run_owned,
)



def mock_db(updated_id):
    db = AsyncMock()

    # SQLAlchemy AsyncSession.add() is synchronous.
    db.add = MagicMock()

    result = MagicMock()
    result.scalar_one_or_none.return_value = updated_id

    db.execute.return_value = result

    return db


def investigation_result():
    return {
        "status": "completed",
        "report": "Investigation completed successfully",
        "selected_agents": ["order_agent"],
        "policy_ids": [],
        "verification": {},
        "evidence": {},
    }


@pytest.mark.asyncio
async def test_owned_completion_success():
    db = mock_db(10)

    await complete_run_owned(
        db,
        run_id=10,
        worker_id="worker-1",
        result=investigation_result(),
        evidence={},
    )

    db.execute.assert_awaited_once()
    db.add.assert_called_once()
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_owned_completion_rejected():
    db = mock_db(None)

    with pytest.raises(InvestigationLeaseLostError):
        await complete_run_owned(
            db,
            run_id=10,
            worker_id="wrong-worker",
            result=investigation_result(),
            evidence={},
        )

    db.commit.assert_not_awaited()
    db.add.assert_not_called()
    db.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_owned_failure_success():
    db = mock_db(10)

    await fail_run_owned(
        db,
        run_id=10,
        worker_id="worker-1",
        error_type="MCPConnectionError",
    )

    db.execute.assert_awaited_once()
    db.add.assert_called_once()
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_owned_failure_rejected():
    db = mock_db(None)

    with pytest.raises(InvestigationLeaseLostError):
        await fail_run_owned(
            db,
            run_id=10,
            worker_id="wrong-worker",
            error_type="RuntimeError",
        )

    db.commit.assert_not_awaited()
    db.add.assert_not_called()
    db.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_completion_audit_commit_failure():
    db = mock_db(10)
    db.commit.side_effect = RuntimeError("Database commit failed")

    with pytest.raises(RuntimeError, match="Database commit failed"):
        await complete_run_owned(
            db,
            run_id=10,
            worker_id="worker-1",
            result=investigation_result(),
            evidence={},
        )

    db.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_invalid_completion_status():
    db = mock_db(10)
    result = investigation_result()
    result["status"] = "running"

    with pytest.raises(ValueError):
        await complete_run_owned(
            db,
            run_id=10,
            worker_id="worker-1",
            result=result,
            evidence={},
        )

    db.execute.assert_not_awaited()
