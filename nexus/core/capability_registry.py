from __future__ import annotations
from uuid import UUID
from nexus.schemas import Capability

class CapabilityRegistry:
    def __init__(self) -> None:
        self._capabilities: dict[UUID, Capability] = {}

    def register(self, capability: Capability) -> Capability:
        self._capabilities[capability.id] = capability
        return capability

    def list(self) -> list[Capability]:
        return list(self._capabilities.values())

    def get(self, capability_id: UUID) -> Capability | None:
        return self._capabilities.get(capability_id)
