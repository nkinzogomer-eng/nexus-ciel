from __future__ import annotations
from .base import CompletionRequest, CompletionResult, ProviderHealth

class SecondaryProvider:
    name = "secondary"
    stage = "standard_model"
    def __init__(self, confidence: float = 0.90, available: bool = True, cost_usd: float = 0.01) -> None:
        self.confidence, self.available, self.cost_usd = confidence, available, cost_usd
    async def health(self) -> ProviderHealth:
        return ProviderHealth(self.available, "secondary provider")
    async def complete(self, request: CompletionRequest) -> CompletionResult:
        return CompletionResult(f"secondary:{request.prompt}", self.confidence, self.cost_usd)
