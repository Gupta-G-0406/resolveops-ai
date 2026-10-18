
"""Database operations for investigation runs and audit events."""

from datetime import datetime, timezone, timedelta
from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.investigation import InvestigationRun, AuditEvent


async def create_run(
    db: AsyncSession,
    ticket_id: int,
    order_number: str,
) -> InvestigationRun:
    """Create a new investigation record."""

    run = InvestigationRun(
        ticket_id=ticket_id,
        order_number=order_number,
        status="running",
    )

    db.add(run)
    await db.flush()

    db.add(
        AuditEvent(
            investigation_id=run.id,
            event_type="investigation_started",
            details={"order_number": order_number},
        )
    )

    await db.commit()
    await db.refresh(run)

    return run


async def complete_run(
    db: AsyncSession,
    run: InvestigationRun,
    result: dict,
    evidence: dict,
) -> InvestigationRun:
    """Save completed investigation results."""

    run.status = result["status"]
    run.report = result["report"]
    run.selected_agents = result["selected_agents"]
    run.policy_ids = result["policy_ids"]
    run.verification = result["verification"]
    run.evidence = evidence
    run.completed_at = datetime.now(timezone.utc)

    db.add(
        AuditEvent(
            investigation_id=run.id,
            event_type="investigation_completed",
            details={
                "status": run.status,
                "selected_agents": run.selected_agents,
                "policy_ids": run.policy_ids,
            },
        )
    )

    await db.commit()
    await db.refresh(run)

    return run





async def fail_run(
    db: AsyncSession,
    run_id: int,
    error_type: str,
) -> None:
    """Mark an investigation as failed using its primary key."""

    await db.execute(
        update(InvestigationRun)
        .where(InvestigationRun.id == run_id)
        .values(
            status="failed",
            completed_at=datetime.now(timezone.utc),
        )
    )

    db.add(
        AuditEvent(
            investigation_id=run_id,
            event_type="investigation_failed",
            details={"error_type": error_type},
        )
    )

    await db.commit()


async def list_ticket_runs(
    db: AsyncSession,
    ticket_id: int,
) -> list[InvestigationRun]:
    """Return newest investigation runs first."""

    result = await db.execute(
        select(InvestigationRun)
        .where(InvestigationRun.ticket_id == ticket_id)
        .order_by(InvestigationRun.created_at.desc())
    )

    return list(result.scalars().all())




async def list_investigations(
    db: AsyncSession,
    *,
    limit: int = 20,
    offset: int = 0,
    ticket_id: int | None = None,
    status: str | None = None,
) -> tuple[list[InvestigationRun], int]:
    """List investigations with pagination and filters."""

    filters = []

    if ticket_id is not None:
        filters.append(
            InvestigationRun.ticket_id == ticket_id
        )

    if status is not None:
        filters.append(
            InvestigationRun.status == status
        )

    count_query = select(
        func.count(InvestigationRun.id)
    ).where(*filters)

    total = (
        await db.execute(count_query)
    ).scalar_one()

    query = (
        select(InvestigationRun)
        .where(*filters)
        .order_by(
            InvestigationRun.created_at.desc(),
            InvestigationRun.id.desc(),
        )
        .limit(limit)
        .offset(offset)
    )

    result = await db.execute(query)

    return list(result.scalars().all()), total


async def get_investigation(
    db: AsyncSession,
    investigation_id: int,
) -> InvestigationRun | None:
    """Get an investigation by ID."""

    return await db.get(
        InvestigationRun,
        investigation_id,
    )


async def list_audit_events(
    db: AsyncSession,
    investigation_id: int,
) -> list[AuditEvent]:
    """Return audit events in chronological order."""

    result = await db.execute(
        select(AuditEvent)
        .where(
            AuditEvent.investigation_id == investigation_id
        )
        .order_by(
            AuditEvent.created_at.asc(),
            AuditEvent.id.asc(),
        )
    )

    return list(result.scalars().all())



async def get_investigation_stats(
    db: AsyncSession,
) -> dict:
    result = await db.execute(
        select(
            InvestigationRun.status,
            func.count(InvestigationRun.id),
        ).group_by(InvestigationRun.status)
    )

    counts = dict(result.all())

    total = sum(counts.values())
    completed = counts.get("completed", 0)

    success_rate = (
        round((completed / total) * 100, 2)
        if total > 0
        else 0.0
    )

    return {
        "total": total,
        "completed": completed,
        "needs_review": counts.get("needs_review", 0),
        "failed": counts.get("failed", 0),
        "running": counts.get("running", 0),
        "success_rate": success_rate,
    }



async def list_stale_investigations(
    db: AsyncSession,
    *,
    timeout_minutes: int = 30,
) -> list[InvestigationRun]:
    """Find old running investigations without modifying them."""

    if timeout_minutes <= 0:
        raise ValueError("timeout_minutes must be positive")

    cutoff = datetime.now(timezone.utc) - timedelta(
        minutes=timeout_minutes
    )

    result = await db.execute(
        select(InvestigationRun)
        .where(
            InvestigationRun.status == "running",
            InvestigationRun.created_at < cutoff,
        )
        .order_by(
            InvestigationRun.created_at.asc(),
            InvestigationRun.id.asc(),
        )
    )

    return list(result.scalars().all())



# ============================================================
# Investigation Worker Lease Management
# ============================================================

DEFAULT_LEASE_SECONDS = 90



async def acquire_investigation_lease(
    db: AsyncSession,
    *,
    run_id: int,
    worker_id: str,
    lease_seconds: int = DEFAULT_LEASE_SECONDS,
) -> bool:
    """Atomically claim an unowned running investigation."""

    if not worker_id.strip():
        raise ValueError("worker_id cannot be empty")

    if lease_seconds <= 0:
        raise ValueError("lease_seconds must be positive")

    db_now = func.clock_timestamp()
    expires_at = db_now + (
        func.make_interval(0, 0, 0, 0, 0, 0, lease_seconds)
    )

    result = await db.execute(
        update(InvestigationRun)
        .where(
            InvestigationRun.id == run_id,
            InvestigationRun.status == "running",
            InvestigationRun.worker_id.is_(None),
        )
        .values(
            worker_id=worker_id,
            heartbeat_at=db_now,
            lease_expires_at=expires_at,
        )
        .returning(InvestigationRun.id)
    )

    acquired = result.scalar_one_or_none() is not None

    await db.commit()
    return acquired



async def renew_investigation_lease(
    db: AsyncSession,
    *,
    run_id: int,
    worker_id: str,
    lease_seconds: int = DEFAULT_LEASE_SECONDS,
) -> bool:
    """Renew an active lease using PostgreSQL clock."""

    if not worker_id.strip():
        raise ValueError("worker_id cannot be empty")

    if lease_seconds <= 0:
        raise ValueError("lease_seconds must be positive")

    db_now = func.clock_timestamp()
    expires_at = db_now + (
        func.make_interval(0, 0, 0, 0, 0, 0, lease_seconds)
    )

    result = await db.execute(
        update(InvestigationRun)
        .where(
            InvestigationRun.id == run_id,
            InvestigationRun.status == "running",
            InvestigationRun.worker_id == worker_id,
            InvestigationRun.lease_expires_at > db_now,
        )
        .values(
            heartbeat_at=db_now,
            lease_expires_at=expires_at,
        )
        .returning(InvestigationRun.id)
    )

    renewed = result.scalar_one_or_none() is not None

    await db.commit()
    return renewed

# ============================================================
# Ownership-Fenced Investigation Finalization
# ============================================================


class InvestigationLeaseLostError(RuntimeError):
    """Worker no longer owns an active investigation lease."""


async def complete_run_owned(
    db: AsyncSession,
    *,
    run_id: int,
    worker_id: str,
    result: dict,
    evidence: dict,
) -> None:
    """Complete a run only while the worker owns a valid lease."""

    if not worker_id.strip():
        raise ValueError("worker_id cannot be empty")

    if result["status"] not in {"completed", "needs_review"}:
        raise ValueError("Invalid successful investigation status")

    now = func.clock_timestamp()

    try:
        updated = await db.execute(
            update(InvestigationRun)
            .where(
                InvestigationRun.id == run_id,
                InvestigationRun.status == "running",
                InvestigationRun.worker_id == worker_id,
                InvestigationRun.lease_expires_at > now,
            )
            .values(
                status=result["status"],
                report=result["report"],
                selected_agents=result["selected_agents"],
                policy_ids=result["policy_ids"],
                verification=result["verification"],
                evidence=evidence,
                completed_at=now,
                lease_expires_at=None,
            )
            .returning(InvestigationRun.id)
        )

        if updated.scalar_one_or_none() is None:
            raise InvestigationLeaseLostError(
                f"Cannot complete investigation {run_id}: "
                "worker does not own a valid lease"
            )

        db.add(
            AuditEvent(
                investigation_id=run_id,
                event_type="investigation_completed",
                details={
                    "status": result["status"],
                    "selected_agents": result["selected_agents"],
                    "policy_ids": result["policy_ids"],
                },
            )
        )

        await db.commit()

    except BaseException:
        await db.rollback()
        raise


async def fail_run_owned(
    db: AsyncSession,
    *,
    run_id: int,
    worker_id: str,
    error_type: str,
) -> None:
    """Fail a run only while the worker owns a valid lease."""

    if not worker_id.strip():
        raise ValueError("worker_id cannot be empty")

    now = func.clock_timestamp()

    try:
        updated = await db.execute(
            update(InvestigationRun)
            .where(
                InvestigationRun.id == run_id,
                InvestigationRun.status == "running",
                InvestigationRun.worker_id == worker_id,
                InvestigationRun.lease_expires_at > now,
            )
            .values(
                status="failed",
                completed_at=now,
                lease_expires_at=None,
            )
            .returning(InvestigationRun.id)
        )

        if updated.scalar_one_or_none() is None:
            raise InvestigationLeaseLostError(
                f"Cannot fail investigation {run_id}: "
                "worker does not own a valid lease"
            )

        db.add(
            AuditEvent(
                investigation_id=run_id,
                event_type="investigation_failed",
                details={"error_type": error_type},
            )
        )

        await db.commit()

    except BaseException:
        await db.rollback()
        raise





async def recover_expired_investigation(
    db: AsyncSession,
    *,
    run_id: int,
) -> bool:
    """Recover one expired, owned investigation.

    Returns True if recovery succeeded.
    Returns False if the run is active, already finalized,
    unowned, or does not exist.

    This function does not retry AI execution.
    """

    try:
        recovered = await db.execute(
            update(InvestigationRun)
            .where(
                InvestigationRun.id == run_id,
                InvestigationRun.status == "running",
                InvestigationRun.worker_id.is_not(None),
                InvestigationRun.lease_expires_at.is_not(None),
                InvestigationRun.lease_expires_at
                <= func.clock_timestamp(),
            )
            .values(
                status="failed",
                completed_at=func.clock_timestamp(),
                lease_expires_at=None,
            )
            .returning(InvestigationRun.id)
        )

        recovered_id = recovered.scalar_one_or_none()

        if recovered_id is None:
            await db.rollback()
            return False

        db.add(
            AuditEvent(
                investigation_id=recovered_id,
                event_type="investigation_recovered",
                details={
                    "reason": "worker_lease_expired",
                    "recovery_action": "marked_failed",
                },
            )
        )

        await db.commit()
        return True

    except BaseException:
        await db.rollback()
        raise
