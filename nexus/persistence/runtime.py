from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol
from uuid import UUID

from nexus.core import NexusRuntime
from nexus.core.capability_registry import CapabilityRegistry
from nexus.core.mission_journal import JournalEntry, MissionJournal
from nexus.core.state_graph import StateGraph
from nexus.schemas import Capability, Mission, MissionState, Report


class SnapshotStore(Protocol):
    def load(self) -> dict[str, Any] | None: ...

    def save(self, snapshot: dict[str, Any]) -> None: ...


class FileSnapshotStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def load(self) -> dict[str, Any] | None:
        if not self.path.is_file():
            return None
        return json.loads(self.path.read_text(encoding="utf-8"))

    def save(self, snapshot: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(json.dumps(snapshot, indent=2, sort_keys=True), encoding="utf-8")
        tmp.replace(self.path)


class PersistentStateGraph(StateGraph):
    def __init__(self, states: list[MissionState], on_change) -> None:
        super().__init__()
        self._states = {
            state.mission_id: state.model_copy(update={"resumable_after_crash": True})
            for state in states
        }
        self._on_change = on_change

    def create(self, mission: Mission) -> MissionState:
        state = MissionState(
            mission_id=mission.mission_id,
            objective=mission.objective,
            resumable_after_crash=True,
        )
        self._states[mission.mission_id] = state
        self._on_change()
        return state

    def update(self, mission_id: UUID, **changes: object) -> MissionState:
        updated = super().update(mission_id, **changes)
        if not updated.resumable_after_crash:
            updated = updated.model_copy(update={"resumable_after_crash": True})
            self._states[mission_id] = updated
        self._on_change()
        return updated


class PersistentMissionJournal(MissionJournal):
    def __init__(self, entries: list[JournalEntry], on_change) -> None:
        super().__init__()
        self._entries = list(entries)
        self._on_change = on_change

    def append(
        self,
        mission_id: UUID,
        event_type: str,
        actor: str,
        payload: dict[str, Any] | None = None,
    ) -> JournalEntry:
        entry = super().append(mission_id, event_type, actor, payload)
        self._on_change()
        return entry


class PersistentCapabilityRegistry(CapabilityRegistry):
    def __init__(self, capabilities: list[Capability], on_change) -> None:
        super().__init__()
        self._capabilities = {capability.id: capability for capability in capabilities}
        self._on_change = on_change

    def register(self, capability: Capability) -> Capability:
        registered = super().register(capability)
        self._on_change()
        return registered


class PersistentReportStore(dict[str, Report]):
    def __init__(self, initial: dict[str, Report], on_change) -> None:
        super().__init__(initial)
        self._on_change = on_change

    def __setitem__(self, key: str, value: Report) -> None:
        super().__setitem__(key, value)
        self._on_change()


class PersistentRuntime(NexusRuntime):
    SNAPSHOT_SCHEMA_VERSION = 1
    INTERRUPTION_POLICY = "controlled_abandon"

    def __init__(self, store: SnapshotStore, router: object | None = None) -> None:
        self._store = store
        self._loading = True
        self.recovered_interruptions: list[str] = []
        super().__init__(router=router)
        snapshot = store.load() or self._empty_snapshot()
        self._validate_snapshot(snapshot)
        self.state_graph = PersistentStateGraph(self._load_states(snapshot), self._flush)
        self.journal = PersistentMissionJournal(self._load_entries(snapshot), self._flush)
        self.registry = PersistentCapabilityRegistry(
            self._load_capabilities(snapshot),
            self._flush,
        )
        self.reports = PersistentReportStore(self._load_reports(snapshot), self._flush)
        self._reconcile_interrupted_missions()
        self._loading = False
        self._flush()

    def _validate_snapshot(self, snapshot: dict[str, Any]) -> None:
        if snapshot.get("schema_version") != self.SNAPSHOT_SCHEMA_VERSION:
            raise ValueError(
                f"unsupported runtime snapshot schema: {snapshot.get('schema_version')!r}"
            )

    def _empty_snapshot(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "saved_at": None,
            "states": [],
            "journal": [],
            "capabilities": [],
            "reports": {},
        }

    def _load_states(self, snapshot: dict[str, Any]) -> list[MissionState]:
        return [
            MissionState.model_validate(item).model_copy(update={"resumable_after_crash": True})
            for item in snapshot.get("states", [])
        ]

    def _load_entries(self, snapshot: dict[str, Any]) -> list[JournalEntry]:
        entries: list[JournalEntry] = []
        for item in snapshot.get("journal", []):
            entry = JournalEntry(
                int(item["seq"]),
                UUID(item["mission_id"]),
                item["type"],
                item["actor"],
                item.get("payload", {}),
                item["signature"],
                item["precedent_hash"],
            )
            entry.timestamp = item["timestamp"]
            entries.append(entry)
        return entries

    def _load_capabilities(self, snapshot: dict[str, Any]) -> list[Capability]:
        return [Capability.model_validate(item) for item in snapshot.get("capabilities", [])]

    def _load_reports(self, snapshot: dict[str, Any]) -> dict[str, Report]:
        return {
            mission_id: Report.model_validate(report)
            for mission_id, report in snapshot.get("reports", {}).items()
        }

    def _reconcile_interrupted_missions(self) -> None:
        interrupted = [
            state
            for state in self.state_graph._states.values()
            if state.status == "in_progress"
        ]
        for state in interrupted:
            self.state_graph._states[state.mission_id] = state.model_copy(
                update={"status": "abandoned", "resumable_after_crash": True}
            )
            self.reports[str(state.mission_id)] = Report(
                mission_id=state.mission_id,
                verdict="FAIL",
                objective=state.objective,
                summary=(
                    "mission interrupted by crash; durable state recovered but "
                    "automatic resume is disabled"
                ),
                iterations=max(state.iterations, 1),
                actions=[
                    {
                        "stage": "recovery",
                        "provider": "persistent_runtime",
                        "reason": "controlled abandon",
                        "escalated": False,
                        "cost_usd": 0.0,
                        "cost_avoided_usd": 0.0,
                    }
                ],
                validation={
                    "criteria": [
                        {"name": "durable state recovered", "passed": True},
                        {
                            "name": "automatic resume disabled by policy",
                            "passed": False,
                        },
                    ],
                    "recovery_policy": self.INTERRUPTION_POLICY,
                },
            )
            self.journal.append(
                state.mission_id,
                "mission_interrupted",
                "persistent_runtime",
                {
                    "policy": self.INTERRUPTION_POLICY,
                    "previous_status": "in_progress",
                    "new_status": "abandoned",
                },
            )
            self.recovered_interruptions.append(str(state.mission_id))

    def _flush(self) -> None:
        if not self._loading:
            self._store.save(self._serialize())

    def _serialize(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "saved_at": datetime.now(timezone.utc).isoformat(),
            "states": [
                state.model_copy(update={"resumable_after_crash": True}).model_dump(
                    mode="json"
                )
                for state in self.state_graph._states.values()
            ],
            "journal": [entry.as_dict() for entry in self.journal.entries()],
            "capabilities": [capability.model_dump(mode="json") for capability in self.registry.list()],
            "reports": {
                mission_id: report.model_dump(mode="json")
                for mission_id, report in self.reports.items()
            },
        }
