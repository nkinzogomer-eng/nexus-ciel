from __future__ import annotations

import os
import signal
import subprocess
import sys
from pathlib import Path

import pytest


pytestmark = pytest.mark.integration


WORKER = r'''
import asyncio
import os
import sys
from nexus.core import NexusRuntime
from nexus.persistence import build_runtime
from nexus.schemas import Mission

async def main():
    runtime = build_runtime()
    mission_id = await runtime.accept(Mission(objective="kill restart proof"))
    print(mission_id, flush=True)
    if os.environ.get("NEXUS_KILL_AFTER_COMMIT"):
        os.kill(os.getpid(), 9)
    state = runtime.state_graph.get(mission_id)
    assert state is not None

asyncio.run(main())
'''


@pytest.mark.skipif(
    not os.environ.get("NEXUS_DATABASE_URL"),
    reason="requires the PostgreSQL service configured by CI",
)
def test_api_runtime_survives_process_kill_and_restart(tmp_path: Path):
    """A process kill must not erase a committed mission.

    This is deliberately a subprocess test, not an in-process fixture. The
    first worker commits through the application runtime and is then killed;
    the second worker creates a fresh runtime against the same PostgreSQL
    database and must recover the mission and its journal. If the API still
    constructs the volatile NexusRuntime, this test fails loudly instead of
    letting a scaffold masquerade as persistence.
    """
    env = os.environ.copy()
    env["NEXUS_KILL_AFTER_COMMIT"] = "1"
    first = subprocess.Popen(
        [sys.executable, "-c", WORKER],
        cwd=Path(__file__).parents[1],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    stdout, stderr = first.communicate(timeout=30)
    assert first.returncode == -signal.SIGKILL, stderr
    mission_id = stdout.strip()
    assert mission_id, stderr

    env.pop("NEXUS_KILL_AFTER_COMMIT", None)
    check = subprocess.run(
        [
            sys.executable,
            "-c",
            """
import asyncio
import sys
from uuid import UUID
from nexus.persistence import build_runtime

async def main():
    runtime = build_runtime()
    mission_id = sys.argv[1]
    state = runtime.state_graph.get(UUID(mission_id))
    report = runtime.report(mission_id)
    assert state is not None, mission_id
    assert state.resumable_after_crash is True
    assert report is not None
    assert runtime.journal.verify_chain()

asyncio.run(main())
""",
            mission_id,
        ],
        cwd=Path(__file__).parents[1],
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert check.returncode == 0, check.stderr
