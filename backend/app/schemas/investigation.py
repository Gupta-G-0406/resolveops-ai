
"""Response schema for multi-agent investigations."""

from typing import Any
from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime


class InvestigationResponse(BaseModel):
    ticket_id: int
    order_number: str
    status: str
    report: str

    # Keep this field for frontend backward compatibility.
    tools_used: list[str] = Field(default_factory=list)

    # New multi-agent information.
    selected_agents: list[str] = Field(default_factory=list)
    policy_ids: list[str] = Field(default_factory=list)
    verification: dict[str, Any] = Field(default_factory=dict)







class InvestigationHistoryItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ticket_id: int
    order_number: str
    status: str
    report: str | None
    selected_agents: list[str]
    policy_ids: list[str]
    verification: dict[str, Any]
    created_at: datetime
    completed_at: datetime | None





class InvestigationListItem(BaseModel):
    """Lightweight investigation summary."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    ticket_id: int
    order_number: str
    status: str
    selected_agents: list[str]
    policy_ids: list[str]
    created_at: datetime
    completed_at: datetime | None


class InvestigationListResponse(BaseModel):
    """Paginated investigation list."""

    items: list[InvestigationListItem]
    total: int
    limit: int
    offset: int


class InvestigationDetailResponse(
    InvestigationHistoryItem
):
    """Full investigation details."""

    evidence: dict[str, Any] = Field(
        default_factory=dict
    )


class AuditEventResponse(BaseModel):
    """Investigation audit event."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    investigation_id: int
    event_type: str
    details: dict[str, Any]
    created_at: datetime



class InvestigationStatsResponse(BaseModel):
    total: int
    completed: int
    needs_review: int
    failed: int
    running: int
    success_rate: float
