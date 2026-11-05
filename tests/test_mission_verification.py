import pytest

from nexus.core import NexusRuntime
from nexus.providers import LocalProvider
from nexus.router import AdaptiveRouter
from nexus.schemas import Mission


@pytest.mark.asyncio
async def test_provider_confidence_alone_never_proves_mission_success():
    runtime = NexusRuntime(router=AdaptiveRouter([LocalProvider(confidence=0.99)]))
    mission = Mission(objective="unverified objective")
    mission_id = await runtime.accept(mission)

    report = runtime.report(mission_id)
    state = runtime.state_graph.get(mission.mission_id)

    assert report is not None
    assert report.verdict == "PARTIAL"
    assert report.validation["confidence_is_not_proof"] is True
    assert "no deterministic verification contract" in report.validation["verification"]["reason"]
    assert report.output == "local:unverified objective"
    assert state is not None and state.status == "partial"


@pytest.mark.asyncio
async def test_deterministic_contains_all_oracle_can_validate_output():
    runtime = NexusRuntime(router=AdaptiveRouter([LocalProvider(confidence=0.99)]))
    mission = Mission(
        objective="produce a result",
        constraints={"verification": {"mode": "contains_all", "needles": ["local:", "produce a result"]}},
    )
    mission_id = await runtime.accept(mission)

    report = runtime.report(mission_id)
    state = runtime.state_graph.get(mission.mission_id)
    assert report is not None and report.verdict == "PASS"
    assert state is not None and state.status == "validated"
    assert report.validation["criteria"][0]["passed"] is True


@pytest.mark.asyncio
async def test_failed_deterministic_oracle_does_not_mark_mission_validated():
    runtime = NexusRuntime(router=AdaptiveRouter([LocalProvider(confidence=0.99)]))
    mission = Mission(
        objective="produce a result",
        constraints={"verification": {"mode": "contains_all", "needles": ["independent-proof"]}},
    )
    mission_id = await runtime.accept(mission)

    report = runtime.report(mission_id)
    state = runtime.state_graph.get(mission.mission_id)
    assert report is not None and report.verdict == "FAIL"
    assert state is not None and state.status == "abandoned"
