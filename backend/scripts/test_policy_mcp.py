
import asyncio
import time

from app.mcp.client_tools import call_mcp_tool


async def main():
    print("[TEST] Calling policy MCP tool", flush=True)

    started = time.perf_counter()

    result = await asyncio.wait_for(
        call_mcp_tool(
            "search_company_policy",
            arguments={
                "query": "Delivered but not received",
                "limit": 3,
            },
        ),
        timeout=180,
    )

    print(
        f"[TEST] MCP completed in "
        f"{time.perf_counter() - started:.2f}s",
        flush=True,
    )

    print(result[:1500])


if __name__ == "__main__":
    asyncio.run(main())
