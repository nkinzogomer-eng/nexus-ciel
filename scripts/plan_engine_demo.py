"""Deterministic Phase 2 demonstration; no network, tools, or model calls."""
from __future__ import annotations

import json
from uuid import uuid4

from nexus.planning import DeterministicCondition, PlanEngine, Step


def step(ordinal: int, title: str, *, depends_on=None, preconditions=None) -> Step:
    return Step(
        ordinal=ordinal,
        title=title,
        action_ref=f"demo.{title}",
        depends_on=list(depends_on or []),
        preconditions=list(preconditions or []),
        postconditions=[DeterministicCondition(key="ok", operator="equals", expected=True)],
        idempotency_key=f"demo-{title}-{ordinal}",
        budget_usd=1.0,
    )


def execute(engine: PlanEngine, plan_id, item: Step, facts: dict) -> None:
    engine.make_step_ready(plan_id, item.step_id, facts)
    engine.start_step(plan_id, item.step_id, estimated_cost_usd=1.0)
    engine.record_observation(plan_id, item.step_id, {"ok": True}, actual_cost_usd=1.0)
    engine.verify_step(plan_id, item.step_id)


def main() -> None:
    first = step(1, "prepare")
    second = step(
        2,
        "transform",
        depends_on=[first.step_id],
        preconditions=[DeterministicCondition(key="prepared", operator="equals", expected=True)],
    )
    third = step(3, "publish", depends_on=[second.step_id])
    engine = PlanEngine()
    plan = engine.create_plan(uuid4(), [first, second, third], budget_usd=3.0)
    engine.validate_plan(plan.plan_id)
    execute(engine, plan.plan_id, first, {})
    execute(engine, plan.plan_id, second, {"prepared": True})
    execute(engine, plan.plan_id, third, {})
    result = engine.get_plan(plan.plan_id)
    print(json.dumps({
        "plan_id": str(result.plan_id),
        "version": result.version,
        "status": result.status,
        "steps": [step.status for step in result.steps],
        "spent_cost_usd": result.total_spent_cost_usd,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
