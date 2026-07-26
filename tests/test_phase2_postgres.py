import os
from uuid import UUID

import pytest

from nexus.persistence import PostgresSnapshotStore, PersistentRuntime
from nexus.persistence.dsn import normalize_postgres_dsn_for_psycopg, normalize_postgres_dsn_for_sqlalchemy
from nexus.providers import LocalProvider
from nexus.router import AdaptiveRouter
from nexus.schemas import Mission


@pytest.mark.asyncio
async def test_postgres_store_restores_runtime_after_restart():
    store = PostgresSnapshotStore(os.environ["NEXUS_DATABASE_URL"], snapshot_key="ci-phase2")
    runtime = PersistentRuntime(store, router=AdaptiveRouter([LocalProvider(confidence=0.90)]))
    mission_id = await runtime.accept(Mission(objective="postgres restart proof"))
    restarted = PersistentRuntime(store)
    state = restarted.state_graph.get(UUID(mission_id))
    report = restarted.report(mission_id)
    assert state is not None and state.status == "validated" and state.resumable_after_crash is True
    assert report is not None and report.verdict == "PASS"
    assert restarted.journal.verify_chain()


def test_phase2_postgres_dsn_normalization_supports_sqlalchemy_and_psycopg():
    plain = "postgresql://nexus:nexus@localhost:5432/nexus_ciel"
    qualified = "postgresql+psycopg://nexus:nexus@localhost:5432/nexus_ciel"
    assert normalize_postgres_dsn_for_sqlalchemy(plain) == qualified
    assert normalize_postgres_dsn_for_sqlalchemy(qualified) == qualified
    assert normalize_postgres_dsn_for_psycopg(qualified) == plain
    assert normalize_postgres_dsn_for_psycopg(plain) == plain
