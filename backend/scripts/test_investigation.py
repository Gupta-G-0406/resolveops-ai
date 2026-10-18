
"""Run an end-to-end ResolveOps investigation."""

import asyncio

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage

from app.agents.order_investigation import (
    build_order_investigation_agent,
)


async def main():
    load_dotenv()

    agent = build_order_investigation_agent()

    complaint = (
        "Customer says order ORD-1001 was marked "
        "delivered but the package was not received. "
        "Investigate using available business tools."
    )

    print("\nStarting ResolveOps investigation...\n")

    result = await agent.ainvoke(
        {
            "messages": [
                HumanMessage(content=complaint)
            ]
        },
        config={"recursion_limit": 12},
    )

    print("\n--- INVESTIGATION TRACE ---")

    for message in result["messages"]:
        if isinstance(message, AIMessage) and message.tool_calls:
            for call in message.tool_calls:
                print(
                    f"TOOL REQUEST: {call['name']} "
                    f"{call['args']}"
                )

        elif isinstance(message, ToolMessage):
            print(
                f"TOOL RESULT ({message.name}): "
                f"{message.content}"
            )

    print("\n--- FINAL INVESTIGATION REPORT ---")

    final_message = result["messages"][-1]
    print(final_message.content)


if __name__ == "__main__":
    asyncio.run(main())
