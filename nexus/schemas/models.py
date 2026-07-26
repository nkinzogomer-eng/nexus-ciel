from __future__ import annotations
from datetime import datetime, timezone
from typing import Any, Literal
from uuid import UUID, uuid4
from pydantic import BaseModel, Field, computed_field

class Mission(BaseModel):
    schema_version: int = 1
    mission_id: UUID = Field(default_factory=uuid4)
    objective: str = Field(min_length=1)
    constraints: dict[str, Any] = Field(default_factory=lambda: {"deadline": None, "budget_usd": 5.0, "forbidden": []})
    context: dict[str, Any] = Field(default_factory=lambda: {"inputs": [], "references": []})
    priority: Literal["low", "normal", "high", "urgent"] = "normal"
    created_by: Literal["human", "nexus"] = "human"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class Event(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    type: str
    schema_version: int = 1
    mission_id: UUID | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    payload: dict[str, Any] = Field(default_factory=dict)
    causation_id: UUID | None = None
    correlation_id: UUID = Field(default_factory=uuid4)

class MissionState(BaseModel):
    mission_id: UUID
    objective: str
    status: Literal["planned", "in_progress", "validated", "abandoned"] = "planned"
    iterations: int = 0
    checkpointed_at: datetime | None = None

    @computed_field
    @property
    def resumable_after_crash(self) -> bool:
        return self.checkpointed_at is not None

class Report(BaseModel):
    schema_version: int = 1
    mission_id: UUID
    verdict: Literal["PASS", "FAIL", "PARTIAL"]
    objective: str
    summary: str
    iterations: int
    cost_usd: float = 0.0
    duration_s: float = 0.0
    actions: list[dict[str, Any]] = Field(default_factory=list)
    validation: dict[str, Any] = Field(default_factory=dict)
    learned: dict[str, Any] = Field(default_factory=lambda: {"skill_cards": [], "capabilities_touched": []})
    guard_events: list[dict[str, Any]] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class Capability(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    name: str
    description: str
    type: Literal["script", "workflow", "agent", "prompt-recipe", "tool"]
    status: Literal["probationary", "proven", "legacy"] = "probationary"
    version: int = 1
    stats: dict[str, Any] = Field(default_factory=lambda: {"executions": 0, "successes": 0, "failures": 0})
