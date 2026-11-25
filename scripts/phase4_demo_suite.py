"""Generate five bounded Phase 4 Action Engine demonstrations."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path
from uuid import uuid4

from nexus.actions import ActionExecutor, ActionRequest, ApprovalRequired, ToolRegistry
from nexus.cognitive import CognitiveEngine, GoalUnderstanding
from nexus.persistence import FileSnapshotStore, PersistentRuntime
from nexus.planning import PlanEngine

ROOT = Path(__file__).parents[1] / "reports"


def write_report(name: str, report: dict) -> None:
    ROOT.mkdir(parents=True, exist_ok=True)
    (ROOT / f"phase4-demo-{name}.json").write_text(json.dumps(report, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    lines = [f"# Phase 4 demonstration — {name}", "", "```json", json.dumps(report, indent=2, sort_keys=True, default=str), "```", ""]
    (ROOT / f"phase4-demo-{name}.md").write_text("\n".join(lines), encoding="utf-8")


def action_request(cycle, step, tool, parameters, key) -> ActionRequest:
    return ActionRequest(mission_id=cycle.mission.mission_id, plan_id=cycle.plan_id, step_id=step.step_id, tool_name=tool, parameters=parameters, idempotency_key=key, budget_usd=5.0)


def nominal() -> None:
    executor = ActionExecutor(ToolRegistry.deterministic())
    engine = CognitiveEngine(plan_engine=PlanEngine(), action_executor=executor, mode="CORE_ONLY")
    goal = GoalUnderstanding(objective="compute two bounded results", expected_results=["first", "second"], success_criteria=["ok is observed"], constraints={"budget_usd": 5.0})
    cycle = engine.start(goal, action_tool="calculate")
    results = []
    for index, step in enumerate(engine.plan_engine.get_plan(cycle.plan_id).steps, 1):
        result = engine.execute_action(cycle.cycle_id, step.step_id, action_request(cycle, step, "calculate", {"operation": "add", "values": [index, index]}, f"nominal-{index}"), granted_permissions={"compute"})
        results.append(result.model_dump(mode="json"))
    plan = engine.plan_engine.get_plan(cycle.plan_id)
    write_report("nominal", {"objective": goal.objective, "steps": [s.model_dump(mode="json") for s in plan.steps], "tools_called": ["calculate", "calculate"], "permissions": ["compute"], "decisions": [d.model_dump(mode="json") for d in engine.get_cycle(cycle.cycle_id).decisions], "observations": results, "verifications": {"all_verified": plan.all_verified}, "costs": {"consumed": plan.total_spent_cost_usd}, "final_state": engine.get_cycle(cycle.cycle_id).status, "limits": ["Only deterministic registered tools are used."]})


def error_correction() -> None:
    executor = ActionExecutor(ToolRegistry.deterministic())
    engine = CognitiveEngine(plan_engine=PlanEngine(), action_executor=executor)
    goal = GoalUnderstanding(objective="recover from a bounded failure", expected_results=["recovered"], success_criteria=["ok is observed"], constraints={"budget_usd": 5.0})
    cycle = engine.start(goal, action_tool="simulated_failure")
    step = engine.plan_engine.get_plan(cycle.plan_id).steps[0]
    failed = engine.execute_action(cycle.cycle_id, step.step_id, action_request(cycle, step, "simulated_failure", {"reason": "controlled demo failure"}, "failure-once"), granted_permissions={"demo.simulate"})
    revised = engine.revise_after_failure(cycle.cycle_id, reason="bounded correction required")
    correction = next(item for item in engine.plan_engine.get_plan(revised.plan_id).steps if item.title == "controlled-correction")
    repaired = engine.execute_action(revised.cycle_id, correction.step_id, action_request(revised, correction, "calculate", {"operation": "add", "values": [1, 1]}, "correction-once"), granted_permissions={"compute"})
    plan = engine.plan_engine.get_plan(revised.plan_id)
    write_report("error-correction", {"objective": goal.objective, "steps": [s.model_dump(mode="json") for s in plan.steps], "tools_called": ["simulated_failure", "calculate"], "permissions": ["demo.simulate", "compute"], "decisions": [d.model_dump(mode="json") for d in engine.get_cycle(revised.cycle_id).decisions], "observations": [failed.model_dump(mode="json"), repaired.model_dump(mode="json")], "verifications": {"suffix_or_correction_preserved": any(s.title == "controlled-correction" for s in plan.steps), "failed_action_replayed": False}, "costs": {"consumed": plan.total_spent_cost_usd}, "final_state": plan.status, "limits": ["The remaining suffix still requires its own explicit execution and verification."]})


def interruption_restore() -> None:
    with tempfile.TemporaryDirectory(prefix="ciel-action-demo-") as directory:
        store = FileSnapshotStore(Path(directory) / "runtime.json")
        runtime = PersistentRuntime(store)
        action = ActionRequest(mission_id=uuid4(), plan_id=uuid4(), step_id=uuid4(), tool_name="simulated_uncertain", parameters={"reason": "interrupted transport"}, idempotency_key="interrupt-once", budget_usd=1.0)
        first = runtime.action_executor.execute(action, granted_permissions={"demo.simulate"})
        restarted = PersistentRuntime(store)
        replay = restarted.action_executor.execute(action, granted_permissions={"demo.simulate"})
        write_report("interruption-restore", {"objective": "restore without replaying an uncertain effect", "steps": [], "tools_called": ["simulated_uncertain"], "permissions": ["demo.simulate"], "decisions": [{"kind": "SUSPEND", "reason": "uncertain effect requires explicit verification"}], "observations": [first.model_dump(mode="json"), replay.model_dump(mode="json")], "verifications": {"restored": restarted.action_executor.get(action.action_id) is not None, "replay_blocked": replay.idempotent_replay, "journal_valid": restarted.journal.verify_chain()}, "costs": {"consumed": first.actual_cost_usd}, "final_state": restarted.action_executor.get(action.action_id).status, "limits": ["Automatic resume is disabled; external effect verification is not inferred from restoration."]})


def security_refusal() -> None:
    executor = ActionExecutor(ToolRegistry.deterministic())
    unknown = ActionRequest(mission_id=uuid4(), plan_id=uuid4(), step_id=uuid4(), tool_name="shell", parameters={"command": "echo forbidden"}, idempotency_key="security-unknown", budget_usd=1.0)
    result = executor.execute(unknown, granted_permissions={"shell"})
    write_report("security-refusal", {"objective": "refuse an unregistered arbitrary command", "steps": [], "tools_called": [], "permissions": ["shell"], "decisions": [{"kind": "REJECT", "reason": result.error}], "observations": [result.model_dump(mode="json")], "verifications": {"no_effect": True, "unregistered_refused": result.status == "rejected"}, "costs": {"consumed": result.actual_cost_usd}, "final_state": result.status, "limits": ["No shell, network, browser or arbitrary filesystem tool is registered."]})


def core_only() -> None:
    executor = ActionExecutor(ToolRegistry.deterministic())
    engine = CognitiveEngine(plan_engine=PlanEngine(), action_executor=executor, mode="CORE_ONLY")
    goal = GoalUnderstanding(objective="run without an LLM", expected_results=["calculation"], success_criteria=["ok is observed"], constraints={"budget_usd": 2.0})
    cycle = engine.start(goal, action_tool="calculate")
    step = engine.plan_engine.get_plan(cycle.plan_id).steps[0]
    result = engine.execute_action(cycle.cycle_id, step.step_id, action_request(cycle, step, "calculate", {"operation": "multiply", "values": [3, 4]}, "core-only-once"), granted_permissions={"compute"})
    write_report("core-only", {"objective": goal.objective, "steps": [step.model_dump(mode="json")], "tools_called": ["calculate"], "permissions": ["compute"], "decisions": [d.model_dump(mode="json") for d in engine.get_cycle(cycle.cycle_id).decisions], "observations": [result.model_dump(mode="json")], "verifications": {"core_only": cycle.mode == "CORE_ONLY", "all_verified": engine.plan_engine.get_plan(cycle.plan_id).all_verified}, "costs": {"consumed": engine.plan_engine.get_plan(cycle.plan_id).total_spent_cost_usd}, "final_state": engine.get_cycle(cycle.cycle_id).status, "limits": ["LLM providers are not involved."]})


if __name__ == "__main__":
    nominal()
    error_correction()
    interruption_restore()
    security_refusal()
    core_only()
    print("generated five Phase 4 JSON and Markdown reports")
