
"""Verify ResolveOps MCP policy readiness transitions."""

import asyncio
import time

from app.mcp.client_tools import mcp_client


async def main():
    print("Connecting to ResolveOps MCP server...")

    await mcp_client.connect()

    try:
        started = time.perf_counter()

        for attempt in range(1, 13):
            result = await mcp_client.call_tool(
                "get_policy_readiness",
                {},
            )

            print(
                f"Attempt {attempt}: "
                f"elapsed={time.perf_counter() - started:.1f}s "
                f"state={result}"
            )

            if result.get("ready") is True:
                print("Policy model is READY.")
                return

            if result.get("status") == "failed":
                raise RuntimeError(
                    "Policy model warmup failed"
                )

            await asyncio.sleep(3)

        raise TimeoutError(
            "Policy model did not become ready within "
            "the polling window"
        )

    finally:
        await mcp_client.close()
        print("MCP connection closed.")


if __name__ == "__main__":
    asyncio.run(main())
