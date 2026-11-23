"""Phase 3 deterministic cognitive-cycle demonstration; no external effects."""
from __future__ import annotations

import json
from nexus.cognitive import GoalUnderstanding
from nexus.persistence import FileSnapshotStore, PersistentRuntime


def main() -> None:
    store = FileSnapshotStore("/tmp/ciel-cognitive-demo.json")
    runtime = PersistentRuntime(store)
    goal = GoalUnderstanding(
        objective="prepare a verified report",
        expected_results=["collect facts", "verify report"],
        success_criteria=["all observations satisfy postconditions"],
        constraints={"budget_usd": 5.0},
    )
    cycle = runtime.cognitive_engine.start(goal, llm_recommendation="advisory only")
    first = runtime.plan_engine.get_plan(cycle.plan_id).steps[0]
    runtime.plan_engine.make_step_ready(cycle.plan_id, first.step_id, {})
    runtime.plan_engine.start_step(cycle.plan_id, first.step_id, estimated_cost_usd=0.1)
    runtime.cognitive_engine.observe(cycle.cycle_id, first.step_id, {"ok": False}, actual_cost_usd=0.1)
    cycle = runtime.cognitive_engine.revise_after_failure(cycle.cycle_id, reason="unexpected observation")
    correction = runtime.plan_engine.get_plan(cycle.plan_id).steps[-1]
    runtime.plan_engine.make_step_ready(cycle.plan_id, correction.step_id, {})
    runtime.plan_engine.start_step(cycle.plan_id, correction.step_id, estimated_cost_usd=0.1)
    runtime.cognitive_engine.observe(cycle.cycle_id, correction.step_id, {"ok": True}, actual_cost_usd=0.1)
    restarted = PersistentRuntime(store)
    restored = restarted.cognitive_engine.get_cycle(cycle.cycle_id)
    print(json.dumps({
        "strategy": restored.selection.candidate_name,
        "decisions": [decision.kind for decision in restored.decisions],
        "observations": [observation.outcome for observation in restored.observations],
        "plan_version": restarted.plan_engine.get_plan(restored.plan_id).version,
        "journal_valid": restarted.journal.verify_chain(),
        "deterministic": True,
        "external_tools_called": False,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
