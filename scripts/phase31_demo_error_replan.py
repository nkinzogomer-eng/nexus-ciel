"""Phase 3.1 controlled replanning demonstration."""
from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

from nexus.cognitive import ControlledReplanner
from nexus.planning import DeterministicCondition, PlanEngine, Step


def make_steps() -> list[Step]:
    raw = [
        Step(ordinal=i, title=f"step-{i}", action_ref=f"demo.action.{i}", idempotency_key=f"demo-{i}", budget_usd=1.0, postconditions=[DeterministicCondition(key="ok", expected=True)])
        for i in range(1, 4)
    ]
    return [item.model_copy(update={"depends_on": [raw[i - 2].step_id] if i > 1 else []}) for i, item in enumerate(raw, 1)]


def main() -> None:
    engine = PlanEngine()
    initial = engine.validate_plan(engine.create_plan(uuid4(), make_steps(), budget_usd=6.0).plan_id)
    failed_step = initial.steps[0]
    engine.make_step_ready(initial.plan_id, failed_step.step_id, {})
    engine.fail_step(initial.plan_id, failed_step.step_id, "demonstration failure")
    revised = ControlledReplanner().revise_after_failure(engine, initial.plan_id, reason="replace failed first step")
    correction = next(step for step in revised.steps if step.title == "controlled-correction")
    engine.make_step_ready(revised.plan_id, correction.step_id, {})
    engine.start_step(revised.plan_id, correction.step_id, estimated_cost_usd=0.1)
    engine.record_observation(revised.plan_id, correction.step_id, {"ok": True}, actual_cost_usd=0.1)
    engine.verify_step(revised.plan_id, correction.step_id)
    report = {
        "mission": str(revised.mission_id),
        "objective": "recover after a failed first step without deleting the suffix",
        "strategy": "controlled correction with preserved suffix",
        "steps": [step.model_dump(mode="json") for step in revised.steps],
        "decisions": [{"kind": "REVISE", "reason": "demonstration failure"}],
        "observations": [{"step": str(correction.step_id), "outcome": "success", "verified": True}],
        "costs": {"budget": revised.budget_usd, "consumed": revised.total_spent_cost_usd, "reserved": revised.total_reserved_cost_usd},
        "revisions": len(engine.history(revised.plan_id)) - 1,
        "final_state": {"plan": engine.get_plan(revised.plan_id).status, "correction": engine.get_plan(revised.plan_id).steps[-1].status},
        "verifications": {"suffix_preserved": any(step.title == "step-3" for step in revised.steps), "failed_step_not_replayed": all(step.step_id != failed_step.step_id for step in revised.steps)},
        "limits": ["The correction itself still requires explicit observation and verification.", "No automatic replay is performed."],
    }
    output = Path(__file__).parents[1] / "reports" / "phase31-demo-error-replan.json"
    output.write_text(json.dumps(report, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True, default=str))


if __name__ == "__main__":
    main()
