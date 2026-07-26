from __future__ import annotations
from dataclasses import dataclass

OFFICIAL_CASCADE = (
    "cache",
    "memory",
    "formal",
    "tool",
    "small_model",
    "large_model",
    "deep_reasoning",
)

@dataclass(frozen=True)
class RoutingPolicy:
    version: str = "phase1-v1"
    stages: tuple[str, ...] = OFFICIAL_CASCADE
    confidence_threshold: float = 0.75

    @classmethod
    def default(cls) -> "RoutingPolicy":
        return cls()
