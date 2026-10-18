
"""Tests for MCP health and policy readiness."""

from unittest.mock import AsyncMock, patch

import pytest

from app.main import mcp_health

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from app.main import mcp_health

@pytest.mark.asyncio
@pytest.mark.parametrize(
    "status, ready",
    [
        ("warming", False),
        ("ready", True),
        ("failed", False),
    ],
)
async def test_mcp_health_policy_states(status, ready):
    policy_state = {
        "status": status,
        "ready": ready,
        "error": None,
    }

    with (
        patch("app.main.mcp_client") as mock_client,
    ):
        mock_client.is_connected = True
        mock_client.call_tool = AsyncMock(
            return_value=policy_state
        )

        result = await mcp_health()

    assert result["connected"] is True
    assert result["policy"] == policy_state


@pytest.mark.asyncio
async def test_mcp_health_disconnected():
    with patch("app.main.mcp_client") as mock_client:
        mock_client.is_connected = False

        result = await mcp_health()

        mock_client.call_tool.assert_not_called()

    assert result["connected"] is False
    assert result["policy"]["ready"] is False


@pytest.mark.asyncio
async def test_mcp_health_tool_failure():
    with patch("app.main.mcp_client") as mock_client:
        mock_client.is_connected = True
        mock_client.call_tool = AsyncMock(
            side_effect=RuntimeError("MCP tool unavailable")
        )

        result = await mcp_health()

    assert result["connected"] is True
    assert result["policy"]["status"] == "unavailable"
    assert result["policy"]["ready"] is False



@pytest.mark.asyncio
async def test_mcp_health_timeout():
    async def slow_readiness(*args, **kwargs):
        await asyncio.sleep(0.1)

    with (
        patch("app.main.mcp_client") as mock_client,
        patch(
            "app.main.MCP_HEALTH_TIMEOUT_SECONDS",
            0.01,
        ),
    ):
        mock_client.is_connected = True
        mock_client.call_tool = AsyncMock(
            side_effect=slow_readiness
        )

        result = await mcp_health()

    assert result["connected"] is True
    assert result["policy"]["status"] == "unavailable"
    assert result["policy"]["ready"] is False


@pytest.mark.asyncio
async def test_mcp_health_fast_response():
    policy_state = {
        "status": "ready",
        "ready": True,
        "error": None,
    }

    with patch("app.main.mcp_client") as mock_client:
        mock_client.is_connected = True
        mock_client.call_tool = AsyncMock(
            return_value=policy_state
        )

        result = await mcp_health()

    assert result["policy"] == policy_state
