from __future__ import annotations

from datetime import datetime, timezone
from typing import Protocol
from uuid import UUID

from .models import MemoryRecord, SkillCard


class MemoryRepository(Protocol):
    def put_record(self, record: MemoryRecord) -> MemoryRecord: ...
    def get_record(self, record_id: UUID) -> MemoryRecord | None: ...
    def list_records(self) -> list[MemoryRecord]: ...
    def invalidate_record(self, record_id: UUID, reason: str) -> MemoryRecord: ...
    def put_skill_card(self, card: SkillCard) -> SkillCard: ...
    def get_skill_card(self, card_id: UUID) -> SkillCard | None: ...


class MemoryConflict(ValueError):
    """Raised when an idempotency key is reused for different content."""


class InMemoryMemoryRepository:
    """Deterministic contract adapter; not a production persistence backend."""

    def __init__(self) -> None:
        self._records: dict[UUID, MemoryRecord] = {}
        self._record_keys: dict[str, UUID] = {}
        self._cards: dict[UUID, SkillCard] = {}

    def put_record(self, record: MemoryRecord) -> MemoryRecord:
        existing_id = self._record_keys.get(record.extraction_key)
        if existing_id is not None:
            existing = self._records[existing_id]
            if existing.model_dump(mode="json") != record.model_dump(mode="json"):
                raise MemoryConflict(
                    "extraction_key already exists with different memory content"
                )
            return existing
        self._records[record.id] = record
        self._record_keys[record.extraction_key] = record.id
        return record

    def get_record(self, record_id: UUID) -> MemoryRecord | None:
        return self._records.get(record_id)

    def list_records(self) -> list[MemoryRecord]:
        return list(self._records.values())

    def invalidate_record(self, record_id: UUID, reason: str) -> MemoryRecord:
        if not reason.strip():
            raise ValueError("invalidation reason must not be empty")
        current = self._records.get(record_id)
        if current is None:
            raise KeyError(f"unknown memory record {record_id}")
        if current.confidence_status == "invalidated":
            return current
        updated = current.model_copy(
            update={
                "confidence_status": "invalidated",
                "invalidated_at": datetime.now(timezone.utc),
                "invalidation_reason": reason,
            }
        )
        self._records[record_id] = updated
        return updated

    def put_skill_card(self, card: SkillCard) -> SkillCard:
        current = self._cards.get(card.id)
        if current is not None and card.version < current.version:
            raise MemoryConflict("SkillCard version cannot move backwards")
        if current is not None and card.version == current.version:
            if current.model_dump(mode="json") != card.model_dump(mode="json"):
                raise MemoryConflict("same SkillCard version has different content")
            return current
        self._cards[card.id] = card
        return card

    def get_skill_card(self, card_id: UUID) -> SkillCard | None:
        return self._cards.get(card_id)

    def retrieval_candidates(
        self,
        scope: list[str],
        *,
        now: datetime | None = None,
        include_hypotheses: bool = False,
    ) -> list[MemoryRecord]:
        instant = now or datetime.now(timezone.utc)
        requested = set(scope)
        candidates = [
            record
            for record in self._records.values()
            if record.confidence_status != "invalidated"
            and (include_hypotheses or record.confidence_status == "corroborated")
            and (record.expires_at is None or record.expires_at > instant)
            and requested.intersection(record.scope)
        ]
        return sorted(
            candidates,
            key=lambda record: (
                0 if requested.issubset(set(record.scope)) else 1,
                -len(requested.intersection(record.scope)),
                record.created_at,
                str(record.id),
            ),
        )
