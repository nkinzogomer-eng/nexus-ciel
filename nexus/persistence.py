from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PersistenceStatus:
    backend: str
    crash_resumable: bool


def current_persistence_status() -> PersistenceStatus:
    """Truthful persistence status of the current prototype.

    Until a durable backend really owns the canonical state, every mission is
    bound to process memory and must report that it cannot survive a crash.
    """
    return PersistenceStatus(backend="memory", crash_resumable=False)
