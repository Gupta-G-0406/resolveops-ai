
"""Heartbeat lifecycle for running AI investigations."""

import asyncio
import logging
from collections.abc import Awaitable
from typing import TypeVar

from app.db.session import AsyncSessionLocal
from app.services import investigation_repository

logger = logging.getLogger(__name__)

T = TypeVar("T")

HEARTBEAT_INTERVAL_SECONDS = 30
LEASE_SECONDS = 90


async def _heartbeat_loop(
    *,
    run_id: int,
    worker_id: str,
    interval_seconds: float,
    lease_seconds: int,
) -> None:
    """Renew the lease until cancelled or ownership is lost."""

    while True:
        await asyncio.sleep(interval_seconds)

        # Never share the request's AsyncSession with this task.
        async with AsyncSessionLocal() as db:
            renewed = await (
                investigation_repository.renew_investigation_lease(
                    db,
                    run_id=run_id,
                    worker_id=worker_id,
                    lease_seconds=lease_seconds,
                )
            )

        if not renewed:
            raise investigation_repository.InvestigationLeaseLostError(
                f"Heartbeat rejected for investigation {run_id}"
            )


async def run_with_heartbeat(
    operation: Awaitable[T],
    *,
    run_id: int,
    worker_id: str,
    interval_seconds: float = HEARTBEAT_INTERVAL_SECONDS,
    lease_seconds: int = LEASE_SECONDS,
) -> T:
    """Run an operation while independently renewing its lease.

    If the heartbeat fails, cancel the operation rather than
    allowing it to finish without confirmed ownership.
    """

    if interval_seconds <= 0:
        raise ValueError("interval_seconds must be positive")

    if lease_seconds <= 0:
        raise ValueError("lease_seconds must be positive")

    operation_task = asyncio.ensure_future(operation)

    heartbeat_task = asyncio.create_task(
        _heartbeat_loop(
            run_id=run_id,
            worker_id=worker_id,
            interval_seconds=interval_seconds,
            lease_seconds=lease_seconds,
        )
    )

    try:
        done, _ = await asyncio.wait(
            {operation_task, heartbeat_task},
            return_when=asyncio.FIRST_COMPLETED,
        )

        # Prioritize heartbeat failure even when both tasks finish
        # at approximately the same time.
        if heartbeat_task in done:
            if heartbeat_task.cancelled():
                raise asyncio.CancelledError()

            heartbeat_error = heartbeat_task.exception()

            if heartbeat_error is not None:
                raise heartbeat_error

        if operation_task in done:
            return await operation_task

        # Normally unreachable because a healthy heartbeat
        # runs until it is cancelled.
        raise RuntimeError(
            "Heartbeat stopped before investigation completed"
        )

    finally:
        for task in (operation_task, heartbeat_task):
            if not task.done():
                task.cancel()

        # Wait for task cleanup, including cancellation handlers.
        await asyncio.gather(
            operation_task,
            heartbeat_task,
            return_exceptions=True,
        )
