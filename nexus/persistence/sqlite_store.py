from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator
from uuid import UUID

from nexus.core.mission_journal import JournalEntry
from nexus.schemas import Capability, Mission, MissionState, Report


@dataclass(frozen=True)
class PendingMission:
    mission: Mission
    state: MissionState


class SqliteRuntimeStore:
    """Deterministic checkpoint store for the current runtime contract.

    SQLite keeps the acceptance tests self-contained. The schema is relational
    on purpose so the same canonical sources can later move under Postgres
    without changing what gets checkpointed.
    """

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.path)
        try:
            conn.row_factory = sqlite3.Row
            yield conn
            conn.commit()
        finally:
            conn.close()

    def initialise(self) -> None:
        with self.connect() as conn:
            conn.executescript(
                """
                PRAGMA foreign_keys = ON;

                CREATE TABLE IF NOT EXISTS missions (
                    mission_id TEXT PRIMARY KEY,
                    mission_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS mission_states (
                    mission_id TEXT PRIMARY KEY,
                    state_json TEXT NOT NULL,
                    status TEXT NOT NULL,
                    checkpointed_at TEXT,
                    FOREIGN KEY (mission_id) REFERENCES missions (mission_id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS journal_entries (
                    seq INTEGER PRIMARY KEY,
                    mission_id TEXT NOT NULL,
                    entry_json TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    FOREIGN KEY (mission_id) REFERENCES missions (mission_id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS capabilities (
                    capability_id TEXT PRIMARY KEY,
                    capability_json TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS reports (
                    mission_id TEXT PRIMARY KEY,
                    report_json TEXT NOT NULL,
                    FOREIGN KEY (mission_id) REFERENCES missions (mission_id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS router_decisions (
                    mission_id TEXT NOT NULL,
                    decision_index INTEGER NOT NULL,
                    decision_json TEXT NOT NULL,
                    PRIMARY KEY (mission_id, decision_index),
                    FOREIGN KEY (mission_id) REFERENCES missions (mission_id) ON DELETE CASCADE
                );
                """
            )

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def checkpoint_runtime(self, runtime: object) -> None:
        self.initialise()
        missions = getattr(runtime, "_missions", {})
        with self.connect() as conn:
            for mission in missions.values():
                conn.execute(
                    """
                    INSERT INTO missions (mission_id, mission_json, created_at)
                    VALUES (?, ?, ?)
                    ON CONFLICT(mission_id) DO UPDATE SET
                      mission_json=excluded.mission_json,
                      created_at=excluded.created_at
                    """,
                    (
                        str(mission.mission_id),
                        json.dumps(mission.model_dump(mode="json"), sort_keys=True),
                        mission.created_at.isoformat(),
                    ),
                )

            for state in runtime.state_graph._states.values():
                conn.execute(
                    """
                    INSERT INTO mission_states (mission_id, state_json, status, checkpointed_at)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(mission_id) DO UPDATE SET
                      state_json=excluded.state_json,
                      status=excluded.status,
                      checkpointed_at=excluded.checkpointed_at
                    """,
                    (
                        str(state.mission_id),
                        json.dumps(state.model_dump(mode="json"), sort_keys=True),
                        state.status,
                        state.checkpointed_at.isoformat() if state.checkpointed_at else None,
                    ),
                )

            for entry in runtime.journal.entries():
                payload = entry.as_dict()
                conn.execute(
                    """
                    INSERT INTO journal_entries (seq, mission_id, entry_json, timestamp)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(seq) DO UPDATE SET
                      mission_id=excluded.mission_id,
                      entry_json=excluded.entry_json,
                      timestamp=excluded.timestamp
                    """,
                    (
                        entry.seq,
                        str(entry.mission_id),
                        json.dumps(payload, sort_keys=True),
                        entry.timestamp,
                    ),
                )

            for capability in runtime.registry.list():
                conn.execute(
                    """
                    INSERT INTO capabilities (capability_id, capability_json)
                    VALUES (?, ?)
                    ON CONFLICT(capability_id) DO UPDATE SET capability_json=excluded.capability_json
                    """,
                    (
                        str(capability.id),
                        json.dumps(capability.model_dump(mode="json"), sort_keys=True),
                    ),
                )

            for mission_id, report in runtime.reports.items():
                conn.execute(
                    """
                    INSERT INTO reports (mission_id, report_json)
                    VALUES (?, ?)
                    ON CONFLICT(mission_id) DO UPDATE SET report_json=excluded.report_json
                    """,
                    (mission_id, json.dumps(report.model_dump(mode="json"), sort_keys=True)),
                )
                conn.execute("DELETE FROM router_decisions WHERE mission_id = ?", (mission_id,))
                for index, decision in enumerate(report.actions):
                    conn.execute(
                        """
                        INSERT INTO router_decisions (mission_id, decision_index, decision_json)
                        VALUES (?, ?, ?)
                        """,
                        (mission_id, index, json.dumps(decision, sort_keys=True)),
                    )

    def _load_missions(self) -> dict[str, Mission]:
        self.initialise()
        with self.connect() as conn:
            rows = conn.execute("SELECT mission_id, mission_json FROM missions ORDER BY created_at").fetchall()
        return {row["mission_id"]: Mission.model_validate_json(row["mission_json"]) for row in rows}

    def _load_states(self) -> dict[UUID, MissionState]:
        self.initialise()
        with self.connect() as conn:
            rows = conn.execute("SELECT state_json FROM mission_states ORDER BY mission_id").fetchall()
        states = [MissionState.model_validate_json(row["state_json"]) for row in rows]
        return {state.mission_id: state for state in states}

    def _load_entries(self) -> list[JournalEntry]:
        self.initialise()
        with self.connect() as conn:
            rows = conn.execute("SELECT entry_json FROM journal_entries ORDER BY seq").fetchall()
        entries: list[JournalEntry] = []
        for row in rows:
            data = json.loads(row["entry_json"])
            entry = JournalEntry(
                seq=int(data["seq"]),
                mission_id=UUID(data["mission_id"]),
                event_type=data["type"],
                actor=data["actor"],
                payload=data["payload"],
                signature=data["signature"],
                previous_hash=data["precedent_hash"],
            )
            entry.timestamp = data["timestamp"]
            entries.append(entry)
        return entries

    def _load_capabilities(self) -> dict[UUID, Capability]:
        self.initialise()
        with self.connect() as conn:
            rows = conn.execute("SELECT capability_json FROM capabilities ORDER BY capability_id").fetchall()
        capabilities = [Capability.model_validate_json(row["capability_json"]) for row in rows]
        return {cap.id: cap for cap in capabilities}

    def _load_reports(self) -> dict[str, Report]:
        self.initialise()
        with self.connect() as conn:
            rows = conn.execute("SELECT mission_id, report_json FROM reports ORDER BY mission_id").fetchall()
        return {row["mission_id"]: Report.model_validate_json(row["report_json"]) for row in rows}

    def hydrate_runtime(self, runtime: object) -> object:
        runtime._missions = self._load_missions()
        runtime.state_graph._states = self._load_states()
        runtime.journal._entries = self._load_entries()
        runtime.registry._capabilities = self._load_capabilities()
        runtime.reports = self._load_reports()
        return runtime

    def pending_missions(self) -> list[PendingMission]:
        missions = self._load_missions()
        states = self._load_states()
        reports = self._load_reports()
        pending: list[PendingMission] = []
        for mission_id, mission in missions.items():
            state = states.get(mission.mission_id)
            if state is None:
                continue
            if state.status == "in_progress" and mission_id not in reports:
                pending.append(PendingMission(mission=mission, state=state))
        return pending
