
import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from app.services.investigation_heartbeat import (
    run_with_heartbeat,
)
from app.services.investigation_repository import (
    InvestigationLeaseLostError,
)


@pytest.mark.asyncio
async def test_operation_completes_with_heartbeat():
    async def operation():
        await asyncio.sleep(0)
        return {"status": "completed"}

    result = await run_with_heartbeat(
        operation(),
        run_id=10,
        worker_id="worker-1",
        interval_seconds=0.01,
    )

    assert result == {"status": "completed"}


@pytest.mark.asyncio
async def test_operation_exception_propagates():
    async def operation():
        raise RuntimeError("LangGraph failed")

    with pytest.raises(RuntimeError, match="LangGraph failed"):
        await run_with_heartbeat(
            operation(),
            run_id=10,
            worker_id="worker-1",
            interval_seconds=0.01,
        )


@pytest.mark.asyncio
async def test_heartbeat_failure_cancels_operation():
    cancelled = asyncio.Event()

    async def operation():
        try:
            await asyncio.sleep(60)
        finally:
            cancelled.set()

    with patch(
        "app.services.investigation_heartbeat._heartbeat_loop",
        new_callable=AsyncMock,
        side_effect=InvestigationLeaseLostError("Lease lost"),
    ):
        with pytest.raises(
            InvestigationLeaseLostError,
            match="Lease lost",
        ):
            await run_with_heartbeat(
                operation(),
                run_id=10,
                worker_id="worker-1",
            )

    assert cancelled.is_set()


@pytest.mark.asyncio
async def test_external_cancellation_cleans_up_operation():
    cancelled = asyncio.Event()

    async def operation():
        try:
            await asyncio.sleep(60)
        finally:
            cancelled.set()

    task = asyncio.create_task(
        run_with_heartbeat(
            operation(),
            run_id=10,
            worker_id="worker-1",
        )
    )

    await asyncio.sleep(0)
    task.cancel()

    with pytest.raises(asyncio.CancelledError):
        await task

    assert cancelled.is_set()
