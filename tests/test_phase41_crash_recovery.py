from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
from pathlib import Path
from uuid import UUID, uuid4

from nexus.actions import ActionRequest
from nexus.persistence import FileSnapshotStore, PersistentRuntime


def test_real_process_crash_persists_running_and_restores_without_replay(tmp_path):
    snapshot = tmp_path / "runtime.json"
    marker = tmp_path / "handler-calls.log"
    action_data = tmp_path / "request.json"
    code = r'''
import os, signal, sys
from nexus.actions import ActionRequest
from nexus.persistence import FileSnapshotStore, PersistentRuntime
store = FileSnapshotStore(sys.argv[1])
marker = sys.argv[2]
runtime = PersistentRuntime(store)
request = ActionRequest(mission_id=__import__('uuid').uuid4(), plan_id=__import__('uuid').uuid4(), step_id=__import__('uuid').uuid4(), tool_name='calculate', parameters={'operation':'add','values':[4,5]}, idempotency_key='crash-real-key', budget_usd=1.0)
open(sys.argv[3], 'w').write(request.model_dump_json())
def crash(params):
    with open(marker, 'a') as stream:
        stream.write('handler\n')
        stream.flush()
    os.kill(os.getpid(), signal.SIGKILL)
runtime.action_executor.registry._handlers['calculate'] = crash
runtime.action_executor.execute(request, granted_permissions={'compute'})
'''
    child = subprocess.Popen(
        [sys.executable, "-c", code, str(snapshot), str(marker), str(action_data)],
        cwd=Path(__file__).parents[1],
        env={**os.environ, "PYTHONPATH": str(Path(__file__).parents[1])},
    )
    assert child.wait(timeout=10) == -signal.SIGKILL
    assert marker.read_text() == "handler\n"

    request = ActionRequest.model_validate_json(action_data.read_text())
    restarted = PersistentRuntime(FileSnapshotStore(snapshot))
    restored = restarted.action_executor.get(request.action_id)
    assert restored is not None
    assert restored.status == "interrupted_uncertain"
    assert any(entry.type == "action_recovery_blocked" for entry in restarted.journal.entries(request.mission_id))

    replay = restarted.action_executor.execute(request, granted_permissions={"compute"})
    assert replay.status == "interrupted_uncertain"
    assert replay.idempotent_replay is True
    assert marker.read_text() == "handler\n"
    assert restarted.journal.verify_chain()
    assert json.loads(snapshot.read_text())["actions"][0]["status"] == "interrupted_uncertain"
