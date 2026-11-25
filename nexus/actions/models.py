from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


ActionStatus = Literal[
    "requested", "authorized", "running", "succeeded", "failed", "partial",
    "uncertain", "cancelled", "rejected",
]
ActionOutcome = Literal["success", "failure", "partial", "uncertain"]
RiskLevel = Literal["low", "medium", "high"]


class ToolSpec(BaseModel):
    tool_id: UUID = Field(default_factory=uuid4)
    name: str = Field(min_length=1, max_length=100, pattern=r"^[a-z][a-z0-9_.-]*$")
    description: str = Field(min_length=1, max_length=500)
    input_schema: dict[str, Any] = Field(default_factory=dict)
    output_schema: dict[str, Any] = Field(default_factory=dict)
    permissions: list[str] = Field(default_factory=list)
    risk_level: RiskLevel = "low"
    reversible: bool = True
    estimated_cost_usd: float = Field(default=0.0, ge=0.0)
    timeout_s: float = Field(default=5.0, gt=0.0, le=60.0)
    idempotency_rule: str = Field(min_length=1, max_length=300)
    verification_conditions: list[dict[str, Any]] = Field(default_factory=list)
    available: bool = True
    requires_approval: bool = False
    access_scope: Literal["none", "workspace"] = "none"


class ActionRequest(BaseModel):
    action_id: UUID = Field(default_factory=uuid4)
    mission_id: UUID
    plan_id: UUID
    step_id: UUID
    tool_name: str = Field(min_length=1)
    parameters: dict[str, Any] = Field(default_factory=dict)
    idempotency_key: str = Field(min_length=1, max_length=256)
    budget_usd: float = Field(default=0.0, ge=0.0)
    preconditions: dict[str, Any] = Field(default_factory=dict)
    requested_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ActionRecord(BaseModel):
    request: ActionRequest
    status: ActionStatus = "requested"
    outcome: ActionOutcome | None = None
    tool_id: UUID | None = None
    permissions: list[str] = Field(default_factory=list)
    observation: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    approval_required: bool = False
    approved: bool = False
    estimated_cost_usd: float = 0.0
    actual_cost_usd: float = 0.0
    started_at: datetime | None = None
    finished_at: datetime | None = None


class ActionResult(BaseModel):
    action_id: UUID
    status: ActionStatus
    outcome: ActionOutcome | None = None
    observation: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    actual_cost_usd: float = 0.0
    idempotent_replay: bool = False
