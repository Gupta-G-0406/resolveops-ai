
"""Unit tests for investigation worker lease operations."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.investigation_repository import (
    acquire_investigation_lease,
    renew_investigation_lease,
)


def make_mock_db(returned_id):
    db = AsyncMock()

    result = MagicMock()
    result.scalar_one_or_none.return_value = returned_id

    db.execute.return_value = result

    return db


@pytest.mark.asyncio
async def test_acquire_lease_success():
    db = make_mock_db(17)

    acquired = await acquire_investigation_lease(
        db,
        run_id=17,
        worker_id="worker-abc",
    )

    assert acquired is True
    db.execute.assert_awaited_once()
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_acquire_lease_rejected():
    db = make_mock_db(None)

    acquired = await acquire_investigation_lease(
        db,
        run_id=17,
        worker_id="worker-xyz",
    )

    assert acquired is False


@pytest.mark.asyncio
async def test_renew_lease_success():
    db = make_mock_db(17)

    renewed = await renew_investigation_lease(
        db,
        run_id=17,
        worker_id="worker-abc",
    )

    assert renewed is True
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_renew_lease_rejected():
    db = make_mock_db(None)

    renewed = await renew_investigation_lease(
        db,
        run_id=17,
        worker_id="wrong-worker",
    )

    assert renewed is False


@pytest.mark.asyncio
async def test_invalid_lease_duration():
    db = make_mock_db(17)

    with pytest.raises(ValueError):
        await acquire_investigation_lease(
            db,
            run_id=17,
            worker_id="worker-abc",
            lease_seconds=0,
        )

    db.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_empty_worker_id():
    db = make_mock_db(17)

    with pytest.raises(ValueError):
        await renew_investigation_lease(
            db,
            run_id=17,
            worker_id=" ",
        )

    db.execute.assert_not_awaited()
