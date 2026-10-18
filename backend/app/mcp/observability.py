
import functools
import inspect
import logging
import time
from typing import Any, Callable, TypeVar

from mcp.server.fastmcp import Context

from app.core.logging_config import request_id_var
from app.mcp.correlation import get_mcp_request_id


logger = logging.getLogger("resolveops.mcp")

F = TypeVar("F", bound=Callable[..., Any])


def mcp_observed_tool(func: F) -> F:
    """
    Add request correlation, execution timing,
    and exception logging to an async MCP tool.

    Apply this decorator below @mcp.tool().
    """

    if not inspect.iscoroutinefunction(func):
        raise TypeError(
            "mcp_observed_tool requires an async function"
        )

    signature = inspect.signature(func)

    if "ctx" not in signature.parameters:
        raise ValueError(
            "MCP tool must declare ctx: Context"
        )

    @functools.wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        bound = signature.bind(*args, **kwargs)
        ctx = bound.arguments["ctx"]

        if not isinstance(ctx, Context):
            raise TypeError(
                "MCP context was not injected correctly"
            )

        request_id = get_mcp_request_id(ctx)
        token = request_id_var.set(request_id)

        started = time.perf_counter()
        tool_name = func.__name__

        try:
            logger.info(
                "MCP tool started tool=%s",
                tool_name,
            )

            result = await func(*args, **kwargs)

            duration_ms = (
                time.perf_counter() - started
            ) * 1000

            logger.info(
                "MCP tool completed tool=%s "
                "duration_ms=%.2f status=success",
                tool_name,
                duration_ms,
            )

            return result

        except Exception:
            duration_ms = (
                time.perf_counter() - started
            ) * 1000

            logger.exception(
                "MCP tool failed tool=%s "
                "duration_ms=%.2f status=error",
                tool_name,
                duration_ms,
            )

            raise

        finally:
            request_id_var.reset(token)

    # Preserve original tool signature for FastMCP.
    wrapper.__signature__ = signature

    return wrapper  # type: ignore[return-value]
