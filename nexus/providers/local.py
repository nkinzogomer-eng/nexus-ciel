from __future__ import annotations
from .base import CompletionRequest, CompletionResult, ProviderCaps, ProviderHealth

class LocalProvider:
    name = "ollama"
    stage = "small_model"
    def __init__(self, confidence: float = 0.80, available: bool = True) -> None:
        self.confidence, self.available = confidence, available
    async def health(self) -> ProviderHealth:
        return ProviderHealth(self.available, "local provider")
    async def complete(self, request: CompletionRequest) -> CompletionResult:
        return CompletionResult(f"local:{request.prompt}", self.confidence, 0.0)
    def cost_estimate(self, request: CompletionRequest) -> float:
        return 0.0
    def capabilities(self) -> ProviderCaps:
        return ProviderCaps(context_window=8192, tools=False, json_mode=True)
