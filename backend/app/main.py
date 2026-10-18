
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.tickets import router as tickets_router
from app.api.orders import router as orders_router
from app.api.investigations import (
    router as investigations_router,
    history_router,
)

from app.mcp.client_tools import (
    mcp_client,
    MCPConnectionError,
    MCPToolError,
)

from app.core.logging_config import configure_logging
from app.core.request_logging import RequestLoggingMiddleware

import logging

logger = logging.getLogger("resolveops.api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting ResolveOps API")
    logger.info("Connecting to MCP server")

    try:
        await mcp_client.connect()
        logger.info("MCP server connected successfully")

        yield

    except Exception:
        logger.exception("ResolveOps application lifecycle failed")
        raise

    finally:
        logger.info("Closing MCP client")
        await mcp_client.close()
        logger.info("MCP client closed")

configure_logging()

app = FastAPI(
    title="ResolveOps AI API",
    lifespan=lifespan,
    description="Multi-Agent Support Investigation Platform",
    version="0.1.0",
)



@app.exception_handler(MCPConnectionError)
async def mcp_connection_exception_handler(
    request: Request,
    exc: MCPConnectionError,
):
    return JSONResponse(
        status_code=503,
        content={
            "detail": {
                "code": "MCP_UNAVAILABLE",
                "message": (
                    "AI investigation service is temporarily "
                    "unavailable. Please retry."
                ),
            }
        },
        headers={"Retry-After": "5"},
    )


@app.exception_handler(MCPToolError)
async def mcp_tool_exception_handler(
    request: Request,
    exc: MCPToolError,
):
    return JSONResponse(
        status_code=502,
        content={
            "detail": {
                "code": "MCP_TOOL_FAILED",
                "message": (
                    "An AI investigation tool failed. "
                    "Please retry or contact support."
                ),
            }
        },
    )


app.include_router(tickets_router)
app.include_router(orders_router)
app.include_router(investigations_router)
app.include_router(history_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,   #Permits the frontend to send sensitive credentials
    allow_methods=["*"], #Grants permission for all standard HTTP methods (GET, POST, PUT, DELETE, etc.).
    allow_headers=["*"], #Permits all custom or standard HTTP headers to be sent in the requests.
)

app.add_middleware(RequestLoggingMiddleware)




@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "service": "resolveops-api",
        "version": "0.1.0",
    }





MCP_HEALTH_TIMEOUT_SECONDS = 3.0


@app.get("/health/mcp")
async def mcp_health():
    """Return MCP connection and policy readiness."""

    connected = mcp_client.is_connected

    response = {
        "service": "resolveops-mcp",
        "connected": connected,
        "policy": {
            "status": "unavailable",
            "ready": False,
        },
    }

    if not connected:
        return response

    try:
        policy = await asyncio.wait_for(
            mcp_client.call_tool(
                "get_policy_readiness",
                {},
            ),
            timeout=MCP_HEALTH_TIMEOUT_SECONDS,
        )

        response["policy"] = policy

    except asyncio.TimeoutError:
        logger.warning(
            "MCP policy readiness check timed out"
        )

    except Exception:
        logger.exception(
            "Unable to retrieve MCP policy readiness"
        )

    return response


@app.get("/health/mcp/metrics")
async def get_mcp_metrics():
    """Return MCP connection and tool execution metrics."""

    return mcp_client.get_metrics()
