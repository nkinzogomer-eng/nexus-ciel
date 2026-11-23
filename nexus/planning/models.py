from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, model_validator


ConditionOperator = Literal["equals", "not_equals", "exists"]
StepStatus = Literal[
    "planned",
    "ready",
    "running",
    "observed",
    "verified",
    "failed",
    "blocked",
    "abandoned",
]
PlanStatus = Literal["draft", "ready", "running", "succeeded", "failed", "invalid"]


class DeterministicCondition(BaseModel):
    """Small, non-executable condition evaluated against an observation map."""

    key: str = Field(min_length=1, max_length=200)
    operator: ConditionOperator = "equals"
    expected: Any = None

    def evaluate(self, facts: dict[str, Any]) -> bool:
        present = self.key in facts
        if self.operator == "exists":
            return present is bool(self.expected)
        if not present:
            return False
        if self.operator == "equals":
            return facts[self.key] == self.expected
        return facts[self.key] != self.expected


class Step(BaseModel):
    step_id: UUID = Field(default_factory=uuid4)
    ordinal: int = Field(ge=1)
    title: str = Field(min_length=1, max_length=200)
    action_ref: str = Field(min_length=1, max_length=200)
    depends_on: list[UUID] = Field(default_factory=list)
    preconditions: list[DeterministicCondition] = Field(default_factory=list)
    postconditions: list[DeterministicCondition] = Field(default_factory=list)
    idempotency_key: str = Field(min_length=1, max_length=256)
    budget_usd: float = Field(default=0.0, ge=0.0)
    status: StepStatus = "planned"
    observation: dict[str, Any] | None = None
    error: str | None = None
    spent_cost_usd: float = Field(default=0.0, ge=0.0)


class Plan(BaseModel):
    plan_id: UUID = Field(default_factory=uuid4)
    mission_id: UUID
    schema_version: int = 1
    version: int = Field(default=1, ge=1)
    steps: list[Step] = Field(min_length=1)
    max_steps: int = Field(default=50, ge=1)
    budget_usd: float = Field(default=0.0, ge=0.0)
    spent_cost_usd: float = Field(default=0.0, ge=0.0)
    status: PlanStatus = "draft"
    revision_reason: str = Field(default="initial plan", min_length=1, max_length=1000)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @model_validator(mode="after")
    def unique_step_ids_and_ordinals(self) -> "Plan":
        if len({step.step_id for step in self.steps}) != len(self.steps):
            raise ValueError("plan steps must have unique step_id values")
        if len({step.ordinal for step in self.steps}) != len(self.steps):
            raise ValueError("plan steps must have unique ordinal values")
        return self

    @property
    def total_steps(self) -> int:
        return len(self.steps)

    @property
    def all_verified(self) -> bool:
        return bool(self.steps) and all(step.status == "verified" for step in self.steps)

    @property
    def total_spent_cost_usd(self) -> float:
        return round(sum(step.spent_cost_usd for step in self.steps), 10)
