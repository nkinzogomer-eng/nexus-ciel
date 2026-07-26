"""Regressions found by running the system, not by reading it.

Each test here maps to a defect the Phase 1 suite happily declared green.
"""
from uuid import UUID

import pytest

from nexus.core import NexusRuntime
from nexus.core.mission_journal import MissionJournal
from nexus.providers import (
    CompletionRequest,
    ProviderCaps,
    ProviderHealth,
    SecondaryProvider,
)
from nexus.router import AdaptiveRouter, RoutingExhausted
from nexus.schemas import Mission

MISSION = UUID("00000000-0000-0000-0000-000000000001")


# --- the journal was tamper-tolerant --------------------------------------


def test_journal_detects_a_rewritten_payload():
    journal = MissionJournal()
    journal.append(MISSION, "decision", "manas", {"budget_usd": 5.0})
    journal.append(MISSION, "validation", "validation_engine", {"passed": True})
    assert journal.verify_chain()

    journal.entries()[0].payload["budget_usd"] = 999_999.0
    assert journal.verify_chain() is False
    assert journal.tampered_entries() == [1]


def test_journal_detects_a_rewritten_actor_or_type():
    journal = MissionJournal()
    journal.append(MISSION, "decision", "manas", {"ok": True})
    journal.entries()[0].actor = "evolution_engine"
    assert journal.verify_chain() is False

    other = MissionJournal()
    other.append(MISSION, "decision", "manas", {"ok": True})
    other.entries()[0].type = "validation"
    assert other.verify_chain() is False


def test_journal_detects_a_removed_entry():
    journal = MissionJournal()
    for index in range(3):
        journal.append(MISSION, f"step_{index}", "manas", {"i": index})
    del journal._entries[1]
    assert journal.verify_chain() is False


def test_untouched_journal_still_verifies():
    journal = MissionJournal()
    for index in range(5):
        journal.append(MISSION, f"step_{index}", "manas", {"i": index})
    assert journal.verify_chain()
    assert journal.tampered_entries() == []


# --- a cache hit was billed as if it had been paid -------------------------


@pytest.mark.asyncio
async def test_cache_hit_is_free_and_reports_what_it_avoided():
    router = AdaptiveRouter([SecondaryProvider(cost_usd=0.02)])
    await router.complete(CompletionRequest("expensive question"))
    assert router.total_cost_usd == pytest.approx(0.02)

    await router.complete(CompletionRequest("expensive question"))
    assert router.decisions[-1].stage == "cache"
    assert router.decisions[-1].cost_usd == 0.0
    assert router.decisions[-1].cost_avoided_usd == pytest.approx(0.02)
    assert router.total_cost_usd == pytest.approx(0.02)
    assert router.total_cost_avoided_usd == pytest.approx(0.02)


@pytest.mark.asyncio
async def test_a_cache_served_mission_reports_zero_cost():
    router = AdaptiveRouter([SecondaryProvider(cost_usd=0.02)])
    first = NexusRuntime(router=router)
    await first.accept(Mission(objective="same question"))

    second = NexusRuntime(router=router)
    mission_id = await second.accept(Mission(objective="same question"))
    report = second.report(mission_id)

    assert report is not None
    assert report.actions[-1]["stage"] == "cache"
    assert report.cost_usd == 0.0
    assert report.actions[-1]["cost_avoided_usd"] == pytest.approx(0.02)


# --- a provider raising killed the mission instead of escalating -----------


class ExplodingProvider:
    def __init__(self, name="flaky", stage="small_model", on_health=False):
        self.name, self.stage, self.on_health = name, stage, on_health
        self.calls = 0

    async def health(self):
        if self.on_health:
            raise TimeoutError("health probe timed out")
        return ProviderHealth(True, "pretends to be healthy")

    async def complete(self, request):
        self.calls += 1
        raise ConnectionError("connection refused")

    def cost_estimate(self, request):
        return 0.0

    def capabilities(self):
        return ProviderCaps(context_window=1024, tools=False, json_mode=True)


@pytest.mark.asyncio
async def test_a_raising_provider_escalates_instead_of_aborting():
    flaky = ExplodingProvider()
    router = AdaptiveRouter([flaky, SecondaryProvider(confidence=0.95)])
    result = await router.complete(CompletionRequest("survive a provider outage"))

    assert result.text.startswith("secondary:")
    assert flaky.calls == 1
    failure = router.decisions[0]
    assert failure.reason == "provider error"
    assert failure.confidence == 0.0
    assert failure.cost_usd == 0.0
    assert "ConnectionError" in (failure.error or "")
    assert router.decisions[-1].escalated is True


@pytest.mark.asyncio
async def test_a_raising_health_check_is_treated_as_unavailable():
    flaky = ExplodingProvider(on_health=True)
    router = AdaptiveRouter([flaky, SecondaryProvider(confidence=0.95)])
    result = await router.complete(CompletionRequest("broken health probe"))

    assert result.text.startswith("secondary:")
    assert flaky.calls == 0
    assert all(d.provider != "flaky" for d in router.decisions)


@pytest.mark.asyncio
async def test_every_provider_failing_still_fails_explicitly():
    router = AdaptiveRouter(
        [ExplodingProvider(), ExplodingProvider(name="flaky2", stage="large_model")]
    )
    with pytest.raises(RoutingExhausted) as excinfo:
        await router.complete(CompletionRequest("everything is down"))
    message = str(excinfo.value)
    assert "ConnectionError" in message
    assert "flaky2" in message
    assert len(router.decisions) == 2


@pytest.mark.asyncio
async def test_a_mission_survives_a_provider_outage_end_to_end():
    router = AdaptiveRouter([ExplodingProvider(), SecondaryProvider(confidence=0.95)])
    runtime = NexusRuntime(router=router)
    mission_id = await runtime.accept(Mission(objective="resilient mission"))
    report = runtime.report(mission_id)

    assert report is not None
    assert report.verdict == "PASS"
    assert [step["reason"] for step in report.actions] == ["provider error", "sufficient"]
    assert runtime.journal.verify_chain()


# --- the HTTP surface silently bypassed the cascade ------------------------


def test_http_surface_is_wired_to_the_cascade():
    from nexus.api.app import router as api_router, runtime as api_runtime

    assert api_runtime.router is api_router
    assert api_router.policy.source_path is not None
    assert api_router.policy.router_access == "read_only"


@pytest.mark.asyncio
async def test_http_surface_reports_a_real_routing_decision():
    from nexus.api.app import runtime as api_runtime

    mission_id = await api_runtime.accept(Mission(objective="routed through the api"))
    report = api_runtime.report(mission_id)
    assert report is not None
    assert report.summary != "Phase 0 trivial execution completed"
    assert report.actions
    assert report.actions[-1]["stage"] in {"cache", "small_model", "large_model"}


# --- the demo could not reach its own failure path -------------------------


@pytest.mark.asyncio
async def test_demo_can_reach_the_unroutable_path():
    from nexus.demo import run

    out = await run(
        "impossible objective",
        local_confidence=0.10,
        local_available=True,
        secondary_confidence=0.20,
    )
    assert out["verdict"] == "FAIL"
    assert out["state"] == "abandoned"
    assert out["journal_chain_valid"] is True
    assert "routing_exhausted" in out["journal_entries"]
