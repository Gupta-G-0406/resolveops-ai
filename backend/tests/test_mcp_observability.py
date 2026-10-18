
import asyncio
import logging
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from app.core.logging_config import request_id_var
from app.mcp.observability import mcp_observed_tool


@pytest.mark.asyncio
async def test_observed_tool_success():
    fake_context = object()

    @mcp_observed_tool
    async def sample_tool(ctx):
        assert request_id_var.get() == "test-123"
        return {"found": True}

    with (
        patch(
            "app.mcp.observability.Context",
            object,
        ),
        patch(
            "app.mcp.observability.get_mcp_request_id",
            return_value="test-123",
        ),
    ):
        result = await sample_tool(ctx=fake_context)

    assert result == {"found": True}
    assert request_id_var.get() is None


@pytest.mark.asyncio
async def test_observed_tool_failure():
    @mcp_observed_tool
    async def failing_tool(ctx):
        assert request_id_var.get() == "test-error"
        raise RuntimeError("Test failure")

    with (
        patch(
            "app.mcp.observability.Context",
            object,
        ),
        patch(
            "app.mcp.observability.get_mcp_request_id",
            return_value="test-error",
        ),
    ):
        with pytest.raises(RuntimeError):
            await failing_tool(ctx=object())

    assert request_id_var.get() is None


@pytest.mark.asyncio
async def test_concurrent_request_isolation():
    @mcp_observed_tool
    async def concurrent_tool(ctx, expected_id):
        assert request_id_var.get() == expected_id

        await asyncio.sleep(0.01)

        assert request_id_var.get() == expected_id
        return expected_id

    def extract_request_id(ctx):
        return ctx.request_id

    with (
        patch(
            "app.mcp.observability.Context",
            object,
        ),
        patch(
            "app.mcp.observability.get_mcp_request_id",
            side_effect=extract_request_id,
        ),
    ):
        results = await asyncio.gather(
            concurrent_tool(
                ctx=SimpleNamespace(request_id="request-A"),
                expected_id="request-A",
            ),
            concurrent_tool(
                ctx=SimpleNamespace(request_id="request-B"),
                expected_id="request-B",
            ),
        )

    assert results == ["request-A", "request-B"]
    assert request_id_var.get() is None


def test_decorator_rejects_sync_function():
    with pytest.raises(TypeError):

        @mcp_observed_tool
        def sync_tool(ctx):
            return {}


def test_decorator_requires_context_parameter():
    with pytest.raises(ValueError):

        @mcp_observed_tool
        async def missing_context():
            return {}
