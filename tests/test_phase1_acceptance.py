import pytest
from nexus.providers import CompletionRequest, CostEstimate, LocalProvider, ProviderCapabilities, SecondaryProvider
from nexus.router import AdaptiveRouter, OFFICIAL_CASCADE, RoutingPolicy

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
async def test_phase1_unavailable_provider_is_skipped_with_telemetry():
    router = AdaptiveRouter([LocalProvider(available=False), SecondaryProvider()])
    result = await router.complete(CompletionRequest("fallback"))
    assert result.text.startswith("secondary:")
    assert router.telemetry[0].reason.startswith("unavailable:")
    assert router.telemetry[0].stage == "small_model"
    assert router.telemetry[-1].success is True

@pytest.mark.asyncio
async def test_phase1_cache_avoids_second_provider_call():
    router = AdaptiveRouter([LocalProvider(confidence=0.80), SecondaryProvider()])
    first = await router.complete(CompletionRequest("cached"))
    second = await router.complete(CompletionRequest("cached"))
    assert first.text == second.text
    assert router.decisions[-1].stage == "cache"
    assert router.telemetry[-1].provider == "cache"

@pytest.mark.asyncio
async def test_phase1_provider_contract_exposes_cost_and_capabilities():
    provider = SecondaryProvider(cost_usd=0.02)
    estimate = await provider.estimate_cost(CompletionRequest("measure cost"))
    capabilities = provider.capabilities()
    assert isinstance(estimate, CostEstimate)
    assert estimate.estimated_cost_usd == 0.02
    assert isinstance(capabilities, ProviderCapabilities)
    assert capabilities.supports_tools is True
    assert capabilities.max_context_tokens >= 32768

@pytest.mark.asyncio
async def test_phase1_policy_is_versioned_and_read_only():
    router = AdaptiveRouter([LocalProvider()], policy=RoutingPolicy.default())
    assert router.routing_policy.version == "phase1-v1"
    assert router.routing_policy.stages == OFFICIAL_CASCADE
    with pytest.raises(Exception):
        router.routing_policy.version = "mutated"

@pytest.mark.asyncio
async def test_phase1_bounded_failure_is_explicit_and_explainable():
    router = AdaptiveRouter([LocalProvider(confidence=0.10), SecondaryProvider(confidence=0.20)])
    with pytest.raises(RuntimeError, match="no provider produced a result meeting the confidence threshold after 2 attempts"):
        await router.complete(CompletionRequest("hopeless"))
    assert [item.success for item in router.telemetry] == [False, False]
    assert [item.stage for item in router.telemetry] == ["small_model", "large_model"]
