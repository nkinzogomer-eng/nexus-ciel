from pathlib import Path
from uuid import UUID

import pytest

from nexus.core import NexusRuntime
from nexus.persistence import FileSnapshotStore, PersistentRuntime, build_runtime
from nexus.providers import LocalProvider
from nexus.router import AdaptiveRouter
from nexus.schemas import Mission


class ExplodingRouter:
    def __init__(self) -> None:
        self.decisions = []

    async def complete(self, request):
        raise RuntimeError("simulated crash")

    def trace(self):
        return []


@pytest.mark.asyncio
async def test_phase2_ephemeral_runtime_is_explicitly_not_resumable_after_crash():
    runtime = NexusRuntime()
    mission_id = await runtime.accept(Mission(objective="ephemeral"))
    state = runtime.state_graph.get(UUID(mission_id))
    assert state is not None
    assert state.resumable_after_crash is False


@pytest.mark.asyncio
async def test_phase2_file_store_restores_completed_mission_after_restart(tmp_path):
    store = FileSnapshotStore(tmp_path / "runtime.json")
    runtime = PersistentRuntime(store, router=AdaptiveRouter([LocalProvider(confidence=0.90)]))
    mission_id = await runtime.accept(Mission(objective="persist me"))

    restarted = PersistentRuntime(store)
    state = restarted.state_graph.get(UUID(mission_id))
    report = restarted.report(mission_id)

    assert state is not None
    assert state.status == "validated"
    assert state.resumable_after_crash is True
    assert report is not None
    assert report.verdict == "PASS"
    assert restarted.journal.verify_chain()
    assert [entry.type for entry in restarted.journal.entries(UUID(mission_id))] == [
        "mission_accepted",
        "routing_decided",
        "mission_validated",
    ]


@pytest.mark.asyncio
async def test_phase2_file_store_preserves_in_progress_mission_after_crash(tmp_path):
    store = FileSnapshotStore(tmp_path / "runtime.json")
    runtime = PersistentRuntime(store, router=ExplodingRouter())
    mission = Mission(objective="crash halfway")

    with pytest.raises(RuntimeError, match="simulated crash"):
        await runtime.accept(mission)

    restarted = PersistentRuntime(store)
    state = restarted.state_graph.get(mission.mission_id)

    assert state is not None
    assert state.status == "in_progress"
    assert state.resumable_after_crash is True
    assert restarted.report(str(mission.mission_id)) is None
    assert [entry.type for entry in restarted.journal.entries(mission.mission_id)] == [
        "mission_accepted"
    ]


def test_phase2_runtime_factory_selects_the_file_snapshot_store(monkeypatch, tmp_path):
    snapshot_path = tmp_path / "runtime.json"
    monkeypatch.setenv("NEXUS_RUNTIME_SNAPSHOT", str(snapshot_path))
    runtime = build_runtime()
    assert isinstance(runtime, PersistentRuntime)
    assert isinstance(runtime._store, FileSnapshotStore)


def test_phase2_compose_wires_postgres_and_migrations():
    compose = Path("docker-compose.yml").read_text(encoding="utf-8")
    assert "postgres:16-alpine" in compose
    assert "alembic upgrade head" in compose
    assert "NEXUS_DATABASE_URL" in compose
