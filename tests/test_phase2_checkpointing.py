import asyncio

import pytest

from nexus.persistence import CheckpointingRuntime, SqliteRuntimeStore
from nexus.providers import CompletionResult, LocalProvider, ProviderCaps, ProviderHealth, SecondaryProvider
from nexus.router import AdaptiveRouter
from nexus.schemas import Capability, Mission, MissionState


class BlockingProvider:
    name = "blocking"
    stage = "small_model"

    def __init__(self) -> None:
        self.started = asyncio.Event()
        self.release = asyncio.Event()

    async def health(self):
        return ProviderHealth(True, "waiting")

    async def complete(self, request):
        self.started.set()
        await self.release.wait()
        return CompletionResult(f"blocking:{request.prompt}", 0.8, 0.0)

    def cost_estimate(self, request):
        return 0.0

    def capabilities(self):
        return ProviderCaps(context_window=1024, tools=False, json_mode=True)


def test_phase2_state_is_not_resumable_without_a_checkpoint():
    state = MissionState(mission_id=Mission(objective="checkpoint me").mission_id, objective="checkpoint me")
    assert state.resumable_after_crash is False
    assert state.checkpointed_at is None


@pytest.mark.asyncio
async def test_phase2_checkpoint_round_trip_restores_canonical_sources(tmp_path):
    store = SqliteRuntimeStore(tmp_path / "runtime.sqlite3")
    runtime = CheckpointingRuntime(router=AdaptiveRouter([LocalProvider(confidence=0.9)]), store=store)
    runtime.registry.register(Capability(name="persist", description="persist", type="tool"))
    mission_id = await runtime.accept(Mission(objective="round trip"))

    restored = CheckpointingRuntime.load(store, router=AdaptiveRouter([LocalProvider(confidence=0.9)]))
    assert restored.report(mission_id) is not None
    restored_state = restored.state_graph.get(restored.report(mission_id).mission_id)
    assert restored_state is not None
    assert restored_state.status == "validated"
    assert restored_state.resumable_after_crash is True
    assert restored.journal.verify_chain() is True
    assert restored.registry.list()[-1].name == "persist"


@pytest.mark.asyncio
async def test_phase2_crash_recovery_can_finish_a_pending_mission(tmp_path):
    store = SqliteRuntimeStore(tmp_path / "runtime.sqlite3")
    blocker = BlockingProvider()
    runtime = CheckpointingRuntime(router=AdaptiveRouter([blocker]), store=store)
    mission = Mission(objective="resume me after a crash")

    task = asyncio.create_task(runtime.accept(mission))
    await blocker.started.wait()

    pending = store.pending_missions()
    assert len(pending) == 1
    assert pending[0].state.status == "in_progress"
    assert pending[0].state.resumable_after_crash is True

    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    resumed = CheckpointingRuntime.load(
        store,
        router=AdaptiveRouter([SecondaryProvider(confidence=0.95)]),
    )
    resumed_ids = await resumed.resume_pending()
    assert resumed_ids == [str(mission.mission_id)]

    report = resumed.report(str(mission.mission_id))
    state = resumed.state_graph.get(mission.mission_id)
    assert report is not None and state is not None
    assert report.verdict == "PASS"
    assert state.status == "validated"
    assert resumed.journal.verify_chain() is True


@pytest.mark.asyncio
async def test_phase2_checkpointed_failure_survives_restart(tmp_path):
    store = SqliteRuntimeStore(tmp_path / "runtime.sqlite3")
    runtime = CheckpointingRuntime(
        router=AdaptiveRouter([LocalProvider(confidence=0.1), SecondaryProvider(confidence=0.2)]),
        store=store,
    )
    mission_id = await runtime.accept(Mission(objective="fail but persist"))

    restored = CheckpointingRuntime.load(
        store,
        router=AdaptiveRouter([LocalProvider(confidence=0.1), SecondaryProvider(confidence=0.2)]),
    )
    report = restored.report(mission_id)
    assert report is not None
    state = restored.state_graph.get(report.mission_id)
    assert state is not None
    assert report.verdict == "FAIL"
    assert state.status == "abandoned"
    assert restored.journal.verify_chain() is True


@pytest.mark.asyncio
async def test_phase2_checkpoint_persists_routing_trace(tmp_path):
    store = SqliteRuntimeStore(tmp_path / "runtime.sqlite3")
    runtime = CheckpointingRuntime(
        router=AdaptiveRouter([LocalProvider(confidence=0.1), SecondaryProvider(confidence=0.95)]),
        store=store,
    )
    mission_id = await runtime.accept(Mission(objective="trace me"))
    restored = CheckpointingRuntime.load(store, router=AdaptiveRouter([SecondaryProvider(confidence=0.95)]))
    report = restored.report(mission_id)
    assert report is not None
    assert [step["stage"] for step in report.actions] == ["small_model", "large_model"]
