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
        """Cache identity of the request.

        The ``critical`` flag is part of the key: a critical mission must
        never silently reuse an answer produced under relaxed conditions.
        """
        material = f"v1|{int(self.critical)}|{self.prompt}"
        return hashlib.sha256(material.encode("utf-8")).hexdigest()

@dataclass(frozen=True)
class ProviderCaps:
    context_window: int = 0
    tools: bool = False
    json_mode: bool = False

@dataclass(frozen=True)
class CompletionResult:
    text: str
    confidence: float
    cost_usd: float = 0.0
    latency_ms: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0

@dataclass(frozen=True)
class ProviderHealth:
    available: bool
    detail: str = ""

class ProviderAdapter(Protocol):
    name: str
    stage: str
    async def complete(self, request: CompletionRequest) -> CompletionResult: ...
    async def health(self) -> ProviderHealth: ...
    def cost_estimate(self, request: CompletionRequest) -> float: ...
    def capabilities(self) -> ProviderCaps: ...
