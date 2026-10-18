
"""
ResolveOps AI - MCP Client Test

Starts the MCP server, connects to it, discovers
available tools, and tests order-related operations.
"""

import asyncio
import os
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main():
    # Configure the MCP server subprocess
    server_params = StdioServerParameters(
        command=sys.executable,          # Current Python interpreter
        args=["-m", "app.mcp.server"],    # MCP server module
        env=os.environ.copy(),           # Pass environment variables
    )

    # Start the server and establish stdio communication
    async with stdio_client(server_params) as (
        read_stream,
        write_stream,
    ):
        # Create an MCP client session
        async with ClientSession(
            read_stream,
            write_stream,
        ) as session:

            # Initialize the MCP connection
            await session.initialize()

            # Discover tools exposed by the MCP server
            tools = await session.list_tools()

            print("\nAvailable MCP tools:")
            for tool in tools.tools:
                print(f"- {tool.name}")

            # Test each tool with the same order number
            for tool_name in [
                "get_order",
                "get_payment",
                "get_shipment",
            ]:
                # Invoke the MCP tool
                result = await session.call_tool(
                    tool_name,
                    {"order_number": "ORD-1001"},
                )

                # Display the tool response
                print(f"\n{tool_name}:")
                print(result)


if __name__ == "__main__":
    # Run the asynchronous MCP client
    asyncio.run(main())
