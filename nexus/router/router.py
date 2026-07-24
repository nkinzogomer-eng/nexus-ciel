from __future__ import annotations
from dataclasses import dataclass
from typing import Protocol
from nexus.providers.base import CompletionRequest, CompletionResult, ProviderAdapter

@dataclass(frozen=True)
class RoutingDecision:
    stage: str
    provider: str
    confidence: float
    escalated: bool
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
    def __init__(self, providers: list[ProviderAdapter], cache: SemanticCache | None = None, confidence_threshold: float = 0.75) -> None:
        self.providers = providers
        self.cache = cache or InMemorySemanticCache()
        self.confidence_threshold = confidence_threshold
        self.decisions: list[RoutingDecision] = []

    async def complete(self, request: CompletionRequest) -> CompletionResult:
        key = request.cache_key()
        cached = await self.cache.get(key)
        if cached is not None and cached.confidence >= self.confidence_threshold:
            self.decisions.append(RoutingDecision("cache", "cache", cached.confidence, False, "cached result met threshold"))
            return cached
        for index, provider in enumerate(self.providers):
            health = await provider.health()
            if not health.available:
                continue
            result = await provider.complete(request)
            stage = provider.stage
            self.decisions.append(RoutingDecision(stage, provider.name, result.confidence, index > 0, "confidence threshold" if result.confidence < self.confidence_threshold else "sufficient"))
            if result.confidence >= self.confidence_threshold:
                await self.cache.put(key, result)
                return result
        raise RuntimeError("no provider produced a result meeting the confidence threshold")
