
"""Test dynamic supervisor routing with demo orders."""

import asyncio

from app.agents.supervisor import build_supervisor


SCENARIOS = [
    {
        "order_number": "ORD-1001",
        "complaint": (
            "The order is marked delivered, "
            "but I have not received it."
        ),
    },
    {
        "order_number": "ORD-1004",
        "complaint": (
            "My order was cancelled, "
            "but I have not received a refund."
        ),
    },
]


async def main():
    supervisor = build_supervisor()

    for scenario in SCENARIOS:
        print("\n" + "=" * 60)
        print("INVESTIGATING:", scenario["order_number"])

        result = await supervisor.ainvoke(
            {
                "order_number": scenario["order_number"],
                "complaint": scenario["complaint"],
                "selected_agents": [],
                "remaining_agents": [],
                "evidence": {},
                "report": "",
                "verification": {},
            },
            config={"recursion_limit": 12},
        )

        print("\nSelected agents:")
        print(result["selected_agents"])

        print("\nEvidence collected:")
        print(list(result["evidence"].keys()))

        print("\nFinal report:")
        print(result["report"])

        print("\nEvidence verification:")
        print(result["verification"])


if __name__ == "__main__":
    asyncio.run(main())
