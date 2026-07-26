from __future__ import annotations

import json
from datetime import datetime
from uuid import UUID

from nexus.core import NexusRuntime
from nexus.core.capability_registry import CapabilityRegistry
from nexus.core.mission_journal import JournalEntry, MissionJournal
from nexus.core.state_graph import StateGraph
from nexus.schemas import Capability, Mission, MissionState, Report

from .postgres import PostgresSnapshotStore


class PersistentStateGraph(StateGraph):
    def __init__(self, states, on_change=None):
        super().__init__()
        self._states = {state.mission_id: state for state in states}
        self._on_change = on_change

    def get(self, mission_id):
        if isinstance(mission_id, str):
            mission_id = UUID(mission_id)
        return super().get(mission_id)

    def create(self, mission):
        state = super().create(mission).model_copy(update={"resumable_after_crash": True})
        self._states[mission.mission_id] = state
        if self._on_change:
            self._on_change()
        return state

    def update(self, mission_id, **changes):
        updated = super().update(mission_id, **changes).model_copy(update={"resumable_after_crash": True})
        self._states[mission_id] = updated
        if self._on_change:
            self._on_change()
        return updated


class PersistentMissionJournal(MissionJournal):
    def __init__(self, entries):
        super().__init__()
        self._entries = entries


class PersistentRuntime(NexusRuntime):
    """Runtime facade that loads and commits the canonical state to PostgreSQL."""

    def __init__(self, store: PostgresSnapshotStore, router=None):
        super().__init__(router=router)
        data = store.load()
        self._store = store
        self.state_graph = PersistentStateGraph(self._states_from(data))
        self.journal = PersistentMissionJournal(self._journal_from(data))
        self.registry = self._registry_from(data)
        self.reports = self._reports_from(data)

    @staticmethod
    def _states_from(data):
        return [MissionState(mission_id=UUID(row[0]), objective=row[1], status=row[2], iterations=row[3], resumable_after_crash=True) for row in data["states"]]

    @staticmethod
    def _reports_from(data):
        result = {}
        for row in data["reports"]:
            actions, validation, learned, guard_events = (json.loads(value) if isinstance(value, str) else value for value in row[7:11])
            result[str(row[0])] = Report(mission_id=UUID(row[0]), verdict=row[1], objective=row[2], summary=row[3], iterations=row[4], cost_usd=row[5], duration_s=row[6], actions=actions, validation=validation, learned=learned, guard_events=guard_events, generated_at=row[11])
        return result

    @staticmethod
    def _journal_from(data):
        entries = []
        for row in data["journal"]:
            payload = json.loads(row[4]) if isinstance(row[4], str) else row[4]
            entry = JournalEntry(int(row[0]), UUID(row[1]), row[2], row[3], payload, row[5], row[6])
            entry.timestamp = row[7].isoformat() if hasattr(row[7], "isoformat") else row[7]
            entries.append(entry)
        return entries

    @staticmethod
    def _registry_from(data):
        registry = CapabilityRegistry()
        for row in data["capabilities"]:
            stats = json.loads(row[6]) if isinstance(row[6], str) else row[6]
            registry.register(Capability(id=UUID(row[0]), name=row[1], description=row[2], type=row[3], status=row[4], version=row[5], stats=stats))
        return registry

    async def accept(self, mission: Mission) -> str:
        mission_id = await super().accept(mission)
        self._store.save_runtime(self)
        return mission_id
