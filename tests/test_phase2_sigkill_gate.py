"""Black-box PostgreSQL crash gate for Phase 2.

This deliberately uses two Python processes. The first process persists an
in-progress mission and is killed with SIGKILL before it can finish. The
second process must recover the same snapshot and apply the documented
controlled-abandon policy.
"""

from __future__ import annotations

import asyncio
import json
import os
import signal
import subprocess
import sys
import textwrap
import uuid
from pathlib import Path

import pytest


pytestmark = pytest.mark.skipif(
    not os.environ.get("NEXUS_DATABASE_URL"),
    reason="NEXUS_DATABASE_URL is required for the PostgreSQL crash gate",
)


_WRITER = textwrap.dedent(
    """
    import asyncio
    import os
    import sys
    from nexus.persistence import PersistentRuntime, PostgresSnapshotStore
    from nexus.schemas import Mission

    class CrashRouter:
        decisions = []

        async def complete(self, request):
            raise RuntimeError("SIGKILL gate: stop before mission completion")

        def trace(self):
            return []

    async def main():
        key = sys.argv[1]
        mission = Mission(objective="real SIGKILL recovery gate")
        runtime = PersistentRuntime(
            PostgresSnapshotStore(os.environ["NEXUS_DATABASE_URL"], snapshot_key=key),
            router=CrashRouter(),
        )
        try:
            await runtime.accept(mission)
        except RuntimeError:
            # accept() has already persisted the in_progress state. Keep the
            # process alive so the parent can terminate it with SIGKILL.
            print(str(mission.mission_id), flush=True)
            await asyncio.sleep(60)

    asyncio.run(main())
    """
)


_RECOVERER = textwrap.dedent(
    """
    import json
    import os
    import sys
    from uuid import UUID
    from nexus.persistence import PersistentRuntime, PostgresSnapshotStore

    key, mission_id = sys.argv[1:]
    runtime = PersistentRuntime(
        PostgresSnapshotStore(os.environ["NEXUS_DATABASE_URL"], snapshot_key=key)
    )
    mission_uuid = UUID(mission_id)
    state = runtime.state_graph.get(mission_uuid)
    report = runtime.report(mission_id)
    entries = runtime.journal.entries(mission_uuid)
    print(json.dumps({
        "status": state.status if state else None,
        "resumable_after_crash": state.resumable_after_crash if state else None,
        "verdict": report.verdict if report else None,
        "recovery_policy": report.validation.get("recovery_policy") if report else None,
        "interrupted_event": entries[-1].type if entries else None,
        "journal_valid": runtime.journal.verify_chain(),
    }), flush=True)
    """
)


def _run_recovery(key: str, mission_id: str) -> dict[str, object]:
    completed = subprocess.run(
        [sys.executable, "-c", _RECOVERER, key, mission_id],
        check=True,
        capture_output=True,
        text=True,
        env=os.environ.copy(),
        cwd=Path(__file__).parents[1],
        timeout=30,
    )
    return json.loads(completed.stdout)


def test_postgres_sigkill_gate_recovers_and_abandons_mission() -> None:
    key = f"sigkill-gate-{uuid.uuid4()}"
    writer = subprocess.Popen(
        [sys.executable, "-c", _WRITER, key],
        cwd=Path(__file__).parents[1],
        env=os.environ.copy(),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )

    assert writer.stdout is not None
    try:
        mission_id = writer.stdout.readline().strip()
        assert mission_id, writer.stderr.read() if writer.stderr else "writer produced no mission"

        os.killpg(writer.pid, signal.SIGKILL)
        assert writer.wait(timeout=10) == -signal.SIGKILL

        recovered = _run_recovery(key, mission_id)
        assert recovered == {
            "status": "abandoned",
            "resumable_after_crash": True,
            "verdict": "FAIL",
            "recovery_policy": "controlled_abandon",
            "interrupted_event": "mission_interrupted",
            "journal_valid": True,
        }
    finally:
        if writer.poll() is None:
            os.killpg(writer.pid, signal.SIGKILL)
            writer.wait(timeout=10)
"