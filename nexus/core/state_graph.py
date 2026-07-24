from __future__ import annotations
from uuid import UUID
from nexus.schemas import Mission, MissionState

class StateGraph:
    def __init__(self) -> None:
        self._states: dict[UUID, MissionState] = {}

    def create(self, mission: Mission) -> MissionState:
        state = MissionState(mission_id=mission.mission_id, objective=mission.objective)
        self._states[mission.mission_id] = state
        return state

    def get(self, mission_id: UUID) -> MissionState | None:
        return self._states.get(mission_id)

    def update(self, mission_id: UUID, **changes: object) -> MissionState:
        current = self._states[mission_id]
        updated = current.model_copy(update=changes)
        self._states[mission_id] = updated
        return updated
