
import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from app.mcp.client_tools import (
    MCPConnectionError,
    PersistentMCPClient,
)


@pytest.fixture
def client():
    instance = PersistentMCPClient()
    instance._reconnect_delay = 0.01
    instance._startup_timeout = 0.05
    return instance


@pytest.mark.asyncio
async def test_reconnect_after_session_ends(client):
    """
    Verify that the worker starts another connection
    after an established session ends.
    """

    calls = 0
    reconnected = asyncio.Event()

    async def fake_serve_connection():
        nonlocal calls

        calls += 1

        if calls == 1:
            # Simulate initial successful connection
            client._connected = True

            if client._ready and not client._ready.done():
                client._ready.set_result(None)

            # Simulate unexpected session termination
            return

        # Second connection attempt
        client._connected = True
        reconnected.set()
        client._closed = True

    client._queue = asyncio.Queue()
    client._ready = asyncio.get_running_loop().create_future()

    with patch.object(
        client,
        "_serve_connection",
        side_effect=fake_serve_connection,
    ):
        worker = asyncio.create_task(client._run())

        try:
            await asyncio.wait_for(
                reconnected.wait(),
                timeout=1,
            )
        finally:
            client._closed = True
            await asyncio.wait_for(worker, timeout=1)

    assert calls >= 2
    assert reconnected.is_set()
    assert client.metrics.reconnect_attempts == 1


@pytest.mark.asyncio
async def test_reconnect_after_connection_exception(client):
    """
    Verify recovery when an established connection fails.
    """

    calls = 0
    reconnected = asyncio.Event()

    async def fake_serve_connection():
        nonlocal calls
        calls += 1

        if calls == 1:
            client._connected = True

            if client._ready and not client._ready.done():
                client._ready.set_result(None)

            raise RuntimeError("Simulated connection loss")

        client._connected = True
        reconnected.set()
        client._closed = True

    client._queue = asyncio.Queue()
    client._ready = asyncio.get_running_loop().create_future()

    with patch.object(
        client,
        "_serve_connection",
        side_effect=fake_serve_connection,
    ):
        worker = asyncio.create_task(client._run())

        try:
            await asyncio.wait_for(
                reconnected.wait(),
                timeout=1,
            )
        finally:
            client._closed = True
            await asyncio.wait_for(worker, timeout=1)

    assert calls >= 2
    assert reconnected.is_set()
    assert client.metrics.reconnect_attempts == 1


@pytest.mark.asyncio
async def test_initial_connection_failure(client):
    """
    Initial startup failure must not retry forever.
    """

    client._queue = asyncio.Queue()
    client._ready = asyncio.get_running_loop().create_future()

    with patch.object(
        client,
        "_serve_connection",
        new_callable=AsyncMock,
        side_effect=RuntimeError("Startup failed"),
    ):
        await asyncio.wait_for(client._run(), timeout=1)

    with pytest.raises(
        MCPConnectionError,
        match="MCP startup failed",
    ):
        await client._ready

    assert client.is_connected is False


@pytest.mark.asyncio
async def test_startup_timeout(client):
    """
    connect() must stop the worker when startup times out.
    """

    async def never_connect():
        await asyncio.Event().wait()

    with patch.object(
        client,
        "_serve_connection",
        side_effect=never_connect,
    ):
        with pytest.raises(
            MCPConnectionError,
            match="MCP startup exceeded",
        ):
            await client.connect()

    assert client.is_connected is False
    assert client._closed is True
    assert client._queue is None
    assert client._ready is None
