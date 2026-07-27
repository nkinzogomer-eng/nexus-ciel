from __future__ import annotations

import json
from typing import Any

from .dsn import normalize_postgres_dsn_for_psycopg


class PostgresSnapshotStore:
    def __init__(self, dsn: str, snapshot_key: str = "default") -> None:
        self.dsn, self.snapshot_key = dsn, snapshot_key

    def _connect(self):
        try:
            import psycopg
        except ModuleNotFoundError as exc:
            raise RuntimeError("psycopg is required for PostgreSQL persistence") from exc
        return psycopg.connect(normalize_postgres_dsn_for_psycopg(self.dsn))

    def load(self) -> dict[str, Any] | None:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute("SELECT payload FROM runtime_snapshots WHERE snapshot_key = %s", (self.snapshot_key,))
            row = cur.fetchone()
        if row is None:
            return None
        return json.loads(row[0]) if isinstance(row[0], str) else row[0]

    def save(self, snapshot: dict[str, Any]) -> None:
        payload = json.dumps(snapshot)
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """INSERT INTO runtime_snapshots (snapshot_key, payload) VALUES (%s, %s::jsonb)
                ON CONFLICT (snapshot_key) DO UPDATE SET payload = EXCLUDED.payload,
                updated_at = timezone('utc', now())""",
                (self.snapshot_key, payload),
            )
            conn.commit()
