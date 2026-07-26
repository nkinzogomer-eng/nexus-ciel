from __future__ import annotations
from dataclasses import dataclass
from typing import Protocol
import hashlib

@dataclass(frozen=True)
class CompletionRequest:
    prompt: str
    mission_id: str | None = None
    critical: bool = False

    def cache_key(self) -> str:
        return hashlib.sha256(self.prompt.encode()).hexdigest()

@dataclass(frozen=True)
class CompletionResult:
    text: str
    confidence: float
    cost_usd: float = 0.0
    prompt_tokens: int | None = None
    completion_tokens: int | None = None

@dataclass(frozen=True)
class CostEstimate:
    prompt_tokens: int
    estimated_cost_usd: float

@dataclass(frozen=True)
class ProviderCapabilities:
    supports_streaming: bool = False
    supports_tools: bool = False
    max_context_tokens: int = 0

@dataclass(frozen=True)
class ProviderHealth:
    available: bool
    detail: str = ""

class ProviderAdapter(Protocol):
    name: str
    stage: str

    async def complete(self, request: CompletionRequest) -> CompletionResult: ...
    async def health(self) -> ProviderHealth: ...
    async def estimate_cost(self, request: CompletionRequest) -> CostEstimate: ...
    def capabilities(self) -> ProviderCapabilities: ...
