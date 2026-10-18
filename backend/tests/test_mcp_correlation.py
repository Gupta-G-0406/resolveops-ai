
import asyncio

import pytest

from app.core.logging_config import request_id_var
from app.mcp.client_tools import (
    PersistentMCPClient,
    ToolRequest,
)


@pytest.mark.asyncio
async def test_call_tool_captures_request_id():
    client = PersistentMCPClient()
    client._queue = asyncio.Queue()
    client._closed = False
    client._connected = True
    client._request_timeout = 1

    token = request_id_var.set("investigation-123")

    try:
        task = asyncio.create_task(
            client.call_tool(
                "get_order",
                {"order_number": "ORD-001"},
            )
        )

        request = await asyncio.wait_for(
            client._queue.get(),
            timeout=1,
        )

        assert request.request_id == "investigation-123"

        request.future.set_result({"status": "ok"})

        result = await asyncio.wait_for(task, timeout=1)
        assert result == {"status": "ok"}

    finally:
        request_id_var.reset(token)


@pytest.mark.asyncio
async def test_tool_request_backward_compatibility():
    loop = asyncio.get_running_loop()

    request = ToolRequest(
        name="get_order",
        arguments={"order_number": "ORD-001"},
        future=loop.create_future(),
    )

    assert request.request_id is None


@pytest.mark.asyncio
async def test_concurrent_requests_have_separate_ids():
    client = PersistentMCPClient()
    client._queue = asyncio.Queue()
    client._closed = False
    client._connected = True
    client._request_timeout = 1

    async def submit_request(request_id, order_number):
        token = request_id_var.set(request_id)

        try:
            return await client.call_tool(
                "get_order",
                {"order_number": order_number},
            )
        finally:
            request_id_var.reset(token)

    tasks = [
        asyncio.create_task(
            submit_request("request-A", "ORD-A")
        ),
        asyncio.create_task(
            submit_request("request-B", "ORD-B")
        ),
    ]

    requests = [
        await asyncio.wait_for(client._queue.get(), timeout=1)
        for _ in range(2)
    ]

    captured = {
        request.arguments["order_number"]: request.request_id
        for request in requests
    }

    assert captured == {
        "ORD-A": "request-A",
        "ORD-B": "request-B",
    }

    for request in requests:
        request.future.set_result({"status": "ok"})

    results = await asyncio.gather(*tasks)

    assert results == [
        {"status": "ok"},
        {"status": "ok"},
    ]
