"""End-to-end smoke: a real mission crossing every component built so far."""
import json
from uuid import UUID

import pytest

from nexus.core import NexusRuntime
from nexus.core.state_graph import UnknownMission
from nexus.providers import LocalProvider, SecondaryProvider
from nexus.router import AdaptiveRouter
from nexus.schemas import Mission


@pytest.mark.asyncio
async def test_mission_is_served_by_the_cheapest_level_end_to_end():
    router = AdaptiveRouter([SecondaryProvider(), LocalProvider(confidence=0.85)])
    runtime = NexusRuntime(router=router)
    mission_id = await runtime.accept(Mission(objective="summarise the sprint"))

    report = runtime.report(mission_id)
    state = runtime.state_graph.get(UUID(mission_id))

    assert report is not None and state is not None
    assert report.verdict == "PASS"
    assert state.status == "validated"
    assert report.cost_usd == 0.0
    assert report.actions[-1]["stage"] == "small_model"
    assert runtime.journal.verify_chain()
    assert "routing_decided" in [entry.type for entry in runtime.journal.entries()]


@pytest.mark.asyncio
async def test_mission_escalates_and_reports_the_real_cost():
    router = AdaptiveRouter(
        [LocalProvider(confidence=0.10), SecondaryProvider(confidence=0.95, cost_usd=0.02)]
    )
    runtime = NexusRuntime(router=router)
    mission_id = await runtime.accept(Mission(objective="hard problem"))

    report = runtime.report(mission_id)
    assert report is not None
    assert report.verdict == "PASS"
    assert report.cost_usd == pytest.approx(0.02)
    assert [step["stage"] for step in report.actions] == ["small_model", "large_model"]
    assert report.actions[-1]["escalated"] is True


@pytest.mark.asyncio
async def test_unroutable_mission_fails_without_looping():
    router = AdaptiveRouter([LocalProvider(confidence=0.10), SecondaryProvider(confidence=0.20)])
    runtime = NexusRuntime(router=router)
    mission_id = await runtime.accept(Mission(objective="impossible"))

    report = runtime.report(mission_id)
    state = runtime.state_graph.get(UUID(mission_id))
    assert report is not None and state is not None
    assert report.verdict == "FAIL"
    assert state.status == "abandoned"
    assert "routing exhausted" in report.summary
    assert len(report.actions) == 2
    assert runtime.journal.verify_chain()


@pytest.mark.asyncio
async def test_report_and_journal_are_json_serialisable():
    router = AdaptiveRouter([LocalProvider(confidence=0.85)])
    runtime = NexusRuntime(router=router)
    mission_id = await runtime.accept(Mission(objective="serialise me"))
    report = runtime.report(mission_id)
    assert report is not None
    json.dumps(report.model_dump(mode="json"))
    for entry in runtime.journal.entries():
        json.dumps(entry.as_dict())


def test_updating_an_unknown_mission_fails_explicitly():
    runtime = NexusRuntime()
    with pytest.raises(UnknownMission):
        runtime.state_graph.update(
            UUID("00000000-0000-0000-0000-000000000009"), status="validated"
        )


@pytest.mark.asyncio
async def test_demo_entrypoint_runs_and_passes():
    from nexus.demo import run

    out = await run("demo objective", local_confidence=0.85, local_available=True)
    assert out["verdict"] == "PASS"
    assert out["journal_chain_valid"] is True
    assert out["events"] == ["MissionAccepted", "MissionValidated"]
    assert out["trace"][-1]["stage"] == "small_model"
