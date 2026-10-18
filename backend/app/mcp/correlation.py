
import re
from typing import Any

from mcp.server.fastmcp import Context


REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


def get_mcp_request_id(ctx: Context) -> str | None:
    """Extract HTTP correlation ID from MCP request metadata."""

    metadata = ctx.request_context.meta

    if metadata is None:
        return None

    # MCP metadata is a Pydantic model.
    # Custom fields are typically stored in model_extra.
    extra = getattr(metadata, "model_extra", None) or {}

    request_id: Any = extra.get("request_id")

    if not isinstance(request_id, str):
        return None

    if not REQUEST_ID_PATTERN.fullmatch(request_id):
        return None

    return request_id
