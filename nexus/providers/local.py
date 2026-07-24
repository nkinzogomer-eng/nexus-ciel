from __future__ import annotations
from .base import CompletionRequest, CompletionResult, ProviderHealth

class LocalProvider:
    name = "ollama"
    stage = "local_model"
    def __init__(self, confidence: float = 0.80, available: bool = True) -> None:
        self.confidence, self.available = confidence, available
    async def health(self) -> ProviderHealth:
        return ProviderHealth(self.available, "local provider")
    async def complete(self, request: CompletionRequest) -> CompletionResult:
        return CompletionResult(f"local:{request.prompt}", self.confidence, 0.0)
