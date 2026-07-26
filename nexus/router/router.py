from __future__ import annotations
from dataclasses import dataclass
from time import perf_counter
from typing import Protocol
from nexus.providers.base import CompletionRequest, CompletionResult, ProviderAdapter
from .policy import RoutingPolicy

@dataclass(frozen=True)
class RoutingDecision:
    stage: str
    provider: str
    confidence: float
    escalated: bool
    reason: str

@dataclass(frozen=True)
class RoutingTelemetry:
    stage: str
    provider: str
    latency_ms: float
    estimated_cost_usd: float
    actual_cost_usd: float
    prompt_tokens: int | None
    completion_tokens: int | None
    success: bool
    reason: str

class SemanticCache(Protocol):
    async def get(self, key: str) -> CompletionResult | None: ...
    async def put(self, key: str, result: CompletionResult) -> None: ...

class InMemorySemanticCache:
    def __init__(self) -> None:
        self._items: dict[str, CompletionResult] = {}

    async def get(self, key: str) -> CompletionResult | None:
        return self._items.get(key)

    async def put(self, key: str, result: CompletionResult) -> None:
        self._items[key] = result

class AdaptiveRouter:
    def __init__(
        self,
        providers: list[ProviderAdapter],
        cache: SemanticCache | None = None,
        confidence_threshold: float | None = None,
        policy: RoutingPolicy | None = None,
    ) -> None:
        self.providers = providers
        self.cache = cache or InMemorySemanticCache()
        self.routing_policy = policy or RoutingPolicy.default()
        if confidence_threshold is not None:
            self.routing_policy = RoutingPolicy(
                version=self.routing_policy.version,
                stages=self.routing_policy.stages,
                confidence_threshold=confidence_threshold,
            )
        self.confidence_threshold = self.routing_policy.confidence_threshold
        self.decisions: list[RoutingDecision] = []
        self.telemetry: list[RoutingTelemetry] = []

    async def complete(self, request: CompletionRequest) -> CompletionResult:
        key = request.cache_key()
        cached = await self.cache.get(key)
        if cached is not None and cached.confidence >= self.confidence_threshold:
            self.decisions.append(RoutingDecision("cache", "cache", cached.confidence, False, "cached result met threshold"))
            self.telemetry.append(
                RoutingTelemetry(
                    stage="cache",
                    provider="cache",
                    latency_ms=0.0,
                    estimated_cost_usd=0.0,
                    actual_cost_usd=0.0,
                    prompt_tokens=cached.prompt_tokens,
                    completion_tokens=cached.completion_tokens,
                    success=True,
                    reason="cached result met threshold",
                )
            )
            return cached

        attempts: list[str] = []
        available_attempts = 0
        for provider in self.providers:
            start = perf_counter()
            health = await provider.health()
            estimate = await provider.estimate_cost(request)
            if not health.available:
                self.telemetry.append(
                    RoutingTelemetry(
                        stage=provider.stage,
                        provider=provider.name,
                        latency_ms=(perf_counter() - start) * 1000,
                        estimated_cost_usd=estimate.estimated_cost_usd,
                        actual_cost_usd=0.0,
                        prompt_tokens=estimate.prompt_tokens,
                        completion_tokens=None,
                        success=False,
                        reason=f"unavailable: {health.detail}",
                    )
                )
                continue

            available_attempts += 1
            result = await provider.complete(request)
            latency_ms = (perf_counter() - start) * 1000
            reason = "sufficient" if result.confidence >= self.confidence_threshold else "confidence threshold"
            attempts.append(f"{provider.name}@{provider.stage}={result.confidence:.2f}")
            self.decisions.append(
                RoutingDecision(
                    provider.stage,
                    provider.name,
                    result.confidence,
                    available_attempts > 1,
                    reason,
                )
            )
            self.telemetry.append(
                RoutingTelemetry(
                    stage=provider.stage,
                    provider=provider.name,
                    latency_ms=latency_ms,
                    estimated_cost_usd=estimate.estimated_cost_usd,
                    actual_cost_usd=result.cost_usd,
                    prompt_tokens=result.prompt_tokens or estimate.prompt_tokens,
                    completion_tokens=result.completion_tokens,
                    success=result.confidence >= self.confidence_threshold,
                    reason=reason,
                )
            )
            if result.confidence >= self.confidence_threshold:
                await self.cache.put(key, result)
                return result

        detail = ", ".join(attempts) if attempts else "no available providers"
        raise RuntimeError(
            "no provider produced a result meeting the confidence threshold after "
            f"{available_attempts} attempts: {detail}"
        )
