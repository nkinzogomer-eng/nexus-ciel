import os
from uuid import UUID

import pytest

from nexus.persistence import PostgresSnapshotStore, PersistentRuntime
from nexus.providers import LocalProvider
from nexus.router import AdaptiveRouter
from nexus.schemas import Mission


@pytest.mark.asyncio
async def test_postgres_store_restores_runtime_after_restart():
    dsn = os.environ["NEXUS_DATABASE_URL"]
    store = PostgresSnapshotStore(dsn, snapshot_key="ci-phase2")
    runtime = PersistentRuntime(
        store,
        router=AdaptiveRouter([LocalProvider(confidence=0.90)]),
    )
    mission_id = await runtime.accept(Mission(objective="postgres restart proof"))

    restarted = PersistentRuntime(store)
    state = restarted.state_graph.get(UUID(mission_id))
    report = restarted.report(mission_id)

    assert state is not None
    assert state.status == "validated"
    assert state.resumable_after_crash is True
    assert report is not None
    assert report.verdict == "PASS"
    assert restarted.journal.verify_chain()
