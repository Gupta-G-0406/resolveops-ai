
"""Tests for MCP policy readiness recovery."""

import pytest

from app.mcp import server


def reset_policy_state():
    with server._policy_state_lock:
        server._policy_state.update(
            {
                "status": "not_started",
                "ready": False,
                "error": None,
            }
        )


@pytest.fixture(autouse=True)
def isolated_policy_state():
    """Keep readiness tests independent."""

    with server._policy_state_lock:
        original = dict(server._policy_state)

    reset_policy_state()

    yield

    with server._policy_state_lock:
        server._policy_state.clear()
        server._policy_state.update(original)


def test_failed_to_ready_recovery():
    server.update_policy_state(
        "warming",
        source="warmup",
    )

    server.update_policy_state(
        "failed",
        source="warmup",
    )

    assert server._policy_state["status"] == "failed"
    assert server._policy_state["ready"] is False

    # Successful runtime operation recovers readiness.
    server.update_policy_state("ready")

    assert server._policy_state["status"] == "ready"
    assert server._policy_state["ready"] is True


def test_stale_warmup_failure_does_not_override_ready():
    server.update_policy_state(
        "warming",
        source="warmup",
    )

    server.update_policy_state("ready")

    # A delayed warmup failure must be ignored.
    server.update_policy_state(
        "failed",
        source="warmup",
    )

    assert server._policy_state["status"] == "ready"
    assert server._policy_state["ready"] is True


def test_warming_does_not_override_ready():
    server.update_policy_state("ready")

    # A stale warmup status must not overwrite ready.
    server.update_policy_state(
        "warming",
        source="warmup",
    )

    assert server._policy_state["status"] == "ready"
    assert server._policy_state["ready"] is True
