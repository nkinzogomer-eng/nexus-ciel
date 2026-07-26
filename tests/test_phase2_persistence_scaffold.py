from __future__ import annotations

from pathlib import Path

from nexus.persistence import (
    DATABASE_URL_ENV_VAR,
    DEFAULT_DATABASE_URL,
    baseline_manifest,
    load_database_url,
)


def test_phase2_manifest_covers_phase0_sources_and_phase1_telemetry():
    manifest = baseline_manifest()
    assert manifest.table_names() == (
        "mission_states",
        "mission_reports",
        "mission_journal",
        "capabilities",
        "routing_telemetry",
    )
    mission_states = manifest.get("mission_states")
    assert "resumable_after_crash" in mission_states.column_names()
    telemetry = manifest.get("routing_telemetry")
    assert {"cost_usd", "cost_avoided_usd", "error"}.issubset(telemetry.column_names())


def test_phase2_database_url_defaults_to_compose_postgres_and_accepts_sqlite():
    assert load_database_url() == DEFAULT_DATABASE_URL
    sqlite_url = "sqlite:////tmp/nexus-ciel-phase2.db"
    assert load_database_url(sqlite_url) == sqlite_url
    assert DATABASE_URL_ENV_VAR == "NEXUS_DATABASE_URL"


def test_phase2_alembic_baseline_mentions_every_required_table():
    migration = Path("migrations/versions/20260727_0300_phase2_persistence_baseline.py").read_text(encoding="utf-8")
    for table in (
        "mission_states",
        "mission_reports",
        "mission_journal",
        "capabilities",
        "routing_telemetry",
    ):
        assert f'"{table}"' in migration
    assert "resumable_after_crash" in migration
    assert "cost_avoided_usd" in migration
    assert "server_default=sa.false()" in migration


def test_phase2_compose_bootstraps_postgres_then_runs_alembic_before_api():
    compose = Path("docker-compose.yml").read_text(encoding="utf-8")
    dockerfile = Path("Dockerfile").read_text(encoding="utf-8")
    assert "postgres:16-alpine" in compose
    assert "postgres_data:/var/lib/postgresql/data" in compose
    assert "alembic upgrade head" in compose
    assert "uvicorn nexus.api.app:app" in compose
    assert "pip install -e '.[postgres]'" in dockerfile
