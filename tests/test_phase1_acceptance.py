import pytest

from nexus.providers import (
    CompletionRequest,
    CompletionResult,
    LocalProvider,
    ProviderCaps,
    ProviderHealth,
    SecondaryProvider,
)
from nexus.router import AdaptiveRouter, RoutingExhausted, RoutingPolicy


class StubProvider:
    """Configurable provider used to probe cascade ordering and cost tie-breaks."""

    def __init__(self, name, stage, confidence=0.9, cost=0.0, available=True):
        self.name, self.stage = name, stage
        self.confidence, self.cost, self.available = confidence, cost, available
        self.calls = 0

    async def health(self):
        return ProviderHealth(self.available, f"{self.name} stub")

    async def complete(self, request):
        self.calls += 1
        return CompletionResult(f"{self.name}:{request.prompt}", self.confidence, self.cost)

    def cost_estimate(self, request):
        return self.cost

    def capabilities(self):
        return ProviderCaps(context_window=1024, tools=False, json_mode=True)


@pytest.mark.asyncio
async def test_phase1_uses_cheapest_sufficient_provider():
    router = AdaptiveRouter([LocalProvider(confidence=0.80), SecondaryProvider()])
    result = await router.complete(CompletionRequest("simple task"))
    assert result.text.startswith("local:")
    assert router.decisions[-1].stage == "small_model"
    assert router.decisions[-1].escalated is False


@pytest.mark.asyncio
async def test_phase1_escalation_is_logged_and_justified():
    router = AdaptiveRouter([LocalProvider(confidence=0.20), SecondaryProvider(confidence=0.90)])
    result = await router.complete(CompletionRequest("hard task"))
    assert result.text.startswith("secondary:")
    assert [d.stage for d in router.decisions] == ["small_model", "large_model"]
    assert router.decisions[-1].escalated is True
    assert router.decisions[0].reason == "confidence threshold"


@pytest.mark.asyncio
async def test_phase1_unavailable_provider_is_skipped():
    router = AdaptiveRouter([LocalProvider(available=False), SecondaryProvider()])
    result = await router.complete(CompletionRequest("fallback"))
    assert result.text.startswith("secondary:")


@pytest.mark.asyncio
async def test_phase1_cache_avoids_second_provider_call():
    router = AdaptiveRouter([LocalProvider(confidence=0.80), SecondaryProvider()])
    first = await router.complete(CompletionRequest("cached"))
    second = await router.complete(CompletionRequest("cached"))
    assert first.text == second.text
    assert router.decisions[-1].stage == "cache"


@pytest.mark.asyncio
async def test_phase1_failure_is_bounded_and_explainable():
    router = AdaptiveRouter([LocalProvider(confidence=0.10), SecondaryProvider(confidence=0.20)])
    with pytest.raises(RuntimeError, match="routing exhausted"):
        await router.complete(CompletionRequest("impossible"))
    assert len(router.decisions) == 2


@pytest.mark.asyncio
async def test_phase1_provider_contract_is_complete():
    provider = LocalProvider()
    request = CompletionRequest("contract")
    assert (await provider.health()).available
    assert provider.cost_estimate(request) == 0.0
    assert provider.capabilities().json_mode is True


def test_phase1_policy_has_official_cascade():
    assert RoutingPolicy().stages == (
        "cache",
        "memory",
        "formal",
        "tool",
        "small_model",
        "large_model",
        "deep",
    )


# --- regressions found while closing Phase 1 -------------------------------


def test_phase1_router_package_exports_public_contract():
    """Regression: RoutingPolicy was missing from nexus.router, which made the
    whole Phase 1 test module fail at import time."""
    import nexus.router as router_pkg

    for symbol in (
        "AdaptiveRouter",
        "RoutingPolicy",
        "RoutingDecision",
        "RoutingExhausted",
        "load_policy",
        "OFFICIAL_STAGES",
    ):
        assert symbol in router_pkg.__all__
        assert hasattr(router_pkg, symbol)


@pytest.mark.asyncio
async def test_phase1_cascade_order_wins_over_declaration_order():
    """A mis-ordered provider list must not make the router skip a cheaper level."""
    router = AdaptiveRouter([SecondaryProvider(confidence=0.99), LocalProvider(confidence=0.80)])
    result = await router.complete(CompletionRequest("ordering"))
    assert result.text.startswith("local:")
    assert router.decisions[-1].stage == "small_model"
    assert router.decisions[-1].stage_rank < RoutingPolicy().stage_rank("large_model")


@pytest.mark.asyncio
async def test_phase1_cheapest_provider_wins_inside_a_stage():
    expensive = StubProvider("expensive", "small_model", confidence=0.95, cost=0.05)
    cheap = StubProvider("cheap", "small_model", confidence=0.95, cost=0.001)
    router = AdaptiveRouter([expensive, cheap])
    result = await router.complete(CompletionRequest("tie break"))
    assert result.text.startswith("cheap:")
    assert expensive.calls == 0


@pytest.mark.asyncio
async def test_phase1_provider_outside_the_cascade_is_never_called():
    rogue = StubProvider("rogue", "quantum_oracle", confidence=1.0)
    router = AdaptiveRouter([rogue, LocalProvider(confidence=0.80)])
    result = await router.complete(CompletionRequest("cascade guard"))
    assert rogue.calls == 0
    assert result.text.startswith("local:")


@pytest.mark.asyncio
async def test_phase1_critical_request_does_not_reuse_a_relaxed_cache_entry():
    provider = StubProvider("local", "small_model", confidence=0.90)
    router = AdaptiveRouter([provider])
    await router.complete(CompletionRequest("same prompt", critical=False))
    await router.complete(CompletionRequest("same prompt", critical=True))
    assert provider.calls == 2
    assert [d.stage for d in router.decisions] == ["small_model", "small_model"]


@pytest.mark.asyncio
async def test_phase1_cache_is_skipped_when_the_policy_excludes_it():
    provider = StubProvider("local", "small_model", confidence=0.90)
    policy = RoutingPolicy(stages=("small_model", "large_model"))
    router = AdaptiveRouter([provider], policy=policy)
    await router.complete(CompletionRequest("no cache"))
    await router.complete(CompletionRequest("no cache"))
    assert provider.calls == 2
    assert all(d.stage != "cache" for d in router.decisions)


@pytest.mark.asyncio
async def test_phase1_every_decision_carries_telemetry():
    router = AdaptiveRouter([LocalProvider(confidence=0.20), SecondaryProvider(confidence=0.90)])
    await router.complete(CompletionRequest("telemetry"))
    assert [d.attempt for d in router.decisions] == [0, 1]
    assert all(d.latency_ms >= 0.0 for d in router.decisions)
    assert router.total_cost_usd == pytest.approx(0.01)
    assert [step["provider"] for step in router.trace()] == ["ollama", "secondary"]


@pytest.mark.asyncio
async def test_phase1_exhaustion_names_the_skipped_providers():
    router = AdaptiveRouter([LocalProvider(available=False), SecondaryProvider(confidence=0.10)])
    with pytest.raises(RoutingExhausted) as excinfo:
        await router.complete(CompletionRequest("explain the failure"))
    message = str(excinfo.value)
    assert "attempted=1" in message
    assert "ollama" in message
