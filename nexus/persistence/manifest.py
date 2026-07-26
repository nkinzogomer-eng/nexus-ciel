from __future__ import annotations

from dataclasses import dataclass
import os
from urllib.parse import urlparse

DATABASE_URL_ENV_VAR = "NEXUS_DATABASE_URL"
DEFAULT_DATABASE_URL = "postgresql+psycopg://nexus:nexus@postgres:5432/nexus_ciel"


@dataclass(frozen=True)
class ColumnSpec:
    name: str
    sql_type: str
    nullable: bool = False
    notes: str = ""


@dataclass(frozen=True)
class TableSpec:
    name: str
    columns: tuple[ColumnSpec, ...]
    purpose: str

    def column_names(self) -> tuple[str, ...]:
        return tuple(column.name for column in self.columns)


@dataclass(frozen=True)
class PersistenceManifest:
    tables: tuple[TableSpec, ...]

    def table_names(self) -> tuple[str, ...]:
        return tuple(table.name for table in self.tables)

    def get(self, table_name: str) -> TableSpec:
        for table in self.tables:
            if table.name == table_name:
                return table
        raise KeyError(table_name)


def load_database_url(raw: str | None = None) -> str:
    value = raw or os.environ.get(DATABASE_URL_ENV_VAR) or DEFAULT_DATABASE_URL
    parsed = urlparse(value)
    if not parsed.scheme or not parsed.path:
        raise ValueError(f"invalid database url: {value!r}")
    if parsed.scheme != "sqlite" and not parsed.scheme.startswith("postgresql"):
        raise ValueError(
            "database url must target PostgreSQL in production or sqlite for local migration tests"
        )
    return value


def _columns(*items: ColumnSpec) -> tuple[ColumnSpec, ...]:
    return tuple(items)


def baseline_manifest() -> PersistenceManifest:
    return PersistenceManifest(
        tables=(
            TableSpec(
                name="mission_states",
                purpose="Durable State Graph snapshot per mission.",
                columns=_columns(
                    ColumnSpec("mission_id", "uuid"),
                    ColumnSpec("objective", "text"),
                    ColumnSpec("status", "text"),
                    ColumnSpec("iterations", "integer"),
                    ColumnSpec(
                        "resumable_after_crash",
                        "boolean",
                        notes="Must default to false until persistence is wired end to end.",
                    ),
                    ColumnSpec("updated_at", "timestamptz"),
                ),
            ),
            TableSpec(
                name="mission_reports",
                purpose="Final reports returned to callers.",
                columns=_columns(
                    ColumnSpec("mission_id", "uuid"),
                    ColumnSpec("verdict", "text"),
                    ColumnSpec("objective", "text"),
                    ColumnSpec("summary", "text"),
                    ColumnSpec("iterations", "integer"),
                    ColumnSpec("cost_usd", "double precision"),
                    ColumnSpec("duration_s", "double precision"),
                    ColumnSpec("actions", "jsonb"),
                    ColumnSpec("validation", "jsonb"),
                    ColumnSpec("learned", "jsonb"),
                    ColumnSpec("guard_events", "jsonb"),
                    ColumnSpec("generated_at", "timestamptz"),
                ),
            ),
            TableSpec(
                name="mission_journal",
                purpose="Append-only audit chain with signatures.",
                columns=_columns(
                    ColumnSpec("seq", "bigint"),
                    ColumnSpec("mission_id", "uuid"),
                    ColumnSpec("event_type", "text"),
                    ColumnSpec("actor", "text"),
                    ColumnSpec("payload", "jsonb"),
                    ColumnSpec("signature", "text"),
                    ColumnSpec("precedent_hash", "text"),
                    ColumnSpec("timestamp", "timestamptz"),
                ),
            ),
            TableSpec(
                name="capabilities",
                purpose="Capability Registry source of truth.",
                columns=_columns(
                    ColumnSpec("id", "uuid"),
                    ColumnSpec("name", "text"),
                    ColumnSpec("description", "text"),
                    ColumnSpec("type", "text"),
                    ColumnSpec("status", "text"),
                    ColumnSpec("version", "integer"),
                    ColumnSpec("stats", "jsonb"),
                ),
            ),
            TableSpec(
                name="routing_telemetry",
                purpose="Per-attempt routing evidence and cost accounting.",
                columns=_columns(
                    ColumnSpec("id", "bigint"),
                    ColumnSpec("mission_id", "uuid", nullable=True),
                    ColumnSpec("stage", "text"),
                    ColumnSpec("provider", "text"),
                    ColumnSpec("confidence", "double precision"),
                    ColumnSpec("escalated", "boolean"),
                    ColumnSpec("reason", "text"),
                    ColumnSpec("cost_usd", "double precision"),
                    ColumnSpec("cost_avoided_usd", "double precision"),
                    ColumnSpec("latency_ms", "double precision"),
                    ColumnSpec("error", "text", nullable=True),
                    ColumnSpec("created_at", "timestamptz"),
                ),
            ),
        )
    )
