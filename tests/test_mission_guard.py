import pytest

from nexus.core import NexusRuntime
from nexus.providers import CompletionResult, LocalProvider, ProviderCaps, ProviderHealth, SecondaryProvider
from nexus.router import AdaptiveRouter
from nexus.schemas import Mission


class UnderestimatingProvider:
    name = "underestimator"
    stage = "large_model"

    async def health(self):
        return ProviderHealth(True)

    async def complete(self, request):
        return CompletionResult("answer", 0.99, cost_usd=0.20)

    def cost_estimate(self, request):
        return 0.01

    def capabilities(self):
        return ProviderCaps(context_window=1000)


@pytest.mark.asyncio
async def test_provider_over_budget_is_not_called():
    provider = SecondaryProvider(cost_usd=0.10)
    runtime = NexusRuntime(router=AdaptiveRouter([provider]))
    mission = Mission(
        objective="expensive task",
        constraints={
            "budget_usd": 0.01,
            "verification": {"mode": "non_empty"},
        },
    )
    mission_id = await runtime.accept(mission)

    report = runtime.report(mission_id)
    assert report is not None and report.verdict == "FAIL"
    assert "exceeds mission budget" in report.summary
    assert report.cost_usd == 0.0


@pytest.mark.asyncio
async def test_provider_actual_charge_over_budget_is_reported_as_failure():
    runtime = NexusRuntime(router=AdaptiveRouter([UnderestimatingProvider()]))
    mission = Mission(
        objective="provider overrun",
        constraints={
            "budget_usd": 0.05,
            "verification": {"mode": "non_empty"},
        },
    )
    mission_id = await runtime.accept(mission)

    report = runtime.report(mission_id)
    assert report is not None and report.verdict == "FAIL"
    assert "mission budget exceeded" in report.summary
    assert report.cost_usd == pytest.approx(0.20)
    assert report.actions[-1]["reason"] == "provider exceeded mission budget"


@pytest.mark.asyncio
async def test_invalid_budget_is_rejected_before_provider_execution():
    provider = LocalProvider()
    runtime = NexusRuntime(router=AdaptiveRouter([provider]))
    mission = Mission(
        objective="invalid budget",
        constraints={"budget_usd": float("nan")},
    )
    mission_id = await runtime.accept(mission)

    report = runtime.report(mission_id)
    assert report is not None and report.verdict == "FAIL"
    assert report.guard_events[0]["type"] == "invalid_budget"
    assert report.actions == []


class CostlyProvider:
    def __init__(self, name, stage, confidence, cost):
        self.name, self.stage = name, stage
        self.confidence, self.cost = confidence, cost
        self.calls = 0

    async def health(self):
        return ProviderHealth(True)

    async def complete(self, request):
        self.calls += 1
        return CompletionResult(f"{self.name} answer", self.confidence, cost_usd=self.cost)

    def cost_estimate(self, request):
        return self.cost

    def capabilities(self):
        return ProviderCaps(context_window=1000)


@pytest.mark.asyncio
async def test_mission_budget_is_shared_across_escalation_attempts():
    first = CostlyProvider("first", "small_model", confidence=0.20, cost=0.04)
    second = CostlyProvider("second", "large_model", confidence=0.99, cost=0.04)
    runtime = NexusRuntime(router=AdaptiveRouter([first, second]))
    mission = Mission(
        objective="cumulative budget",
        constraints={"budget_usd": 0.05},
    )
    mission_id = await runtime.accept(mission)

    report = runtime.report(mission_id)
    assert report is not None and report.verdict == "FAIL"
    assert first.calls == 1
    assert second.calls == 0
    assert report.cost_usd == pytest.approx(0.04)
    assert "exceeds mission budget" in report.summary
