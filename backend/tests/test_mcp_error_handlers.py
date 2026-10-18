
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.mcp.client_tools import (
    MCPConnectionError,
    MCPToolError,
)

from app.main import (
    mcp_connection_exception_handler,
    mcp_tool_exception_handler,
)


# Isolated FastAPI app
# Does not start the ResolveOps MCP worker
api = FastAPI()


# Register exception handlers
api.add_exception_handler(
    MCPConnectionError,
    mcp_connection_exception_handler,
)

api.add_exception_handler(
    MCPToolError,
    mcp_tool_exception_handler,
)


# ---------------------------------------------------
# Mock Routes
# ---------------------------------------------------

@api.get("/test/mcp-connection")
async def simulate_connection_failure():
    raise MCPConnectionError(
        "Simulated MCP disconnection"
    )


@api.get("/test/mcp-tool")
async def simulate_tool_failure():
    raise MCPToolError(
        "Simulated MCP tool failure"
    )


# ---------------------------------------------------
# Test 1: MCP Connection Failure
# ---------------------------------------------------

def test_mcp_connection_error():

    with TestClient(api) as client:
        response = client.get(
            "/test/mcp-connection"
        )

    assert response.status_code == 503

    assert response.json() == {
        "detail": {
            "code": "MCP_UNAVAILABLE",
            "message": (
                "AI investigation service is temporarily "
                "unavailable. Please retry."
            ),
        }
    }

    assert response.headers["retry-after"] == "5"


# ---------------------------------------------------
# Test 2: MCP Tool Failure
# ---------------------------------------------------

def test_mcp_tool_error():

    with TestClient(api) as client:
        response = client.get(
            "/test/mcp-tool"
        )

    assert response.status_code == 502

    assert response.json()["detail"]["code"] == (
        "MCP_TOOL_FAILED"
    )
