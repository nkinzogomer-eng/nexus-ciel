from uuid import UUID
import pytest
from httpx import ASGITransport, AsyncClient
from nexus.api.app import app, runtime
from nexus.core.mission_journal import MissionJournal
from nexus.schemas import Capability, Mission, MissionState

@pytest.mark.asyncio
async def test_acceptance_mission_enters_and_returns_report():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/mission", json={"objective": "prove phase zero"})
        assert response.status_code == 202
        mission_id = response.json()["mission_id"]
        state = await client.get(f"/mission/{mission_id}")
        report = await client.get(f"/mission/{mission_id}/report")
    assert state.json()["status"] == "validated"
    assert state.json()["resumable_after_crash"] is False
    assert report.json()["verdict"] == "PASS"
    assert runtime.journal.verify_chain()

@pytest.mark.asyncio
async def test_acceptance_event_bus_receives_canonical_events():
    mission = Mission(objective="event test")
    await runtime.accept(mission)
    assert [event.type for event in runtime.bus.events[-2:]] == ["MissionAccepted", "MissionValidated"]


def test_acceptance_journal_is_append_only_and_integrity_checked():
    journal = MissionJournal()
    mission_id = UUID("00000000-0000-0000-0000-000000000001")
    journal.append(mission_id, "decision", "manas", {"ok": True})
    journal.append(mission_id, "validation", "validation_engine", {"passed": True})
    assert len(journal.entries()) == 2
    assert journal.verify_chain()


def test_acceptance_new_capability_starts_probationary():
    runtime.registry.register(Capability(name="test", description="test", type="tool"))
    assert runtime.registry.list()[-1].status == "probationary"


def test_acceptance_resumable_after_crash_is_computed_not_literal():
    state = MissionState(
        mission_id=UUID("00000000-0000-0000-0000-000000000002"),
        objective="persist me",
        resumable_after_crash=True,
    )
    dumped = state.model_dump(mode="json")
    assert dumped["resumable_after_crash"] is False


@pytest.mark.asyncio
async def test_acceptance_health_exposes_memory_backend_honestly():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["persistence_backend"] == "memory"
    assert response.json()["crash_resumable"] is False
