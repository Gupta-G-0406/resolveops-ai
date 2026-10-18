
"""Real PostgreSQL integration tests for investigation leases.

Run only against a disposable/local development database.
"""

import asyncio
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import delete, select

from app.db.session import AsyncSessionLocal, engine
from app.models.investigation import InvestigationRun, AuditEvent
from app.services import investigation_repository


@pytest_asyncio.fixture(autouse=True)
async def dispose_engine_after_test():
    """Prevent asyncpg connections leaking across pytest event loops."""
    try:
        yield
    finally:
        await engine.dispose()


@pytest.fixture
def test_run_id():
    """Unique worker identity for this test execution."""
    return f"lease-test-{uuid4().hex}"

async def create_temporary_run(worker_tag: str) -> int:
    async with AsyncSessionLocal() as db:
        run = InvestigationRun(
            ticket_id=2,
            order_number="TEST-LEASE-001",
            status="running",
        )

        db.add(run)
        await db.commit()
        await db.refresh(run)

        return run.id


async def cleanup_temporary_run(run_id: int) -> None:
    async with AsyncSessionLocal() as db:
        await db.execute(
            delete(AuditEvent).where(
                AuditEvent.investigation_id == run_id
            )
        )

        await db.execute(
            delete(InvestigationRun).where(
                InvestigationRun.id == run_id
            )
        )

        await db.commit()


@pytest.mark.asyncio
async def test_real_postgres_lease_lifecycle(test_run_id):
    run_id = await create_temporary_run(test_run_id)

    worker_a = f"{test_run_id}-a"
    worker_b = f"{test_run_id}-b"

    try:
        # 1. Worker A acquires ownership.
        async with AsyncSessionLocal() as db:
            acquired = await (
                investigation_repository.acquire_investigation_lease(
                    db,
                    run_id=run_id,
                    worker_id=worker_a,
                    lease_seconds=10,
                )
            )

        assert acquired is True

        # 2. Worker B cannot acquire the same run.
        async with AsyncSessionLocal() as db:
            rejected = await (
                investigation_repository.acquire_investigation_lease(
                    db,
                    run_id=run_id,
                    worker_id=worker_b,
                    lease_seconds=10,
                )
            )

        assert rejected is False

        # 3. Capture initial lease expiry.
        async with AsyncSessionLocal() as db:
            run = await db.get(InvestigationRun, run_id)

            assert run.worker_id == worker_a
            assert run.heartbeat_at is not None
            assert run.lease_expires_at is not None

            first_expiry = run.lease_expires_at
            first_heartbeat = run.heartbeat_at

        await asyncio.sleep(0.1)

        # 4. Worker A renews lease.
        async with AsyncSessionLocal() as db:
            renewed = await (
                investigation_repository.renew_investigation_lease(
                    db,
                    run_id=run_id,
                    worker_id=worker_a,
                    lease_seconds=10,
                )
            )

        assert renewed is True

        # 5. Worker B cannot renew Worker A's lease.
        async with AsyncSessionLocal() as db:
            rejected_renewal = await (
                investigation_repository.renew_investigation_lease(
                    db,
                    run_id=run_id,
                    worker_id=worker_b,
                    lease_seconds=10,
                )
            )

        assert rejected_renewal is False

        # 6. Verify heartbeat and expiry advanced.
        async with AsyncSessionLocal() as db:
            run = await db.get(InvestigationRun, run_id)

            assert run.heartbeat_at > first_heartbeat
            assert run.lease_expires_at > first_expiry

        # 7. Finalize as the valid owner.
        result = {
            "status": "completed",
            "report": "Lease integration test completed",
            "selected_agents": ["test"],
            "policy_ids": [],
            "verification": {"status": "passed"},
        }

        async with AsyncSessionLocal() as db:
            await investigation_repository.complete_run_owned(
                db,
                run_id=run_id,
                worker_id=worker_a,
                result=result,
                evidence={"test": True},
            )

        # 8. Verify final state.
        async with AsyncSessionLocal() as db:
            run = await db.get(InvestigationRun, run_id)

            assert run.status == "completed"
            assert run.completed_at is not None
            assert run.lease_expires_at is None
            assert run.worker_id == worker_a

            events = await db.execute(
                select(AuditEvent).where(
                    AuditEvent.investigation_id == run_id
                )
            )

            audit_events = list(events.scalars().all())

            assert len(audit_events) == 1
            assert audit_events[0].event_type == (
                "investigation_completed"
            )

    finally:
        await cleanup_temporary_run(run_id)



@pytest.mark.asyncio
async def test_expired_worker_cannot_complete():
    run_id = await create_temporary_run("expired-completion")
    worker_id = f"expired-worker-{uuid4().hex}"

    try:
        async with AsyncSessionLocal() as db:
            acquired = await (
                investigation_repository.acquire_investigation_lease(
                    db,
                    run_id=run_id,
                    worker_id=worker_id,
                    lease_seconds=1,
                )
            )

        assert acquired is True

        # Allow the real PostgreSQL lease to expire.
        await asyncio.sleep(1.5)

        result = {
            "status": "completed",
            "report": "This must not be saved",
            "selected_agents": ["test"],
            "policy_ids": [],
            "verification": {"status": "passed"},
        }

        with pytest.raises(
            investigation_repository.InvestigationLeaseLostError
        ):
            async with AsyncSessionLocal() as db:
                await investigation_repository.complete_run_owned(
                    db,
                    run_id=run_id,
                    worker_id=worker_id,
                    result=result,
                    evidence={"test": True},
                )

        async with AsyncSessionLocal() as db:
            run = await db.get(InvestigationRun, run_id)

            assert run.status == "running"
            assert run.completed_at is None
            assert run.report is None

            events = await db.execute(
                select(AuditEvent).where(
                    AuditEvent.investigation_id == run_id
                )
            )

            assert events.scalars().all() == []

    finally:
        await cleanup_temporary_run(run_id)


@pytest.mark.asyncio
async def test_expired_worker_cannot_fail():
    run_id = await create_temporary_run("expired-failure")
    worker_id = f"expired-worker-{uuid4().hex}"

    try:
        async with AsyncSessionLocal() as db:
            acquired = await (
                investigation_repository.acquire_investigation_lease(
                    db,
                    run_id=run_id,
                    worker_id=worker_id,
                    lease_seconds=1,
                )
            )

        assert acquired is True

        await asyncio.sleep(1.5)

        with pytest.raises(
            investigation_repository.InvestigationLeaseLostError
        ):
            async with AsyncSessionLocal() as db:
                await investigation_repository.fail_run_owned(
                    db,
                    run_id=run_id,
                    worker_id=worker_id,
                    error_type="SimulatedError",
                )

        async with AsyncSessionLocal() as db:
            run = await db.get(InvestigationRun, run_id)

            assert run.status == "running"
            assert run.completed_at is None

            events = await db.execute(
                select(AuditEvent).where(
                    AuditEvent.investigation_id == run_id
                )
            )

            assert events.scalars().all() == []

    finally:
        await cleanup_temporary_run(run_id)




@pytest.mark.asyncio
async def test_concurrent_workers_only_one_acquires_lease():
    run_id = await create_temporary_run("concurrent-acquire")

    worker_a = f"worker-a-{uuid4().hex}"
    worker_b = f"worker-b-{uuid4().hex}"

    async def try_acquire(worker_id: str) -> bool:
        async with AsyncSessionLocal() as db:
            return await investigation_repository.acquire_investigation_lease(
                db,
                run_id=run_id,
                worker_id=worker_id,
                lease_seconds=30,
            )

    try:
        # Start both attempts concurrently.
        results = await asyncio.gather(
            try_acquire(worker_a),
            try_acquire(worker_b),
        )

        # Exactly one worker must acquire ownership.
        assert sorted(results) == [False, True]

        winning_worker = worker_a if results[0] else worker_b

        async with AsyncSessionLocal() as db:
            run = await db.get(InvestigationRun, run_id)

            assert run.status == "running"
            assert run.worker_id == winning_worker
            assert run.heartbeat_at is not None
            assert run.lease_expires_at is not None

    finally:
        await cleanup_temporary_run(run_id)


@pytest.mark.asyncio
async def test_recover_expired_investigation():
    run_id = await create_temporary_run("recovery-test")
    worker_id = f"recovery-worker-{uuid4().hex}"

    try:
        # Acquire a short lease.
        async with AsyncSessionLocal() as db:
            acquired = await (
                investigation_repository.acquire_investigation_lease(
                    db,
                    run_id=run_id,
                    worker_id=worker_id,
                    lease_seconds=1,
                )
            )

        assert acquired is True

        # An active lease must not be recovered.
        async with AsyncSessionLocal() as db:
            recovered = await (
                investigation_repository.recover_expired_investigation(
                    db,
                    run_id=run_id,
                )
            )

        assert recovered is False

        # Allow the lease to expire.
        await asyncio.sleep(1.5)

        # Recover the expired investigation.
        async with AsyncSessionLocal() as db:
            recovered = await (
                investigation_repository.recover_expired_investigation(
                    db,
                    run_id=run_id,
                )
            )

        assert recovered is True

        # Verify final database state.
        async with AsyncSessionLocal() as db:
            run = await db.get(InvestigationRun, run_id)

            assert run.status == "failed"
            assert run.completed_at is not None
            assert run.lease_expires_at is None

            events = await db.execute(
                select(AuditEvent).where(
                    AuditEvent.investigation_id == run_id
                )
            )

            audit_events = list(events.scalars().all())

            assert len(audit_events) == 1
            assert audit_events[0].event_type == (
                "investigation_recovered"
            )

        # Recovery must be idempotent.
        async with AsyncSessionLocal() as db:
            recovered_again = await (
                investigation_repository.recover_expired_investigation(
                    db,
                    run_id=run_id,
                )
            )

        assert recovered_again is False

    finally:
        await cleanup_temporary_run(run_id)




@pytest.mark.asyncio
async def test_real_postgres_periodic_heartbeat():
    """Verify that a long-running investigation renews its lease."""

    from app.services.investigation_heartbeat import run_with_heartbeat

    run_id = await create_temporary_run("periodic-heartbeat")
    worker_id = f"heartbeat-worker-{uuid4().hex}"

    try:
        # Step 1: Acquire initial lease.
        async with AsyncSessionLocal() as db:
            acquired = await (
                investigation_repository.acquire_investigation_lease(
                    db,
                    run_id=run_id,
                    worker_id=worker_id,
                    lease_seconds=3,
                )
            )

        assert acquired is True

        # Step 2: Capture initial heartbeat.
        async with AsyncSessionLocal() as db:
            run = await db.get(InvestigationRun, run_id)
            initial_heartbeat = run.heartbeat_at

        # Step 3: Simulate long-running investigation.
        async def slow_investigation():
            await asyncio.sleep(4)
            return {"status": "completed"}

        # Step 4: Heartbeat renews lease during execution.
        result = await run_with_heartbeat(
            slow_investigation(),
            run_id=run_id,
            worker_id=worker_id,
            interval_seconds=0.5,
            lease_seconds=3,
        )

        assert result["status"] == "completed"

        # Step 5: Verify lease renewal in PostgreSQL.
        async with AsyncSessionLocal() as db:
            run = await db.get(InvestigationRun, run_id)

            assert run.worker_id == worker_id
            assert run.status == "running"
            assert run.heartbeat_at > initial_heartbeat
            assert run.lease_expires_at is not None

    finally:
        await cleanup_temporary_run(run_id)



@pytest.mark.asyncio
async def test_heartbeat_and_recovery_concurrency():
    """Active leases are protected; expired runs recover once."""

    run_id = await create_temporary_run(
        "heartbeat-recovery-race"
    )
    worker_id = f"worker-{uuid4().hex}"

    async def renew_lease():
        async with AsyncSessionLocal() as db:
            return await (
                investigation_repository.renew_investigation_lease(
                    db,
                    run_id=run_id,
                    worker_id=worker_id,
                    lease_seconds=3,
                )
            )

    async def recover_run():
        async with AsyncSessionLocal() as db:
            return await (
                investigation_repository.recover_expired_investigation(
                    db,
                    run_id=run_id,
                )
            )

    try:
        # 1. Acquire initial ownership.
        async with AsyncSessionLocal() as db:
            acquired = await (
                investigation_repository.acquire_investigation_lease(
                    db,
                    run_id=run_id,
                    worker_id=worker_id,
                    lease_seconds=3,
                )
            )

        assert acquired is True

        # 2. Run heartbeat and recovery concurrently
        # while the lease is still active.
        renewed, recovered = await asyncio.gather(
            renew_lease(),
            recover_run(),
        )

        assert renewed is True
        assert recovered is False

        async with AsyncSessionLocal() as db:
            run = await db.get(InvestigationRun, run_id)
            assert run.status == "running"
            assert run.worker_id == worker_id

        # 3. Allow the renewed lease to expire.
        await asyncio.sleep(3.5)

        # 4. Two recovery attempts compete.
        results = await asyncio.gather(
            recover_run(),
            recover_run(),
        )

        assert sorted(results) == [False, True]

        # 5. Verify only one recovery audit event.
        async with AsyncSessionLocal() as db:
            run = await db.get(InvestigationRun, run_id)

            assert run.status == "failed"
            assert run.lease_expires_at is None

            events = await db.execute(
                select(AuditEvent).where(
                    AuditEvent.investigation_id == run_id,
                    AuditEvent.event_type == "investigation_recovered",
                )
            )

            assert len(events.scalars().all()) == 1

        # 6. Old worker must not renew after recovery.
        assert await renew_lease() is False

    finally:
        await cleanup_temporary_run(run_id)




@pytest.mark.asyncio
async def test_automatic_recovery_worker_recovers_expired_run():
    """Verify the scheduled worker recovers an expired lease."""

    from app.workers.investigation_recovery_worker import (
        run_recovery_worker,
    )

    run_id = await create_temporary_run(
        "automatic-recovery-test"
    )

    worker_id = f"crashed-worker-{uuid4().hex}"

    recovery_task = None

    try:
        # 1. Simulate an investigation worker acquiring a lease.
        async with AsyncSessionLocal() as db:
            acquired = await (
                investigation_repository.acquire_investigation_lease(
                    db,
                    run_id=run_id,
                    worker_id=worker_id,
                    lease_seconds=1,
                )
            )

        assert acquired is True

        # 2. Start the actual periodic recovery worker.
        # Use a short interval for integration testing.
        recovery_task = asyncio.create_task(
            run_recovery_worker(interval_seconds=0.2)
        )

        # 3. Poll the database until recovery happens.
        # This avoids depending on an exact scheduler tick.
        recovered = False

        for _ in range(30):
            await asyncio.sleep(0.2)

            async with AsyncSessionLocal() as db:
                run = await db.get(InvestigationRun, run_id)

                if run.status == "failed":
                    recovered = True
                    break

        assert recovered is True, (
            "Recovery worker did not recover expired run "
            "within the test timeout"
        )

        # 4. Verify final state and audit event.
        async with AsyncSessionLocal() as db:
            run = await db.get(InvestigationRun, run_id)

            assert run.status == "failed"
            assert run.completed_at is not None
            assert run.lease_expires_at is None

            events = await db.execute(
                select(AuditEvent).where(
                    AuditEvent.investigation_id == run_id,
                    AuditEvent.event_type == "investigation_recovered",
                )
            )

            assert len(events.scalars().all()) == 1

        # 5. Old worker cannot renew after recovery.
        async with AsyncSessionLocal() as db:
            renewed = await (
                investigation_repository.renew_investigation_lease(
                    db,
                    run_id=run_id,
                    worker_id=worker_id,
                    lease_seconds=10,
                )
            )

        assert renewed is False

    finally:
        # Always stop the background worker before cleanup.
        if recovery_task is not None:
            recovery_task.cancel()

            try:
                await recovery_task
            except asyncio.CancelledError:
                pass

        await cleanup_temporary_run(run_id)
