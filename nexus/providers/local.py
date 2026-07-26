from __future__ import annotations
from .base import CompletionRequest, CompletionResult, CostEstimate, ProviderCapabilities, ProviderHealth

class LocalProvider:
    name = "ollama"
    stage = "small_model"

    def __init__(self, confidence: float = 0.80, available: bool = True) -> None:
        self.confidence, self.available = confidence, available

    async def health(self) -> ProviderHealth:
        return ProviderHealth(self.available, "local provider")

    async def estimate_cost(self, request: CompletionRequest) -> CostEstimate:
        return CostEstimate(prompt_tokens=max(1, len(request.prompt.split())), estimated_cost_usd=0.0)

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(supports_streaming=False, supports_tools=False, max_context_tokens=8192)

    async def complete(self, request: CompletionRequest) -> CompletionResult:
        estimate = await self.estimate_cost(request)
        return CompletionResult(
            f"local:{request.prompt}",
            self.confidence,
            0.0,
            prompt_tokens=estimate.prompt_tokens,
            completion_tokens=max(1, len(request.prompt.split())),
        )
