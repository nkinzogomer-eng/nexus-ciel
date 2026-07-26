from __future__ import annotations
from .base import CompletionRequest, CompletionResult, CostEstimate, ProviderCapabilities, ProviderHealth

class SecondaryProvider:
    name = "secondary"
    stage = "large_model"

    def __init__(self, confidence: float = 0.90, available: bool = True, cost_usd: float = 0.01) -> None:
        self.confidence, self.available, self.cost_usd = confidence, available, cost_usd

    async def health(self) -> ProviderHealth:
        return ProviderHealth(self.available, "secondary provider")

    async def estimate_cost(self, request: CompletionRequest) -> CostEstimate:
        tokens = max(1, len(request.prompt.split()))
        return CostEstimate(prompt_tokens=tokens, estimated_cost_usd=self.cost_usd)

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(supports_streaming=False, supports_tools=True, max_context_tokens=32768)

    async def complete(self, request: CompletionRequest) -> CompletionResult:
        estimate = await self.estimate_cost(request)
        return CompletionResult(
            f"secondary:{request.prompt}",
            self.confidence,
            self.cost_usd,
            prompt_tokens=estimate.prompt_tokens,
            completion_tokens=max(1, len(request.prompt.split()) + 1),
        )
