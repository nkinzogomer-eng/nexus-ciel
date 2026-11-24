"""Phase 3.1 interruption/recovery demonstration; restart never replays running work."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path
from uuid import uuid4

from nexus.persistence import FileSnapshotStore, PersistentRuntime
from nexus.planning import DeterministicCondition, InvalidPlanTransition, Step


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="ciel-phase31-") as directory:
        store = FileSnapshotStore(Path(directory) / "snapshot.json")
        runtime = PersistentRuntime(store)
        step = Step(ordinal=1, title="interruptible", action_ref="demo.action", idempotency_key="demo-interrupt", budget_usd=1.0, postconditions=[DeterministicCondition(key="ok", expected=True)])
        plan = runtime.plan_engine.validate_plan(runtime.plan_engine.create_plan(uuid4(), [step], budget_usd=1.0).plan_id)
        runtime.plan_engine.make_step_ready(plan.plan_id, step.step_id, {})
        runtime.plan_engine.start_step(plan.plan_id, step.step_id, estimated_cost_usd=0.2)
        restored = PersistentRuntime(store)
        restored_plan = restored.plan_engine.get_plan(plan.plan_id)
        replay_blocked = False
        try:
            restored.plan_engine.start_step(plan.plan_id, step.step_id)
        except InvalidPlanTransition:
            replay_blocked = True
        report = {
            "mission": str(restored_plan.mission_id),
            "objective": "restore durable state without replaying an uncertain running action",
            "strategy": "controlled recovery / no automatic resume",
            "steps": [item.model_dump(mode="json") for item in restored_plan.steps],
            "decisions": [{"kind": "SUSPEND", "reason": "running state requires explicit human or policy decision"}],
            "observations": [],
            "costs": {"budget": restored_plan.budget_usd, "consumed": restored_plan.total_spent_cost_usd, "reserved": restored_plan.total_reserved_cost_usd},
            "revisions": 0,
            "final_state": {"plan": restored_plan.status, "step": restored_plan.steps[0].status},
            "verifications": {"snapshot_restored": True, "replay_blocked": replay_blocked, "journal_chain_valid": restored.journal.verify_chain()},
            "limits": ["Recovery policy is controlled_abandon for in-progress missions; this isolated plan remains running and cannot be started twice.", "Distributed PostgreSQL multi-writer CAS remains a documented blocker."],
        }
        output = Path(__file__).parents[1] / "reports" / "phase31-demo-interruption-restore.json"
        output.write_text(json.dumps(report, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
        print(json.dumps(report, indent=2, sort_keys=True, default=str))


if __name__ == "__main__":
    main()
