"""Phase 3.1 nominal mission demonstration; deterministic and CORE_ONLY."""
from __future__ import annotations

import json
from pathlib import Path
from uuid import UUID

from nexus.cognitive import CognitiveEngine, GoalUnderstanding
from nexus.planning import PlanEngine


def main() -> None:
    engine = CognitiveEngine(plan_engine=PlanEngine(), mode="CORE_ONLY")
    goal = GoalUnderstanding(
        objective="prepare a bounded mission",
        expected_results=["verified result"],
        success_criteria=["ok is observed"],
        known_facts={"scope": "bounded"},
        constraints={"budget_usd": 5.0},
    )
    cycle = engine.start(goal)
    plan = engine.plan_engine.get_plan(cycle.plan_id)
    observations = []
    for step in plan.steps:
        engine.plan_engine.make_step_ready(plan.plan_id, step.step_id, {"ok": True})
        engine.plan_engine.start_step(plan.plan_id, step.step_id, estimated_cost_usd=0.1)
        assessment = engine.observe(cycle.cycle_id, step.step_id, {"ok": True}, actual_cost_usd=0.1)
        observations.append(assessment.model_dump(mode="json"))
        plan = engine.plan_engine.get_plan(plan.plan_id)
    final = engine.get_cycle(cycle.cycle_id)
    report = {
        "mission": str(final.mission.mission_id),
        "objective": goal.model_dump(mode="json"),
        "strategy": final.selection.model_dump(mode="json"),
        "steps": [step.model_dump(mode="json") for step in plan.steps],
        "decisions": [item.model_dump(mode="json") for item in final.decisions],
        "observations": observations,
        "costs": {"estimated": sum(step.estimated_cost_usd for step in plan.steps), "consumed": plan.total_spent_cost_usd, "reserved": plan.total_reserved_cost_usd},
        "revisions": 0,
        "final_state": {"cycle": final.status, "plan": plan.status},
        "verifications": {"all_steps_verified": plan.all_verified, "core_only": final.mode == "CORE_ONLY"},
        "limits": ["No external action executor is involved.", "PostgreSQL multi-writer CAS remains outside this demo."],
    }
    output = Path(__file__).parents[1] / "reports" / "phase31-demo-nominal.json"
    output.write_text(json.dumps(report, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True, default=str))


if __name__ == "__main__":
    main()
