
"""Tests for policy-search readiness recovery."""

from unittest.mock import patch

import pytest

from app.mcp import server


@pytest.fixture(autouse=True)
def isolated_policy_state():
    with server._policy_state_lock:
        original = dict(server._policy_state)
        server._policy_state.update(
            {
                "status": "not_started",
                "ready": False,
                "error": None,
            }
        )

    yield

    with server._policy_state_lock:
        server._policy_state.clear()
        server._policy_state.update(original)


@pytest.mark.asyncio
async def test_successful_policy_search_recovers_readiness():
    server.update_policy_state(
        "failed",
        source="warmup",
    )

    mock_matches = [
        {
            "policy_id": "POL-REFUND-001",
            "title": "Refund Policy",
            "category": "refund",
            "content": "Refund eligibility rules",
            "distance": 0.1,
        }
    ]

    with patch(
        "app.mcp.server.search_policies",
        return_value=mock_matches,
    ):
        result = await server.execute_policy_search(
            query="refund eligibility",
            limit=3,
        )

    assert result["found"] is True
    assert result["policies"] == mock_matches

    assert server._policy_state["status"] == "ready"
    assert server._policy_state["ready"] is True


@pytest.mark.asyncio
async def test_failed_policy_search_does_not_recover_readiness():
    server.update_policy_state(
        "failed",
        source="warmup",
    )

    with patch(
        "app.mcp.server.search_policies",
        side_effect=RuntimeError("Simulated search failure"),
    ):
        with pytest.raises(
            RuntimeError,
            match="Simulated search failure",
        ):
            await server.execute_policy_search(
                query="refund eligibility",
                limit=3,
            )

    assert server._policy_state["status"] == "failed"
    assert server._policy_state["ready"] is False
