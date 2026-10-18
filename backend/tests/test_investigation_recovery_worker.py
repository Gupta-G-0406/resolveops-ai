
"""Unit tests for the automatic investigation recovery worker."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.workers import investigation_recovery_worker as worker


@pytest.mark.asyncio
async def test_recover_expired_batch_success(monkeypatch):
    """Recover only IDs returned by the candidate query."""

    db = MagicMock()
    db.execute = AsyncMock()

    query_result = MagicMock()
    query_result.scalars.return_value.all.return_value = [101, 102]
    db.execute.return_value = query_result

    # Async context manager for mocked database sessions.
    session = MagicMock()
    session.__aenter__ = AsyncMock(return_value=db)
    session.__aexit__ = AsyncMock(return_value=False)

    monkeypatch.setattr(
        worker,
        "AsyncSessionLocal",
        lambda: session,
    )

    recover_mock = AsyncMock(return_value=True)

    monkeypatch.setattr(
        worker,
        "recover_expired_investigation",
        recover_mock,
    )

    count = await worker.recover_expired_batch(batch_size=10)

    assert count == 2
    assert db.execute.await_count == 1
    assert recover_mock.await_count == 2

    recovered_ids = [
        call.kwargs["run_id"]
        for call in recover_mock.await_args_list
    ]

    assert recovered_ids == [101, 102]


@pytest.mark.asyncio
async def test_recover_expired_batch_continues_after_failure(
    monkeypatch,
):
    """One recovery failure must not block the next run."""

    db = MagicMock()
    db.execute = AsyncMock()

    query_result = MagicMock()
    query_result.scalars.return_value.all.return_value = [201, 202]
    db.execute.return_value = query_result

    session = MagicMock()
    session.__aenter__ = AsyncMock(return_value=db)
    session.__aexit__ = AsyncMock(return_value=False)

    monkeypatch.setattr(
        worker,
        "AsyncSessionLocal",
        lambda: session,
    )

    recover_mock = AsyncMock(
        side_effect=[RuntimeError("Temporary DB error"), True]
    )

    monkeypatch.setattr(
        worker,
        "recover_expired_investigation",
        recover_mock,
    )

    count = await worker.recover_expired_batch()

    assert count == 1
    assert recover_mock.await_count == 2


@pytest.mark.asyncio
async def test_recover_expired_batch_invalid_size():
    """Reject invalid batch sizes."""

    with pytest.raises(ValueError):
        await worker.recover_expired_batch(batch_size=0)

    with pytest.raises(ValueError):
        await worker.recover_expired_batch(batch_size=-1)
