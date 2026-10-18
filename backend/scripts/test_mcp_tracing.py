
import asyncio
import os
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main():
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "app.mcp.server"],
        env=os.environ.copy(),
    )

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            request_id = "resolveops-integration-001"

            result = await session.call_tool(
                "get_order",
                arguments={
                    "order_number": "NONEXISTENT-ORDER-001"
                },
                meta={
                    "request_id": request_id
                },
            )

            print("Request ID:", request_id)
            print("Tool error:", result.isError)
            print("Structured content:", result.structuredContent)

            for item in result.content:
                if hasattr(item, "text"):
                    print("Text content:", item.text)


if __name__ == "__main__":
    asyncio.run(main())
