from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError

from nexus.memory import (
    InMemoryMemoryRepository,
    MemoryConflict,
    MemoryProvenance,
    MemoryRecord,
    SkillCard,
    SkillStep,
)


def provenance(mission_id=None):
    return MemoryProvenance(
        source_mission_id=mission_id or uuid4(),
        source_report_digest="a" * 64,
        source_journal_from=1,
        source_journal_to=3,
        source_journal_valid=True,
    )


def record(*, key="extract-1", scope=None, status="hypothesis", expires_at=None):
    return MemoryRecord(
        extraction_key=key,
        kind="procedure",
        scope=scope or ["python", "testing"],
        content="Run the focused regression suite before integration.",
        provenance=provenance(),
        confidence_status=status,
        expires_at=expires_at,
        last_confirmed_at=datetime.now(timezone.utc) if status == "corroborated" else None,
    )


def card(*, status="candidate", sources=None):
    sources = sources or [provenance()]
    return SkillCard(
        title="Focused regression workflow",
        scope=["python", "testing"],
        context="A code change needs targeted validation.",
        method_steps=[SkillStep(action="Run focused tests", expected_observation="All focused tests pass")],
        provenance=sources,
        status=status,
        confidence_rationale="Evidence from source missions is recorded explicitly.",
    )


def test_memory_provenance_rejects_invalid_journal_and_reversed_range():
    with pytest.raises(ValidationError):
        MemoryProvenance(
            source_mission_id=uuid4(),
            source_report_digest="a" * 64,
            source_journal_from=4,
            source_journal_to=2,
            source_journal_valid=True,
        )
    with pytest.raises(ValidationError):
        MemoryProvenance(
            source_mission_id=uuid4(),
            source_report_digest="a" * 64,
            source_journal_from=1,
            source_journal_to=2,
            source_journal_valid=False,
        )


def test_invalidated_memory_requires_reason_and_timestamp():
    with pytest.raises(ValidationError):
        record(status="invalidated")


def test_record_write_is_idempotent_and_conflicting_reuse_is_rejected():
    repository = InMemoryMemoryRepository()
    original = record()
    assert repository.put_record(original) == original
    assert repository.put_record(original) == original
    assert len(repository.list_records()) == 1

    changed = original.model_copy(update={"content": "different method"})
    with pytest.raises(MemoryConflict):
        repository.put_record(changed)


def test_retrieval_excludes_hypotheses_expired_and_invalidated_by_default():
    repository = InMemoryMemoryRepository()
    hypothesis = record(key="hypothesis")
    expired = record(
        key="expired",
        status="corroborated",
        expires_at=datetime.now(timezone.utc) - timedelta(seconds=1),
    )
    corroborated = record(key="good", status="corroborated")
    invalidated = repository.put_record(record(key="bad"))
    repository.put_record(hypothesis)
    repository.put_record(expired)
    repository.put_record(corroborated)
    repository.invalidate_record(invalidated.id, "counterexample found")

    results = repository.retrieval_candidates(["python"])
    assert results == [corroborated]
    assert repository.retrieval_candidates(["python"], include_hypotheses=True) == [
        hypothesis,
        corroborated,
    ]


def test_candidate_skill_card_needs_one_source_but_corroborated_needs_two_distinct_sources():
    candidate = card()
    assert candidate.status == "candidate"
    assert candidate.distinct_source_count == 1

    same_source_twice = provenance(candidate.provenance[0].source_mission_id)
    with pytest.raises(ValidationError):
        card(status="corroborated", sources=[candidate.provenance[0], same_source_twice])

    promoted = card(status="corroborated", sources=[candidate.provenance[0], provenance()])
    assert promoted.distinct_source_count == 2


def test_skill_card_versions_are_monotonic():
    repository = InMemoryMemoryRepository()
    original = card()
    repository.put_skill_card(original)
    older = original.model_copy(update={"version": 0})
    with pytest.raises(ValidationError):
        SkillCard.model_validate(older.model_dump())
    newer = original.model_copy(update={"version": 2})
    repository.put_skill_card(newer)
    assert repository.get_skill_card(original.id).version == 2
