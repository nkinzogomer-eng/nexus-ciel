from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import UUID, uuid4, uuid5, NAMESPACE_URL

from pydantic import BaseModel, Field, model_validator


class Hypothesis(BaseModel):
    statement: str = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)
    basis: list[str] = Field(default_factory=list)


class MissingInformation(BaseModel):
    name: str = Field(min_length=1)
    classification: Literal["blocking", "non_blocking", "verifiable_later"]
    reason: str = Field(min_length=1)


class GoalUnderstanding(BaseModel):
    objective: str = Field(min_length=1, max_length=2000)
    expected_results: list[str] = Field(min_length=1)
    constraints: dict[str, Any] = Field(default_factory=dict)
    success_criteria: list[str] = Field(min_length=1)
    limits: list[str] = Field(default_factory=list)
    known_facts: dict[str, Any] = Field(default_factory=dict)
    unknowns: list[str] = Field(default_factory=list)
    hypotheses: list[Hypothesis] = Field(default_factory=list)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class CompiledMission(BaseModel):
    mission_id: UUID = Field(default_factory=uuid4)
    objective: str
    expected_results: list[str]
    subgoals: list[str]
    dependencies: dict[str, list[str]] = Field(default_factory=dict)
    constraints: dict[str, Any] = Field(default_factory=dict)
    success_criteria: list[str]
    missing_information: list[str] = Field(default_factory=list)
    missing_information_details: list[MissingInformation] = Field(default_factory=list)
    assumptions: list[Hypothesis] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)

    @property
    def is_complete(self) -> bool:
        return not self.missing_information


class StrategyCandidate(BaseModel):
    strategy_id: UUID | None = None
    name: str = Field(min_length=1, max_length=200)
    objective: str = Field(min_length=1)
    planned_steps: list[str] = Field(min_length=1)
    dependencies: dict[str, list[str]] = Field(default_factory=dict)
    preconditions: list[str] = Field(default_factory=list)
    estimated_cost_usd: float = Field(default=0.0, ge=0.0)
    estimated_duration_s: float | None = Field(default=None, ge=0.0)
    risks: list[str] = Field(default_factory=list)
    advantages: list[str] = Field(default_factory=list)
    limits: list[str] = Field(default_factory=list)
    success_criteria: list[str] = Field(default_factory=list)
    score: float = 0.0
    uncertainty: float = Field(default=0.0, ge=0.0, le=1.0)
    risk_level: float = Field(default=0.0, ge=0.0, le=1.0)
    reversible: bool = True
    required_information: list[str] = Field(default_factory=list)
    constraint_violations: list[str] = Field(default_factory=list)
    score_justification: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def stable_id(self) -> "StrategyCandidate":
        if self.strategy_id is None:
            self.strategy_id = uuid5(
                NAMESPACE_URL,
                f"ciel-strategy:{self.name}:{self.objective}:{'|'.join(self.planned_steps)}",
            )
        return self


class StrategySelection(BaseModel):
    strategy_id: UUID
    candidate_name: str
    reasons: list[str] = Field(min_length=1)
    rejected_candidates: list[UUID] = Field(default_factory=list)
    deterministic_key: str
    selected_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CognitiveDecision(BaseModel):
    decision_id: UUID = Field(default_factory=uuid4)
    kind: Literal["keep", "revise", "suspend", "abandon", "select_strategy"]
    subject_id: UUID
    reasons: list[str] = Field(min_length=1)
    evidence: list[str] = Field(default_factory=list)
    authority: Literal["deterministic_core"] = "deterministic_core"
    llm_advice_digest: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ObservationAssessment(BaseModel):
    observation_id: UUID = Field(default_factory=uuid4)
    step_id: UUID
    outcome: Literal["success", "failure", "partial", "uncertain"]
    observed: dict[str, Any]
    expected: list[str] = Field(default_factory=list)
    divergence: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CognitiveCycle(BaseModel):
    cycle_id: UUID = Field(default_factory=uuid4)
    goal: GoalUnderstanding
    mission: CompiledMission
    candidates: list[StrategyCandidate]
    selection: StrategySelection
    plan_id: UUID
    mode: Literal["CORE_ONLY", "AI_ENABLED"] = "CORE_ONLY"
    decisions: list[CognitiveDecision] = Field(default_factory=list)
    observations: list[ObservationAssessment] = Field(default_factory=list)
    status: Literal["planned", "running", "succeeded", "failed", "partial", "suspended", "abandoned"] = "planned"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
