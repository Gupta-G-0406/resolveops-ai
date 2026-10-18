
import asyncio
from unittest.mock import AsyncMock

import pytest

from app.mcp.client_tools import MCPMetrics


def test_metrics_initial_values():
    metrics = MCPMetrics()

    assert metrics.connection_successes == 0
    assert metrics.reconnect_attempts == 0
    assert metrics.heartbeat_successes == 0
    assert metrics.heartbeat_failures == 0
    assert metrics.tool_calls == 0
    assert metrics.tool_successes == 0
    assert metrics.tool_failures == 0
    assert metrics.last_tool_duration_seconds is None
    assert metrics.last_heartbeat_at is None


@pytest.mark.asyncio
async def test_successful_heartbeat():
    metrics = MCPMetrics()
    session = AsyncMock()

    await asyncio.wait_for(
        session.send_ping(),
        timeout=5,
    )

    metrics.heartbeat_successes += 1

    assert metrics.heartbeat_successes == 1
    assert metrics.heartbeat_failures == 0
    session.send_ping.assert_awaited_once()


@pytest.mark.asyncio
async def test_failed_heartbeat():
    metrics = MCPMetrics()
    session = AsyncMock()
    session.send_ping.side_effect = RuntimeError(
        "MCP heartbeat failed"
    )

    try:
        await asyncio.wait_for(
            session.send_ping(),
            timeout=5,
        )
    except Exception:
        metrics.heartbeat_failures += 1

    assert metrics.heartbeat_successes == 0
    assert metrics.heartbeat_failures == 1
