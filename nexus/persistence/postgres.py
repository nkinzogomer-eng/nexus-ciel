from __future__ import annotations

import json
from typing import Any


class PostgresSnapshotStore:
    """Small synchronous repository for the Phase 2 canonical tables."""

    def __init__(self, dsn: str) -> None:
        self.dsn = dsn

    def _connect(self):
        try:
            import psycopg
        except ModuleNotFoundError as exc:
            raise RuntimeError("psycopg is required for PostgreSQL persistence") from exc
        return psycopg.connect(self.dsn)

    def load(self) -> dict[str, Any]:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute("SELECT mission_id, objective, status, iterations, resumable_after_crash FROM mission_states")
            states = cur.fetchall()
            cur.execute("SELECT mission_id, verdict, objective, summary, iterations, cost_usd, duration_s, actions, validation, learned, guard_events, generated_at FROM mission_reports")
            reports = cur.fetchall()
            cur.execute("SELECT seq, mission_id, event_type, actor, payload, signature, precedent_hash, timestamp FROM mission_journal ORDER BY seq")
            journal = cur.fetchall()
            cur.execute("SELECT id, name, description, type, status, version, stats FROM capabilities")
            capabilities = cur.fetchall()
        return {"states": states, "reports": reports, "journal": journal, "capabilities": capabilities}

    def save_runtime(self, runtime: Any) -> None:
        with self._connect() as conn, conn.cursor() as cur:
            for state in runtime.state_graph._states.values():
                cur.execute(
                    """INSERT INTO mission_states (mission_id, objective, status, iterations, resumable_after_crash, updated_at)
                    VALUES (%s,%s,%s,%s,%s,CURRENT_TIMESTAMP)
                    ON CONFLICT (mission_id) DO UPDATE SET objective=EXCLUDED.objective,status=EXCLUDED.status,
                    iterations=EXCLUDED.iterations,resumable_after_crash=EXCLUDED.resumable_after_crash,updated_at=CURRENT_TIMESTAMP""",
                    (str(state.mission_id), state.objective, state.status, state.iterations, state.resumable_after_crash),
                )
            for mission_id, report in runtime.reports.items():
                data = report.model_dump(mode="json")
                cur.execute(
                    """INSERT INTO mission_reports (mission_id, verdict, objective, summary, iterations, cost_usd, duration_s, actions, validation, learned, guard_events, generated_at)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT (mission_id) DO UPDATE SET verdict=EXCLUDED.verdict,summary=EXCLUDED.summary,iterations=EXCLUDED.iterations,cost_usd=EXCLUDED.cost_usd,duration_s=EXCLUDED.duration_s,actions=EXCLUDED.actions,validation=EXCLUDED.validation,learned=EXCLUDED.learned,guard_events=EXCLUDED.guard_events,generated_at=EXCLUDED.generated_at""",
                    (mission_id, data["verdict"], data["objective"], data["summary"], data["iterations"], data["cost_usd"], data["duration_s"], json.dumps(data["actions"]), json.dumps(data["validation"]), json.dumps(data["learned"]), json.dumps(data["guard_events"]), data["generated_at"]),
                )
            for entry in runtime.journal.entries():
                cur.execute(
                    """INSERT INTO mission_journal (seq, mission_id, event_type, actor, payload, signature, precedent_hash, timestamp)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (seq) DO NOTHING""",
                    (entry.seq, str(entry.mission_id), entry.type, entry.actor, json.dumps(entry.payload), entry.signature, entry.precedent_hash, entry.timestamp),
                )
            for capability in runtime.registry.list():
                data = capability.model_dump(mode="json")
                cur.execute(
                    """INSERT INTO capabilities (id,name,description,type,status,version,stats) VALUES (%s,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT (id) DO UPDATE SET name=EXCLUDED.name,description=EXCLUDED.description,status=EXCLUDED.status,version=EXCLUDED.version,stats=EXCLUDED.stats""",
                    (str(capability.id), data["name"], data["description"], data["type"], data["status"], data["version"], json.dumps(data["stats"])),
                )
            conn.commit()
