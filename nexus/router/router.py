from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Protocol

from nexus.providers.base import CompletionRequest, CompletionResult, ProviderAdapter

from .policy import OFFICIAL_STAGES, PolicyError, RoutingPolicy, load_policy

__all__ = [
    "OFFICIAL_STAGES",
    "AdaptiveRouter",
    "InMemorySemanticCache",
    "RoutingDecision",
    "RoutingExhausted",
    "RoutingPolicy",
    "SemanticCache",
]


class RoutingExhausted(RuntimeError):
    """No eligible provider produced a result above the policy threshold."""


@dataclass(frozen=True)
class RoutingDecision:
    stage: str
    provider: str
    confidence: float
    escalated: bool
    reason: str
    cost_usd: float = 0.0
    stage_rank: int = -1
    attempt: int = 0
    latency_ms: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0


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
    """Chooses the cheapest sufficient level of the official cascade.

    The policy is loaded from the versioned policy file and treated as
    read-only: the router holds no write path to it.
    """

    def __init__(
        self,
        providers: list[ProviderAdapter],
        cache: SemanticCache | None = None,
        policy: RoutingPolicy | None = None,
    ) -> None:
        self.providers = list(providers)
        self.cache = cache or InMemorySemanticCache()
        self.policy = policy if policy is not None else load_policy()
        if not self.policy.read_only_for_router:
            raise PolicyError(
                f"router requires router_access='read_only', got {self.policy.router_access!r}"
            )
        self.decisions: list[RoutingDecision] = []

    def eligible_providers(self, request: CompletionRequest) -> list[ProviderAdapter]:
        """Providers allowed by the policy, ordered by cascade rank then cost.

        Declaration order only breaks ties, so a mis-ordered provider list can
        never make the router skip a cheaper level.
        """
        allowed = [p for p in self.providers if self.policy.allows(p.stage)]
        return sorted(
            allowed,
            key=lambda p: (self.policy.stage_rank(p.stage), self._cost_of(p, request)),
        )

    @staticmethod
    def _cost_of(provider: ProviderAdapter, request: CompletionRequest) -> float:
        try:
            return float(provider.cost_estimate(request))
        except Exception:
            return float("inf")

    async def complete(self, request: CompletionRequest) -> CompletionResult:
        threshold = self.policy.confidence_threshold

        key: str | None = None
        if self.policy.allows("cache"):
            key = request.cache_key()
            cached = await self.cache.get(key)
            if cached is not None and cached.confidence >= threshold:
                self._record(
                    stage="cache",
                    provider="cache",
                    result=cached,
                    escalated=False,
                    reason="cached result met policy threshold",
                    attempt=0,
                )
                return cached

        attempt = 0
        skipped: list[str] = []
        for provider in self.eligible_providers(request):
            health = await provider.health()
            if not health.available:
                skipped.append(
                    f"{provider.name}({provider.stage}): {health.detail or 'unavailable'}"
                )
                continue
            started = time.perf_counter()
            result = await provider.complete(request)
            elapsed_ms = (time.perf_counter() - started) * 1000.0
            sufficient = result.confidence >= threshold
            self._record(
                stage=provider.stage,
                provider=provider.name,
                result=result,
                escalated=attempt > 0,
                reason="sufficient" if sufficient else "confidence threshold",
                attempt=attempt,
                measured_latency_ms=elapsed_ms,
            )
            attempt += 1
            if sufficient:
                if key is not None:
                    await self.cache.put(key, result)
                return result

        raise RoutingExhausted(
            "routing exhausted: no available provider met the confidence threshold "
            f"({threshold}); attempted={attempt}; "
            f"skipped=[{'; '.join(skipped) if skipped else 'none'}]"
        )

    def _record(
        self,
        *,
        stage: str,
        provider: str,
        result: CompletionResult,
        escalated: bool,
        reason: str,
        attempt: int,
        measured_latency_ms: float | None = None,
    ) -> None:
        self.decisions.append(
            RoutingDecision(
                stage=stage,
                provider=provider,
                confidence=result.confidence,
                escalated=escalated,
                reason=reason,
                cost_usd=result.cost_usd,
                stage_rank=self.policy.stage_rank(stage),
                attempt=attempt,
                latency_ms=(
                    result.latency_ms
                    if result.latency_ms
                    else (measured_latency_ms or 0.0)
                ),
                input_tokens=result.input_tokens,
                output_tokens=result.output_tokens,
            )
        )

    @property
    def total_cost_usd(self) -> float:
        return round(sum(d.cost_usd for d in self.decisions), 10)

    def trace(self) -> list[dict[str, object]]:
        """Human-readable escalation trace for reports and audits."""
        return [
            {
                "stage": d.stage,
                "provider": d.provider,
                "confidence": d.confidence,
                "escalated": d.escalated,
                "reason": d.reason,
                "cost_usd": d.cost_usd,
                "latency_ms": round(d.latency_ms, 3),
            }
            for d in self.decisions
        ]
