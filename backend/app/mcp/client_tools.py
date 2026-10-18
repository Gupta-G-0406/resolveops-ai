
import asyncio
import json
import logging
import os
import sys
import time

from contextlib import AsyncExitStack
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from app.core.logging_config import request_id_var



logger = logging.getLogger(__name__)


# ============================================================
# Custom Exceptions
# ============================================================

class MCPConnectionError(RuntimeError):
    """Raised when the MCP connection is unavailable."""
    pass


class MCPToolError(RuntimeError):
    """Raised when an MCP tool returns an error."""
    pass


# ============================================================
# Tool Request
# ============================================================


@dataclass
class ToolRequest:
    name: str
    arguments: dict[str, Any]
    future: asyncio.Future
    request_id: str | None = None



@dataclass
class MCPMetrics:
    """In-memory operational metrics for the MCP client."""

    connection_successes: int = 0
    reconnect_attempts: int = 0

    heartbeat_successes: int = 0
    heartbeat_failures: int = 0

    tool_calls: int = 0
    tool_successes: int = 0
    tool_failures: int = 0

    last_tool_duration_seconds: float | None = None
    last_connected_at: float | None = None
    last_heartbeat_at: float | None = None


# ============================================================
# Persistent MCP Client
# ============================================================

class PersistentMCPClient:

    def __init__(self):
        self._worker: asyncio.Task | None = None
        self._queue: asyncio.Queue[ToolRequest] | None = None
        self._ready: asyncio.Future | None = None

        self._connected = False
        self._closed = False

        # Timeouts in seconds
        self._tool_timeout = 120
        self._heartbeat_interval = 10
        self._heartbeat_timeout = 5
        self._request_timeout = 135
        self._reconnect_delay = 2
        self._startup_timeout = 90
        self.metrics = MCPMetrics()

    # --------------------------------------------------------
    # Connection Status
    # --------------------------------------------------------

    @property
    def is_connected(self) -> bool:
        return self._connected and not self._closed


    def get_metrics(self) -> dict[str, Any]:
        """Return a JSON-serializable metrics snapshot."""

        return {
            "service": "resolveops-mcp",
            "connected": self.is_connected,
            "metrics": {
                "connection_successes": (
                    self.metrics.connection_successes
                ),
                "reconnect_attempts": (
                    self.metrics.reconnect_attempts
                ),
                "heartbeat_successes": (
                    self.metrics.heartbeat_successes
                ),
                "heartbeat_failures": (
                    self.metrics.heartbeat_failures
                ),
                "tool_calls": self.metrics.tool_calls,
                "tool_successes": self.metrics.tool_successes,
                "tool_failures": self.metrics.tool_failures,
                "last_tool_duration_seconds": (
                    self.metrics.last_tool_duration_seconds
                ),
                "last_connected_at": (
                    self.metrics.last_connected_at
                ),
                "last_heartbeat_at": (
                    self.metrics.last_heartbeat_at
                ),
            },
        }


    # --------------------------------------------------------
    # Start MCP Worker
    # --------------------------------------------------------

    async def connect(self):
        if self._worker is not None:
            raise RuntimeError("MCP client already started")

        self._closed = False
        self._connected = False
        self._queue = asyncio.Queue()

        loop = asyncio.get_running_loop()
        self._ready = loop.create_future()

        self._worker = asyncio.create_task(
            self._run(),
            name="resolveops-mcp-worker",
        )

        try:
            await asyncio.wait_for(
                asyncio.shield(self._ready),
                timeout=self._startup_timeout,
            )

        except asyncio.TimeoutError as exc:
            logger.error(
                "[MCP] Startup timed out after %ss",
                self._startup_timeout,
            )

            self._closed = True

            await self._stop_worker()

            self._queue = None
            self._ready = None

            raise MCPConnectionError(
                f"MCP startup exceeded "
                f"{self._startup_timeout} seconds"
            ) from exc

        except BaseException:
            self._closed = True

            await self._stop_worker()

            self._queue = None
            self._ready = None

            raise

    # --------------------------------------------------------
    # Background Worker
    # --------------------------------------------------------

    async def _run(self):
        """
        Own the MCP transport and session in a single task.

        If the connection fails, attempt to reconnect.
        """

        try:
            while not self._closed:

                try:
                    await self._serve_connection()

                    if not self._closed:
                        self._connected = False

                        self._fail_pending_requests(
                            "MCP connection lost; retry investigation"
                        )
                        self.metrics.reconnect_attempts += 1
                        logger.warning(
                            "[MCP] Session ended; reconnecting in %ss",
                            self._reconnect_delay,
                        )

                        await asyncio.sleep(
                            self._reconnect_delay
                        )

                except asyncio.CancelledError:
                    raise

                except Exception:
                    self._connected = False

                    self._fail_pending_requests(
                        "MCP connection failed; retry investigation"
                    )

                    logger.exception(
                        "[MCP] Connection failed"
                    )

                    # Initial connection failed
                    if (
                        self._ready is not None
                        and not self._ready.done()
                    ):
                        self._ready.set_exception(
                            MCPConnectionError(
                                "MCP startup failed"
                            )
                        )
                        return

                    # Connection failed after startup
                    if not self._closed:
                        self.metrics.reconnect_attempts += 1
                        await asyncio.sleep(
                            self._reconnect_delay
                        )

        finally:
            self._connected = False

            self._fail_pending_requests(
                "MCP worker stopped"
            )

    # --------------------------------------------------------
    # MCP Connection and Tool Execution
    # --------------------------------------------------------

    async def _serve_connection(self):
        started = time.perf_counter()

        async with AsyncExitStack() as stack:

            # Start MCP server as a subprocess
            params = StdioServerParameters(
                command=sys.executable,
                args=["-m", "app.mcp.server"],
                env=os.environ.copy(),
            )

            read, write = await stack.enter_async_context(
                stdio_client(params)
            )

            # Create MCP client session
            session = await stack.enter_async_context(
                ClientSession(
                    read,
                    write,
                    read_timeout_seconds=timedelta(
                        seconds=self._tool_timeout
                    ),
                )
            )

            # MCP handshake
            await session.initialize()

            self._connected = True
            self.metrics.connection_successes += 1
            self.metrics.last_connected_at = time.time()

            logger.info(
                "[MCP] Connected in %.2fs",
                time.perf_counter() - started,
            )

            print(
                "[MCP] Connected successfully",
                flush=True,
            )

            # Signal successful startup
            if (
                self._ready is not None
                and not self._ready.done()
            ):
                self._ready.set_result(None)

            # Process requests and send heartbeats
            while not self._closed:

                try:
                    request = await asyncio.wait_for(
                        self._queue.get(),
                        timeout=self._heartbeat_interval,
                    )


                except asyncio.TimeoutError:

                    # No requests: check server health
                    try:
                        await asyncio.wait_for(
                            session.send_ping(),
                            timeout=self._heartbeat_timeout,

                        )
                        self.metrics.heartbeat_successes += 1
                        self.metrics.last_heartbeat_at = time.time()
                        print(
                            "[MCP] Heartbeat successful",
                            flush=True,
                        )

                    except Exception:
                         # Heartbeat actually failed
                        self.metrics.heartbeat_failures += 1
                        self._connected = False

                        logger.exception(
                            "[MCP] Heartbeat failed; reconnecting"
                        )

                        print(
                            "[MCP] Heartbeat failed; reconnecting",
                            flush=True,
                        )

                        return

                    continue

                # Skip requests whose callers have timed out
                if request.future.done():
                    continue

                self.metrics.tool_calls += 1
                tool_started = time.perf_counter()
                request_id_token = request_id_var.set(request.request_id)

                try:
                    result = await asyncio.wait_for(
                        session.call_tool(
                            request.name,
                            arguments=request.arguments,
                             meta=(
                                {"request_id": request.request_id}
                                if request.request_id
                                else None
                            ),
                        ),
                        timeout=self._tool_timeout,
                    )


                    # Tool-level error
                    if result.isError:
                        raise MCPToolError(
                            f"MCP tool {request.name} failed: "
                            f"{result.content}"
                        )

                    payload = self._parse_result(result)
                    self.metrics.tool_successes += 1

                    if not request.future.done():
                        request.future.set_result(payload)

                    logger.info(
                        "[MCP] %s completed in %.2fs",
                        request.name,
                        time.perf_counter() - tool_started,
                    )

                except MCPToolError as exc:

                    self.metrics.tool_failures += 1

                    # Tool error does not necessarily mean
                    # the MCP connection is broken
                    if not request.future.done():
                        request.future.set_exception(exc)

                except asyncio.CancelledError:

                    self.metrics.tool_failures += 1

                    if not request.future.done():
                        request.future.set_exception(
                            MCPConnectionError(
                                "MCP worker stopped"
                            )
                        )

                    raise

                except Exception as exc:

                    self.metrics.tool_failures += 1
                    # Transport/session failure
                    self._connected = False

                    if not request.future.done():
                        request.future.set_exception(
                            MCPConnectionError(
                                f"MCP transport failed: {exc}"
                            )
                        )

                    logger.exception(
                        "[MCP] Transport failure; reconnecting"
                    )

                    return

                finally:

                    # Record execution duration for both
                    # successful and failed tool calls
                    self.metrics.last_tool_duration_seconds = round(
                        time.perf_counter() - tool_started,
                        4,
                    )
                    request_id_var.reset(request_id_token)


    # --------------------------------------------------------
    # Public Tool Calling Method
    # --------------------------------------------------------

    async def call_tool(
        self,
        name: str,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:

        if self._closed or self._queue is None:
            raise MCPConnectionError(
                "MCP client is not running"
            )

        if not self.is_connected:
            raise MCPConnectionError(
                "MCP connection is recovering; retry later"
            )

        loop = asyncio.get_running_loop()
        future = loop.create_future()


        request = ToolRequest(
            name=name,
            arguments=arguments,
            future=future,
            request_id=request_id_var.get(),
        )


        await self._queue.put(request)

        try:
            return await asyncio.wait_for(
                future,
                timeout=self._request_timeout,
            )
        except asyncio.CancelledError:
            # Caller cancelled, e.g. FastAPI health timeout.
            # Worker will skip this request if still queued.
            future.cancel()
            raise

        except asyncio.TimeoutError as exc:
            future.cancel()
            raise MCPConnectionError(
                f"MCP request '{name}' exceeded "
                f"{self._request_timeout} seconds"
            ) from exc

    # --------------------------------------------------------
    # Parse MCP Result
    # --------------------------------------------------------

    @staticmethod
    def _parse_result(result) -> dict[str, Any]:

        structured = getattr(
            result,
            "structuredContent",
            None,
        )

        if isinstance(structured, dict):
            return structured

        for block in result.content:

            if getattr(block, "type", None) == "text":

                try:
                    parsed = json.loads(block.text)

                except json.JSONDecodeError:
                    return {
                        "result": block.text
                    }

                if isinstance(parsed, dict):
                    return parsed

                return {
                    "result": parsed
                }

        return {
            "result": None
        }

    # --------------------------------------------------------
    # Fail Queued Requests
    # --------------------------------------------------------

    def _fail_pending_requests(
        self,
        message: str,
    ):
        if self._queue is None:
            return

        while not self._queue.empty():

            request = self._queue.get_nowait()

            if not request.future.done():
                request.future.set_exception(
                    MCPConnectionError(message)
                )

    # --------------------------------------------------------
    # Stop Background Worker
    # --------------------------------------------------------

    async def _stop_worker(self):

        if self._worker is None:
            return

        self._worker.cancel()

        try:
            await self._worker

        except asyncio.CancelledError:
            pass

        finally:
            self._worker = None

    # --------------------------------------------------------
    # Graceful Shutdown
    # --------------------------------------------------------

    async def close(self):

        self._closed = True
        self._connected = False

        await self._stop_worker()

        self._fail_pending_requests(
            "MCP client shut down"
        )

        self._queue = None
        self._ready = None

        logger.info(
            "[MCP] Client shutdown complete"
        )


# ============================================================
# Singleton MCP Client
# ============================================================

mcp_client = PersistentMCPClient()


# ============================================================
# Public Wrapper for LangGraph Agents
# ============================================================

async def call_mcp_tool(
    name: str,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    """
    Execute an MCP tool using the persistent MCP client.

    Used by ResolveOps LangGraph agents.
    """

    return await mcp_client.call_tool(
        name,
        arguments,
    )
