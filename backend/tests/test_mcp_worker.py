
import asyncio
from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.mcp.client_tools import (
    MCPConnectionError,
    MCPToolError,
    PersistentMCPClient,
    ToolRequest,
)

from app.core.logging_config import request_id_var
# =========================================================
# Fake MCP transport
# =========================================================

@asynccontextmanager
async def fake_stdio_client(params):
    """Avoid starting a real MCP subprocess."""
    yield (object(), object())


@asynccontextmanager
async def fake_client_session(*args, **kwargs):
    """Provide the mocked MCP session."""
    yield fake_client_session.session


# =========================================================
# Fixtures
# =========================================================


@pytest.fixture
def client():
    instance = PersistentMCPClient()

    # Fast intervals for testing
    instance._heartbeat_interval = 0.01
    instance._heartbeat_timeout = 0.1
    instance._tool_timeout = 0.5

    # Initialize queue explicitly because tests
    # call _serve_connection() without connect().
    instance._queue = asyncio.Queue()

    return instance


@pytest.fixture
def session():
    mock_session = SimpleNamespace(
        initialize=AsyncMock(),
        send_ping=AsyncMock(),
        call_tool=AsyncMock(),
    )

    fake_client_session.session = mock_session

    return mock_session


# =========================================================
# Test helper
# =========================================================


async def run_worker(
    client,
    session,
    *,
    wait=0.05,
    result_future=None,
):
    loop = asyncio.get_running_loop()
    client._ready = loop.create_future()

    with (
        patch(
            "app.mcp.client_tools.stdio_client",
            fake_stdio_client,
        ),
        patch(
            "app.mcp.client_tools.ClientSession",
            fake_client_session,
        ),
    ):
        worker = asyncio.create_task(
            client._serve_connection()
        )

        try:
            await asyncio.wait_for(
                asyncio.shield(client._ready),
                timeout=1,
            )

            if result_future is not None:
                # Wait until the worker resolves the future.
                # Do not propagate its exception here.
                done, _ = await asyncio.wait(
                    [result_future],
                    timeout=1,
                )

                assert result_future in done, (
                    "MCP tool result timed out"
                )

            else:
                await asyncio.sleep(wait)

        finally:
            client._closed = True

            try:
                await asyncio.wait_for(
                    worker,
                    timeout=1,
                )
            except asyncio.TimeoutError:
                worker.cancel()
                await asyncio.gather(
                    worker,
                    return_exceptions=True,
                )

# =========================================================
# Test 1: Successful heartbeat
# =========================================================

@pytest.mark.asyncio
async def test_worker_successful_heartbeat(
    client,
    session,
):
    await run_worker(
        client,
        session,
        wait=0.05,
    )

    assert client.metrics.connection_successes == 1

    assert client.metrics.heartbeat_successes >= 1

    assert client.metrics.heartbeat_failures == 0

    assert client.metrics.last_heartbeat_at is not None

    assert session.send_ping.await_count >= 1


# =========================================================
# Test 2: Failed heartbeat
# =========================================================

@pytest.mark.asyncio
async def test_worker_failed_heartbeat(
    client,
    session,
):
    session.send_ping.side_effect = RuntimeError(
        "Simulated heartbeat failure"
    )

    await run_worker(
        client,
        session,
        wait=0.05,
    )
    assert client.metrics.heartbeat_successes == 0
    assert client.metrics.heartbeat_failures == 1
    assert client.is_connected is False

    session.send_ping.assert_awaited_once()


# =========================================================
# Test 3: Successful MCP tool execution
# =========================================================

@pytest.mark.asyncio
async def test_worker_successful_tool_call(
    client,
    session,
):
    session.call_tool.return_value = SimpleNamespace(
        isError=False,
        structuredContent={"status": "ok"},
        content=[],
    )

    loop = asyncio.get_running_loop()
    future = loop.create_future()

    await client._queue.put(
        ToolRequest(
            name="get_order",
            arguments={
                "order_number": "ORD-001"
            },
            future=future,
        )
    )

    await run_worker(
        client,
        session,
        result_future=future,
    )

    assert future.result() == {
        "status": "ok"
    }

    assert client.metrics.tool_calls == 1

    assert client.metrics.tool_successes == 1

    assert client.metrics.tool_failures == 0

    assert (
        client.metrics.last_tool_duration_seconds
        is not None
    )

    session.call_tool.assert_awaited_once_with(
        "get_order",
        arguments={
            "order_number": "ORD-001"
        },
        meta=None,
    )


# =========================================================
# Test 4: Failed MCP tool execution
# =========================================================

@pytest.mark.asyncio
async def test_worker_failed_tool_call(
    client,
    session,
):
    session.call_tool.return_value = SimpleNamespace(
        isError=True,
        structuredContent=None,
        content=[
            "Simulated tool failure"
        ],
    )

    loop = asyncio.get_running_loop()
    future = loop.create_future()

    await client._queue.put(
        ToolRequest(
            name="get_order",
            arguments={
                "order_number": "INVALID"
            },
            future=future,
        )
    )

    # An MCPToolError is expected from this future.

    await run_worker(
        client,
        session,
        result_future=future,
    )

    with pytest.raises(MCPToolError):
        await future


    assert future.done()

    assert isinstance(
        future.exception(),
        MCPToolError,
    )

    assert client.metrics.tool_calls == 1

    assert client.metrics.tool_successes == 0

    assert client.metrics.tool_failures == 1

    session.call_tool.assert_awaited_once_with(
        "get_order",
        arguments={
            "order_number": "INVALID"
        },
        meta=None,
    )





@pytest.mark.asyncio
async def test_worker_preserves_request_ids(client, session):
    """Each MCP tool call must use its own request ID."""

    captured_ids = []

    async def fake_call_tool(name, arguments, *, meta=None):
        current_request_id = request_id_var.get()
        captured_ids.append(current_request_id)
        assert meta == {
            "request_id": current_request_id
        }
        return SimpleNamespace(
            isError=False,
            structuredContent={"status": "ok"},
            content=[],
        )

    session.call_tool.side_effect = fake_call_tool

    loop = asyncio.get_running_loop()

    first_future = loop.create_future()
    second_future = loop.create_future()

    await client._queue.put(
        ToolRequest(
            name="get_order",
            arguments={"order_number": "ORD-A"},
            future=first_future,
            request_id="request-A",
        )
    )

    await client._queue.put(
        ToolRequest(
            name="get_order",
            arguments={"order_number": "ORD-B"},
            future=second_future,
            request_id="request-B",
        )
    )

    await run_worker(
        client,
        session,
        result_future=second_future,
    )

    assert first_future.result() == {"status": "ok"}
    assert second_future.result() == {"status": "ok"}

    assert captured_ids == ["request-A", "request-B"]

    assert client.metrics.tool_calls == 2
    assert client.metrics.tool_successes == 2
    assert client.metrics.tool_failures == 0















@pytest.mark.asyncio
async def test_worker_tool_timeout(client, session):
    """Verify timeout handling for an unresponsive MCP tool."""

    async def hanging_tool(*args, **kwargs):
        await asyncio.Event().wait()

    session.call_tool.side_effect = hanging_tool
    client._tool_timeout = 0.02

    loop = asyncio.get_running_loop()
    future = loop.create_future()

    await client._queue.put(
        ToolRequest(
            name="get_order",
            arguments={"order_number": "ORD-TIMEOUT"},
            future=future,
            request_id="timeout-request",
        )
    )

    await run_worker(
        client,
        session,
        result_future=future,
    )

    with pytest.raises(MCPConnectionError):
        await future

    assert client.metrics.tool_calls == 1
    assert client.metrics.tool_successes == 0
    assert client.metrics.tool_failures == 1
    assert client.is_connected is False
    assert client.metrics.last_tool_duration_seconds is not None

    session.call_tool.assert_awaited_once()



@pytest.mark.asyncio
async def test_worker_resets_request_id_after_tool_failure(
    client,
    session,
):
    captured_ids = []

    async def fake_call_tool(name, arguments, *, meta=None):
        current_request_id = request_id_var.get()
        captured_ids.append(current_request_id)
        assert meta == {
            "request_id": current_request_id
        }

        if arguments["order_number"] == "INVALID":
            return SimpleNamespace(
                isError=True,
                structuredContent=None,
                content=["Simulated tool failure"],
            )

        return SimpleNamespace(
            isError=False,
            structuredContent={"status": "ok"},
            content=[],
        )

    session.call_tool.side_effect = fake_call_tool

    loop = asyncio.get_running_loop()
    failed_future = loop.create_future()
    successful_future = loop.create_future()

    await client._queue.put(
        ToolRequest(
            name="get_order",
            arguments={"order_number": "INVALID"},
            future=failed_future,
            request_id="request-A",
        )
    )

    await client._queue.put(
        ToolRequest(
            name="get_order",
            arguments={"order_number": "ORD-B"},
            future=successful_future,
            request_id="request-B",
        )
    )

    await run_worker(
        client,
        session,
        result_future=successful_future,
    )

    with pytest.raises(MCPToolError):
        await failed_future

    assert successful_future.result() == {"status": "ok"}
    assert captured_ids == ["request-A", "request-B"]

    assert client.metrics.tool_calls == 2
    assert client.metrics.tool_failures == 1
    assert client.metrics.tool_successes == 1

    # The worker task has finished; its request context
    # must not affect this test's context.
    assert request_id_var.get() is None
