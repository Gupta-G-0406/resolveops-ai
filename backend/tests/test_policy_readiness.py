
import asyncio

from app.mcp.server import (
    get_policy_readiness,
    update_policy_state,
)


def test_policy_state_transitions():
    update_policy_state("warming")
    state = asyncio.run(get_policy_readiness())

    assert state["status"] == "warming"
    assert state["ready"] is False

    update_policy_state("ready")
    state = asyncio.run(get_policy_readiness())

    assert state["status"] == "ready"
    assert state["ready"] is True

    update_policy_state("failed")
    state = asyncio.run(get_policy_readiness())

    assert state["status"] == "failed"
    assert state["ready"] is False
