from __future__ import annotations
from dataclasses import dataclass
from typing import Protocol
from nexus.providers.base import CompletionRequest, CompletionResult, ProviderAdapter

OFFICIAL_STAGES = ("cache", "memory", "formal", "tool", "small_model", "large_model", "deep")

@dataclass(frozen=True)
class RoutingPolicy:
    version: int = 1
    confidence_threshold: float = 0.75
    stages: tuple[str, ...] = OFFICIAL_STAGES

@dataclass(frozen=True)
class RoutingDecision:
    stage: str
    provider: str
    confidence: float
    escalated: bool
    reason: str
    cost_usd: float = 0.0

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
    def __init__(self, providers: list[ProviderAdapter], cache: SemanticCache | None = None, policy: RoutingPolicy | None = None) -> None:
        self.providers = providers
        self.cache = cache or InMemorySemanticCache()
        self.policy = policy or RoutingPolicy()
        self.decisions: list[RoutingDecision] = []

    async def complete(self, request: CompletionRequest) -> CompletionResult:
        key = request.cache_key()
        cached = await self.cache.get(key)
        if cached is not None and cached.confidence >= self.policy.confidence_threshold:
            self.decisions.append(RoutingDecision("cache", "cache", cached.confidence, False, "cached result met policy threshold", cached.cost_usd))
            return cached
        for index, provider in enumerate(self.providers):
            if provider.stage not in self.policy.stages:
                continue
            health = await provider.health()
            if not health.available:
                continue
            result = await provider.complete(request)
            sufficient = result.confidence >= self.policy.confidence_threshold
            self.decisions.append(RoutingDecision(provider.stage, provider.name, result.confidence, index > 0, "sufficient" if sufficient else "confidence threshold", result.cost_usd))
            if sufficient:
                await self.cache.put(key, result)
                return result
        raise RuntimeError("routing exhausted: no available provider met the confidence threshold")
