"""Reproducible Phase 5 demonstrations using the real cognitive/action components."""
from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import tempfile
from pathlib import Path
from uuid import uuid4

from nexus.actions import ActionExecutor, ActionRequest, ToolRegistry
from nexus.cognitive import CognitiveEngine, NaturalGoalInterpreter
from nexus.persistence import FileSnapshotStore, PersistentRuntime
from nexus.planning import PlanEngine

ROOT = Path(__file__).parents[1]
OUT = ROOT / "reports" / "phase5-demos"


def run_nominal() -> dict:
    analysis = NaturalGoalInterpreter().interpret(
        "Calcule la somme 4 et 6, avec budget 1, vérifie que le résultat vaut 10"
    )
    executor = ActionExecutor(ToolRegistry.deterministic())
    engine = CognitiveEngine(plan_engine=PlanEngine(), action_executor=executor, mode="CORE_ONLY")
    cycle = engine.start(analysis.to_goal(), budget_usd=1.0, action_tool="calculate")
    step = engine.plan_engine.get_plan(cycle.plan_id).steps[0]
    request = ActionRequest(
        mission_id=cycle.mission.mission_id, plan_id=cycle.plan_id, step_id=step.step_id,
        tool_name="calculate", parameters={"operation": "add", "values": [4, 6]},
        idempotency_key="phase5-demo-nominal", budget_usd=1.0,
    )
    result = engine.execute_action(cycle.cycle_id, step.step_id, request, granted_permissions={"compute"})
    return {"mission": "nominal", "input": analysis.model_dump(mode="json"), "strategy": cycle.selection.model_dump(mode="json"), "action": result.model_dump(mode="json"), "final_status": engine.get_cycle(cycle.cycle_id).status}


def run_failure_and_adaptation() -> dict:
    analysis = NaturalGoalInterpreter().interpret("Calcule une valeur de correction avec budget 1")
    registry = ToolRegistry.deterministic()
    engine = CognitiveEngine(plan_engine=PlanEngine(), action_executor=ActionExecutor(registry), mode="CORE_ONLY")
    cycle = engine.start(analysis.to_goal(), budget_usd=1.0, action_tool="simulated_failure")
    failed_step = engine.plan_engine.get_plan(cycle.plan_id).steps[0]
    failed_request = ActionRequest(
        mission_id=cycle.mission.mission_id, plan_id=cycle.plan_id, step_id=failed_step.step_id,
        tool_name="simulated_failure", parameters={"reason": "controlled demo failure"},
        idempotency_key="phase5-demo-failure", budget_usd=1.0,
    )
    failed = engine.execute_action(cycle.cycle_id, failed_step.step_id, failed_request, granted_permissions={"demo.simulate"})
    revised = engine.revise_after_failure(cycle.cycle_id, reason="failure was observed; use a deterministic correction")
    correction = next(item for item in engine.plan_engine.get_plan(cycle.plan_id).steps if item.action_ref == "tool:calculate")
    correction_request = ActionRequest(
        mission_id=cycle.mission.mission_id, plan_id=cycle.plan_id, step_id=correction.step_id,
        tool_name="calculate", parameters={"operation": "add", "values": [2, 3]},
        idempotency_key="phase5-demo-correction", budget_usd=1.0,
    )
    corrected = engine.execute_action(cycle.cycle_id, correction.step_id, correction_request, granted_permissions={"compute"})
    return {"mission": "failure_and_adaptation", "input": analysis.model_dump(mode="json"), "failed_action": failed.model_dump(mode="json"), "revision": revised.model_dump(mode="json"), "corrected_action": corrected.model_dump(mode="json"), "final_status": engine.get_cycle(cycle.cycle_id).status}


def run_real_interruption() -> dict:
    with tempfile.TemporaryDirectory(prefix="ciel-phase5-interruption-") as directory:
        root = Path(directory)
        snapshot = root / "runtime.json"
        marker = root / "handler.log"
        request_file = root / "request.json"
        child = r'''
import os, signal, sys
from nexus.actions import ActionRequest
from nexus.persistence import FileSnapshotStore, PersistentRuntime
store = FileSnapshotStore(sys.argv[1])
request = ActionRequest(mission_id=__import__("uuid").uuid4(), plan_id=__import__("uuid").uuid4(), step_id=__import__("uuid").uuid4(), tool_name="calculate", parameters={"operation":"add","values":[7,8]}, idempotency_key="phase5-demo-interruption", budget_usd=1.0)
open(sys.argv[3], "w").write(request.model_dump_json())
def crash(params):
    with open(sys.argv[2], "a") as stream:
        stream.write("handler\n")
        stream.flush()
    os.kill(os.getpid(), signal.SIGKILL)
runtime = PersistentRuntime(store)
runtime.action_executor.registry._handlers["calculate"] = crash
runtime.action_executor.execute(request, granted_permissions={"compute"})
'''
        process = subprocess.Popen([sys.executable, "-c", child, str(snapshot), str(marker), str(request_file)], cwd=ROOT, env={**os.environ, "PYTHONPATH": str(ROOT)})
        return_code = process.wait(timeout=10)
        request = ActionRequest.model_validate_json(request_file.read_text())
        restored = PersistentRuntime(FileSnapshotStore(snapshot)).action_executor.get(request.action_id)
        replay = PersistentRuntime(FileSnapshotStore(snapshot)).action_executor.execute(request, granted_permissions={"compute"})
        return {"mission": "real_interruption", "process_return_code": return_code, "expected_signal": -signal.SIGKILL, "handler_calls": marker.read_text().splitlines(), "restored_status": restored.status if restored else None, "replay_status": replay.status, "replay_was_idempotent": replay.idempotent_replay, "automatic_replay": False}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    results = [run_nominal(), run_failure_and_adaptation(), run_real_interruption()]
    for result in results:
        path = OUT / f"{result['mission']}.json"
        path.write_text(json.dumps(result, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    lines = ["# Démonstrations Phase 5", "", "Les trois parcours utilisent les composants CIEL réels. Le troisième tue réellement un processus enfant par SIGKILL ; la politique de recovery constate l’incertitude et interdit le rejeu automatique.", ""]
    for result in results:
        lines.extend([f"## {result['mission']}", "", "```json", json.dumps(result, indent=2, sort_keys=True, default=str), "```", ""])
    (OUT / "README.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
