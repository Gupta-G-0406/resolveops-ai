
"""Execute multi-agent ticket investigations."""

import json
from typing import Any

from app.agents.supervisor import build_supervisor
from app.models.order import Ticket





def parse_mcp_result(raw: Any) -> dict[str, Any]:
    """
    Normalize MCP results.

    Supports:
    - Parsed dictionaries from persistent MCP client
    - Legacy JSON strings
    - MCP result wrappers
    """

    if isinstance(raw, str):
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(
                "Invalid JSON returned by MCP tool"
            ) from exc

    elif isinstance(raw, dict):
        payload = raw

    else:
        raise TypeError(
            f"Unsupported MCP result type: {type(raw).__name__}"
        )

    # Unwrap legacy result format if present.
    if isinstance(payload, dict) and "result" in payload:
        payload = payload["result"]

        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    "Invalid wrapped MCP JSON"
                ) from exc

    if not isinstance(payload, dict):
        raise ValueError(
            "Expected MCP result to contain a dictionary"
        )

    return payload


def extract_policy_ids(evidence: dict) -> list[str]:
    """Extract policy IDs from retrieved MCP policy evidence."""

    raw_policy = evidence.get("policy")

    if not raw_policy:
        return []

    payload = parse_mcp_result(raw_policy)
    policies = payload.get("policies", [])

    return [
        policy["policy_id"]
        for policy in policies
        if isinstance(policy, dict) and policy.get("policy_id")
    ]



async def investigate_ticket(ticket: Ticket) -> dict:
    """Run the supervisor and return the investigation result."""

    order_number = ticket.order.order_number

    complaint = (
        f"Subject: {ticket.subject}\n"
        f"Description: {ticket.description}"
    )

    supervisor = build_supervisor()

    # Initial graph state: no evidence has been collected yet.
    result = await supervisor.ainvoke(
        {
            "order_number": order_number,
            "complaint": complaint,
            "selected_agents": [],
            "remaining_agents": [],
            "evidence": {},  # Correct: initial empty state
            "verification": {},
            "report": "",
        },
        config={"recursion_limit": 15},
    )

    # The supervisor has now collected MCP evidence.
    verification = result["verification"]

    status = (
        "completed"
        if verification.get("status") == "passed"
        else "needs_review"
    )

    selected_agents = result["selected_agents"]

    return {
        "ticket_id": ticket.id,
        "order_number": order_number,
        "status": status,
        "report": result["report"],
        "tools_used": [
            "search_company_policy"
            if agent == "policy"
            else f"get_{agent}"
            for agent in selected_agents
        ],
        "selected_agents": selected_agents,
        "policy_ids": extract_policy_ids(
            result["evidence"]
        ),
        "verification": verification,

        # Save collected evidence for database persistence.
        "evidence": result["evidence"],
    }
