
"""ResolveOps MCP business tools server."""

import os

# Configure Hugging Face before importing ML libraries.
# Offline mode works only if the model is already cached.
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"
os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"

import asyncio
import logging
import threading
import time

from logging.handlers import RotatingFileHandler
from pathlib import Path

from mcp.server.fastmcp import FastMCP, Context

from app.db.session import AsyncSessionLocal
from app.services import order_service
from app.rag.policy_store import (
    get_collection,
    search_policies,
)
from app.core.logging_config import (
    SecureJSONFormatter,
    RequestContextFilter,
)
from app.core.log_security import SensitiveDataFilter
from app.mcp.correlation import get_mcp_request_id
from app.mcp.observability import mcp_observed_tool


# ResolveOps MCP server initialize karo.
mcp = FastMCP("ResolveOps Business Tools")


LOG_FILE = Path(__file__).resolve().parents[2] / "mcp_debug.log"

file_handler = RotatingFileHandler(
    LOG_FILE,
    maxBytes=5 * 1024 * 1024,
    backupCount=3,
    encoding="utf-8",
)

file_handler.setFormatter(SecureJSONFormatter())
file_handler.addFilter(RequestContextFilter())
file_handler.addFilter(SensitiveDataFilter())

root_logger = logging.getLogger()
root_logger.handlers.clear()
root_logger.addHandler(file_handler)
root_logger.setLevel(logging.INFO)

logging.getLogger(
    "mcp.server.lowlevel.server"
).setLevel(logging.WARNING)

logger = logging.getLogger("resolveops.mcp")





def warmup_policy_model() -> None:
    """Initialize policy collection in a background thread."""

    started = time.perf_counter()

    update_policy_state("warming", source="warmup")

    logger.info("[MCP WARMUP] Policy warmup started")

    try:
        collection = get_collection()
        policy_count = collection.count()

        update_policy_state("ready", source="warmup")

        logger.info(
            "[MCP WARMUP] Policy warmup completed "
            "duration_seconds=%.2f policies=%d",
            time.perf_counter() - started,
            policy_count,
        )

    except Exception:
        update_policy_state("failed", source="warmup")

        logger.exception(
            "[MCP WARMUP] Policy warmup failed"
        )


# Order number se basic order details fetch karo.

@mcp.tool()
@mcp_observed_tool
async def get_order(
    order_number: str,
    ctx: Context,
) -> dict:
    """Get order information using an order number."""

    async with AsyncSessionLocal() as db:
        order = await order_service.get_order_by_number(
            db,
            order_number,
        )

        if order is None:
            return {
                "found": False,
                "order_number": order_number,
                "message": "Order not found",
            }

        return {
            "found": True,
            "order": {
                "id": order.id,
                "order_number": order.order_number,
                "customer_name": order.customer_name,
                "status": order.status,
                "total_amount_paise": order.total_amount_paise,
            },
        }


# Order ki payment status aur amount fetch karo.

@mcp.tool()
@mcp_observed_tool
async def get_payment(
    order_number: str,
    ctx: Context,
) -> dict:
    """Get payment information for an order."""

    async with AsyncSessionLocal() as db:
        order = await order_service.get_order_by_number(
            db, order_number
        )

        if order is None:
            return {
                "found": False,
                "message": "Order not found",
            }

        if order.payment is None:
            return {
                "found": False,
                "message": "Payment record not found",
            }

        return {
            "found": True,
            "order_number": order.order_number,
            "payment": {
                "id": order.payment.id,
                "status": order.payment.status,
                "amount_paise": order.payment.amount_paise,
            },
        }

# Order ki shipment status aur delivery proof availability fetch karo.

@mcp.tool()
@mcp_observed_tool
async def get_shipment(
    order_number: str,
    ctx: Context,
) -> dict:
    """Get shipment and delivery proof information."""

    async with AsyncSessionLocal() as db:
        order = await order_service.get_order_by_number(
            db, order_number
        )

        if order is None:
            return {
                "found": False,
                "message": "Order not found",
            }

        if order.shipment is None:
            return {
                "found": False,
                "message": "Shipment record not found",
            }

        return {
            "found": True,
            "order_number": order.order_number,
            "shipment": {
                "id": order.shipment.id,
                "status": order.shipment.status,
                "delivery_proof_available": (
                    order.shipment.delivery_proof_available
                ),
            },
        }






async def execute_policy_search(
    query: str,
    limit: int = 3,
) -> dict:
    """Execute policy search and recover readiness on success."""

    if not query.strip():
        return {
            "found": False,
            "policies": [],
            "message": "Search query cannot be empty",
        }

    matches = await asyncio.to_thread(
        search_policies,
        query=query,
        limit=max(1, min(limit, 5)),
    )

    # Successful search confirms policy model is operational.
    update_policy_state("ready")

    return {
        "found": bool(matches),
        "policies": matches,
    }


@mcp.tool()
@mcp_observed_tool
async def search_company_policy(
    query: str,
    ctx: Context,
    limit: int = 3,
) -> dict:
    """Search company policies."""

    return await execute_policy_search(
        query=query,
        limit=limit,
    )


# Policy readiness is maintained inside the MCP process.
_policy_state_lock = threading.Lock()
_policy_state = {
    "status": "not_started",
    "ready": False,
    "error": None,
}



def update_policy_state(
    status: str,
    error: str | None = None,
    *,
    source: str = "runtime",
) -> None:
    """Update policy readiness with warmup race protection."""

    with _policy_state_lock:
        # Stale warmup updates cannot override
        # a model already confirmed operational.
        if (
            source == "warmup"
            and _policy_state["ready"]
            and status in {"warming", "failed"}
        ):
            return

        _policy_state["status"] = status
        _policy_state["ready"] = status == "ready"
        _policy_state["error"] = error


@mcp.tool()
async def get_policy_readiness() -> dict:
    """Return policy embedding model readiness."""

    with _policy_state_lock:
        return dict(_policy_state)


# Script directly run hone par MCP server start karo.

if __name__ == "__main__":
    logger.info("[MCP STARTUP] Initializing MCP server")

    warmup_thread = threading.Thread(
        target=warmup_policy_model,
        name="resolveops-policy-warmup",
        daemon=True,
    )

    warmup_thread.start()

    logger.info(
        "[MCP STARTUP] Background warmup scheduled"
    )

    logger.info("[MCP STARTUP] Starting MCP stdio server")

    mcp.run(transport="stdio")