
"""Tests for MCP queued request cancellation."""

import asyncio
from unittest.mock import patch

import pytest

from app.mcp.client_tools import PersistentMCPClient


@pytest.mark.asyncio
async def test_cancelled_mcp_call_marks_future_done():
    client = PersistentMCPClient()

    client._queue = asyncio.Queue()
    client._closed = False

    task = None

    with patch.object(
        type(client),
        "is_connected",
        new_callable=lambda: property(lambda self: True),
    ):
        task = asyncio.create_task(
            client.call_tool(
                "get_policy_readiness",
                {},
            )
        )

        request = await asyncio.wait_for(
            client._queue.get(),
            timeout=1,
        )

        task.cancel()

        with pytest.raises(asyncio.CancelledError):
            await task

        assert request.future.cancelled()
        assert request.future.done()
