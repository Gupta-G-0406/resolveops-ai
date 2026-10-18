
"""Standalone recovery worker for expired investigation leases."""

import asyncio
import logging
import os

from sqlalchemy import select, func

from app.db.session import AsyncSessionLocal, engine
from app.models.investigation import InvestigationRun
from app.services.investigation_repository import (
    recover_expired_investigation,
)

logger = logging.getLogger(__name__)

RECOVERY_INTERVAL_SECONDS = 60
RECOVERY_BATCH_SIZE = 50


async def recover_expired_batch(
    *,
    batch_size: int = RECOVERY_BATCH_SIZE,
) -> int:
    """Recover a bounded batch of expired, owned investigations."""

    if batch_size <= 0:
        raise ValueError("batch_size must be positive")

    # Read candidates without modifying them.
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(InvestigationRun.id)
            .where(
                InvestigationRun.status == "running",
                InvestigationRun.worker_id.is_not(None),
                InvestigationRun.lease_expires_at.is_not(None),
                InvestigationRun.lease_expires_at
                <= func.clock_timestamp(),
            )
            .order_by(
                InvestigationRun.lease_expires_at.asc(),
                InvestigationRun.id.asc(),
            )
            .limit(batch_size)
        )

        run_ids = list(result.scalars().all())

    recovered_count = 0

    for run_id in run_ids:
        try:
            async with AsyncSessionLocal() as db:
                recovered = await recover_expired_investigation(
                    db,
                    run_id=run_id,
                )

            if recovered:
                recovered_count += 1
                logger.warning(
                    "Recovered expired investigation: run_id=%s",
                    run_id,
                )

        except Exception:
            logger.exception(
                "Recovery failed for investigation: run_id=%s",
                run_id,
            )

    return recovered_count


async def run_recovery_worker(
    *,
    interval_seconds: float = RECOVERY_INTERVAL_SECONDS,
) -> None:
    """Continuously scan for expired investigation leases."""

    if interval_seconds <= 0:
        raise ValueError("interval_seconds must be positive")

    logger.info(
        "Investigation recovery worker started: interval=%ss",
        interval_seconds,
    )

    while True:
        try:
            count = await recover_expired_batch()

            if count:
                logger.info(
                    "Recovery cycle finished: recovered=%s",
                    count,
                )

        except Exception:
            logger.exception("Investigation recovery cycle failed")

        await asyncio.sleep(interval_seconds)


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format=(
            "%(asctime)s %(levelname)s "
            "%(name)s: %(message)s"
        ),
    )

    interval = float(
        os.getenv(
            "RECOVERY_INTERVAL_SECONDS",
            str(RECOVERY_INTERVAL_SECONDS),
        )
    )

    try:
        await run_recovery_worker(
            interval_seconds=interval,
        )
    finally:
        await engine.dispose()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.getLogger(__name__).info(
            "Recovery worker stopped"
        )
