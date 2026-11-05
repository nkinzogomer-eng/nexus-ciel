from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, model_validator


MemoryKind = Literal["fact", "procedure", "pitfall", "preference", "constraint", "observation"]
MemoryStatus = Literal["hypothesis", "corroborated", "invalidated"]
SkillCardStatus = Literal["candidate", "corroborated", "deprecated", "invalidated"]


class MemoryProvenance(BaseModel):
    source_mission_id: UUID
    source_report_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_journal_from: int = Field(ge=1)
    source_journal_to: int = Field(ge=1)
    source_journal_valid: bool

    @model_validator(mode="after")
    def journal_range_is_ordered(self) -> "MemoryProvenance":
        if self.source_journal_to < self.source_journal_from:
            raise ValueError("source_journal_to must be >= source_journal_from")
        if not self.source_journal_valid:
            raise ValueError("memory provenance requires a valid source journal chain")
        return self


class MemoryRecord(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    schema_version: int = 1
    extraction_key: str = Field(min_length=1, max_length=256)
    kind: MemoryKind
    scope: list[str] = Field(min_length=1)
    content: str = Field(min_length=1, max_length=8000)
    provenance: MemoryProvenance
    confidence_status: MemoryStatus = "hypothesis"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_confirmed_at: datetime | None = None
    expires_at: datetime | None = None
    invalidated_at: datetime | None = None
    invalidation_reason: str | None = None

    @model_validator(mode="after")
    def invalidation_is_explicit(self) -> "MemoryRecord":
        if self.confidence_status == "invalidated":
            if self.invalidated_at is None or not self.invalidation_reason:
                raise ValueError("invalidated memory requires timestamp and reason")
        elif self.invalidated_at is not None or self.invalidation_reason is not None:
            raise ValueError("non-invalidated memory cannot carry invalidation metadata")
        return self


class SkillStep(BaseModel):
    action: str = Field(min_length=1)
    expected_observation: str = Field(min_length=1)


class SkillCard(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    schema_version: int = 1
    version: int = Field(default=1, ge=1)
    title: str = Field(min_length=1, max_length=200)
    scope: list[str] = Field(min_length=1)
    applicability_preconditions: list[str] = Field(default_factory=list)
    context: str = Field(min_length=1)
    required_inputs: list[str] = Field(default_factory=list)
    method_steps: list[SkillStep] = Field(min_length=1)
    pitfalls: list[str] = Field(default_factory=list)
    stop_conditions: list[str] = Field(default_factory=list)
    expected_resource_profile: dict[str, Any] = Field(default_factory=dict)
    success_count: int = Field(default=0, ge=0)
    failure_count: int = Field(default=0, ge=0)
    partial_count: int = Field(default=0, ge=0)
    provenance: list[MemoryProvenance] = Field(min_length=1)
    status: SkillCardStatus = "candidate"
    confidence_rationale: str = Field(min_length=1)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_reviewed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @model_validator(mode="after")
    def corroboration_requires_distinct_missions(self) -> "SkillCard":
        distinct_sources = {item.source_mission_id for item in self.provenance}
        if self.status == "corroborated" and len(distinct_sources) < 2:
            raise ValueError("corroborated SkillCard requires two distinct source missions")
        return self

    @property
    def distinct_source_count(self) -> int:
        return len({item.source_mission_id for item in self.provenance})
