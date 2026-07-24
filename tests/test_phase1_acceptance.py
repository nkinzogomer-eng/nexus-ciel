import pytest
from nexus.providers import CompletionRequest, LocalProvider, SecondaryProvider
from nexus.router import AdaptiveRouter

@pytest.mark.asyncio
async def test_phase1_uses_cheapest_sufficient_provider():
    router = AdaptiveRouter([LocalProvider(confidence=0.80), SecondaryProvider()])
    result = await router.complete(CompletionRequest("simple task"))
    assert result.text.startswith("local:")
    assert router.decisions[-1].stage == "local_model"
    assert router.decisions[-1].escalated is False

@pytest.mark.asyncio
async def test_phase1_escalation_is_logged_and_justified():
    router = AdaptiveRouter([LocalProvider(confidence=0.20), SecondaryProvider(confidence=0.90)])
    result = await router.complete(CompletionRequest("hard task"))
    assert result.text.startswith("secondary:")
    assert [d.stage for d in router.decisions] == ["local_model", "standard_model"]
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
