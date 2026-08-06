from pathlib import Path
from uuid import UUID

import pytest

from nexus.core import NexusRuntime
from nexus.persistence import FileSnapshotStore, PersistentRuntime, build_runtime
from nexus.providers import LocalProvider
from nexus.router import AdaptiveRouter
from nexus.schemas import Mission, MissionState, Report


class ExplodingRouter:
    def __init__(self):
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
    assert state is not None and state.resumable_after_crash is False


@pytest.mark.asyncio
async def test_phase2_file_store_restores_completed_mission_after_restart(tmp_path):
    store = FileSnapshotStore(tmp_path / "runtime.json")
    runtime = PersistentRuntime(store, router=AdaptiveRouter([LocalProvider(confidence=0.90)]))
    mission_id = await runtime.accept(Mission(objective="persist me"))

    restarted = PersistentRuntime(store)
    state = restarted.state_graph.get(UUID(mission_id))
    report = restarted.report(mission_id)

    assert state is not None and state.status == "validated" and state.resumable_after_crash is True
    assert report is not None and report.verdict == "PASS"
    assert restarted.journal.verify_chain()


@pytest.mark.asyncio
async def test_phase2_file_store_marks_interrupted_mission_as_abandoned_after_restart(tmp_path):
    store = FileSnapshotStore(tmp_path / "runtime.json")
    runtime = PersistentRuntime(store, router=ExplodingRouter())
    mission = Mission(objective="crash halfway")

    with pytest.raises(RuntimeError, match="simulated crash"):
        await runtime.accept(mission)

    restarted = PersistentRuntime(store)
    state = restarted.state_graph.get(mission.mission_id)
    report = restarted.report(str(mission.mission_id))

    assert state is not None
    assert state.status == "abandoned"
    assert state.resumable_after_crash is True
    assert report is not None
    assert report.verdict == "FAIL"
    assert "automatic resume is disabled" in report.summary
    assert report.validation["recovery_policy"] == "controlled_abandon"
    assert report.actions[-1]["stage"] == "recovery"
    assert restarted.journal.entries(mission.mission_id)[-1].type == "mission_interrupted"
    assert restarted.journal.verify_chain()


def test_phase2_recovery_replaces_a_stale_success_report(tmp_path):
    store = FileSnapshotStore(tmp_path / "runtime.json")
    mission = Mission(objective="stale success")
    store.save(
        {
            "schema_version": 1,
            "saved_at": None,
            "states": [
                MissionState(
                    mission_id=mission.mission_id,
                    objective=mission.objective,
                    status="in_progress",
                    iterations=1,
                    resumable_after_crash=True,
                ).model_dump(mode="json")
            ],
            "journal": [],
            "capabilities": [],
            "reports": {
                str(mission.mission_id): Report(
                    mission_id=mission.mission_id,
                    verdict="PASS",
                    objective=mission.objective,
                    summary="stale success",
                    iterations=1,
                ).model_dump(mode="json")
            },
        }
    )

    restarted = PersistentRuntime(store)
    state = restarted.state_graph.get(mission.mission_id)
    report = restarted.report(str(mission.mission_id))

    assert state is not None and state.status == "abandoned"
    assert report is not None and report.verdict == "FAIL"
    assert report.summary.startswith("mission interrupted by crash")
    assert report.validation["recovery_policy"] == "controlled_abandon"
    assert restarted.journal.verify_chain()


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
