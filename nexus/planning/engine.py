from __future__ import annotations

from datetime import datetime, timezone
from threading import RLock
from typing import TYPE_CHECKING, Any, Callable, Iterable
from uuid import UUID

if TYPE_CHECKING:
    from nexus.core.mission_journal import MissionJournal

from .models import DeterministicCondition, Plan, PlanStatus, Step, StepStatus


class PlanEngineError(ValueError):
    """Base error for deterministic plan operations."""


class PlanValidationError(PlanEngineError):
    """Raised when a plan is incomplete, inconsistent, cyclic, or over limits."""


class InvalidPlanTransition(PlanEngineError):
    """Raised when a plan or step transition is not explicitly allowed."""


class UnknownPlan(PlanEngineError):
    """Raised when a plan identifier is not known."""


class UnknownStep(PlanEngineError):
    """Raised when a step identifier is not part of a plan."""


class PreconditionNotMet(PlanEngineError):
    """Raised when a step cannot become ready."""


class PostconditionNotMet(PlanEngineError):
    """Raised when an observation cannot verify a step."""


class StepBudgetExceeded(PlanEngineError):
    """Raised before or after a step exceeds its declared budget."""


class ConcurrentPlanModification(PlanEngineError):
    """Raised when an optimistic version check detects a stale writer."""


class PlanEngine:
    """Thread-safe deterministic plan state machine.

    This engine records planning progress only. It never invokes tools, models,
    files, network services, or arbitrary user code. Persistence is provided by
    the ``snapshot``/``from_snapshot`` boundary used by PersistentRuntime.
    """

    PLAN_TRANSITIONS: dict[PlanStatus, set[PlanStatus]] = {
        "draft": {"ready", "invalid"},
        "ready": {"running", "invalid"},
        "running": {"succeeded", "failed", "invalid"},
        "failed": {"ready", "invalid"},
        "succeeded": set(),
        "invalid": set(),
    }
    STEP_TRANSITIONS: dict[StepStatus, set[StepStatus]] = {
        "planned": {"ready", "blocked", "abandoned"},
        "ready": {"running", "blocked", "abandoned"},
        "running": {"observed", "failed", "abandoned"},
        "observed": {"verified", "failed", "abandoned"},
        "verified": set(),
        "failed": {"ready", "abandoned"},
        "blocked": {"ready", "abandoned"},
        "abandoned": set(),
        "uncertain": {"abandoned"},
        "obsolete": set(),
    }

    def __init__(
        self,
        *,
        journal: MissionJournal | None = None,
        plans: Iterable[Plan] | None = None,
        on_change: Callable[[], None] | None = None,
    ) -> None:
        self.journal = journal
        self._on_change = on_change or (lambda: None)
        self._lock = RLock()
        self._versions: dict[UUID, dict[int, Plan]] = {}
        for plan in plans or []:
            self._versions.setdefault(plan.plan_id, {})[plan.version] = plan
        for plan_id in self._versions:
            self._validate_history(plan_id)

    def set_journal(self, journal: MissionJournal) -> None:
        with self._lock:
            self.journal = journal

    def create_plan(
        self,
        mission_id: UUID,
        steps: list[Step],
        *,
        budget_usd: float = 0.0,
        max_steps: int = 50,
        plan_id: UUID | None = None,
        rationale: str = "initial plan",
    ) -> Plan:
        with self._lock:
            plan = Plan(
                plan_id=plan_id or UUID(int=0),
                mission_id=mission_id,
                steps=steps,
                budget_usd=budget_usd,
                max_steps=max_steps,
                revision_reason=rationale,
            )
            if plan.plan_id.int == 0:
                from uuid import uuid4

                plan = plan.model_copy(update={"plan_id": uuid4()})
            self._validate_plan(plan)
            if plan.plan_id in self._versions:
                raise PlanValidationError(f"plan {plan.plan_id} already exists")
            self._versions[plan.plan_id] = {1: plan}
            self._event(plan, "plan_created", {"step_count": len(steps)})
            self._changed()
            return plan

    def get_plan(self, plan_id: UUID, version: int | None = None) -> Plan:
        with self._lock:
            history = self._versions.get(plan_id)
            if not history:
                raise UnknownPlan(f"unknown plan {plan_id}")
            selected = version if version is not None else max(history)
            try:
                return history[selected]
            except KeyError as exc:
                raise UnknownPlan(f"unknown plan version {plan_id} v{selected}") from exc

    def history(self, plan_id: UUID) -> list[Plan]:
        with self._lock:
            return [self._versions[plan_id][v] for v in sorted(self._versions.get(plan_id, {}))]

    def revise_plan(
        self,
        plan_id: UUID,
        steps: list[Step],
        *,
        expected_version: int,
        rationale: str,
        budget_usd: float | None = None,
        max_steps: int | None = None,
    ) -> Plan:
        with self._lock:
            current = self.get_plan(plan_id)
            if current.version != expected_version:
                raise ConcurrentPlanModification(
                    f"plan {plan_id} is at v{current.version}, expected v{expected_version}"
                )
            if current.status == "succeeded":
                raise InvalidPlanTransition("a succeeded plan cannot be revised")
            revised = Plan(
                plan_id=current.plan_id,
                mission_id=current.mission_id,
                version=current.version + 1,
                steps=steps,
                budget_usd=current.budget_usd if budget_usd is None else budget_usd,
                max_steps=current.max_steps if max_steps is None else max_steps,
                revision_reason=rationale,
                status="draft",
            )
            self._validate_plan(revised)
            self._versions[plan_id][revised.version] = revised
            self._event(
                revised,
                "plan_revised",
                {"previous_version": current.version, "rationale": rationale},
            )
            self._changed()
            return revised

    def validate_plan(self, plan_id: UUID, *, expected_version: int | None = None) -> Plan:
        with self._lock:
            plan = self._checked_current(plan_id, expected_version)
            self._validate_plan(plan)
            updated = plan.model_copy(
                update={"status": "ready", "updated_at": datetime.now(timezone.utc)}
            )
            self._replace_current(updated)
            self._event(updated, "plan_validated", {"step_count": len(updated.steps)})
            self._changed()
            return updated

    def make_step_ready(
        self,
        plan_id: UUID,
        step_id: UUID,
        facts: dict[str, Any],
        *,
        expected_version: int | None = None,
    ) -> Plan:
        with self._lock:
            plan = self._checked_current(plan_id, expected_version)
            step = self._step(plan, step_id)
            if step.status != "planned":
                raise InvalidPlanTransition(f"step {step_id} cannot become ready from {step.status}")
            if not self._dependencies_verified(plan, step):
                self._event(
                    plan,
                    "step_blocked",
                    {"step_id": str(step_id), "reason": "dependencies are not verified"},
                )
                raise PreconditionNotMet(f"step {step_id} dependencies are not verified")
            if not self._conditions_pass(step.preconditions, facts):
                self._event(
                    plan,
                    "step_blocked",
                    {"step_id": str(step_id), "reason": "preconditions are not satisfied"},
                )
                raise PreconditionNotMet(f"step {step_id} preconditions are not satisfied")
            updated = self._with_step(plan, step.model_copy(update={"status": "ready"}))
            self._replace_current(updated)
            self._event(updated, "step_ready", {"step_id": str(step_id)})
            self._changed()
            return updated

    def start_step(
        self,
        plan_id: UUID,
        step_id: UUID,
        *,
        estimated_cost_usd: float = 0.0,
        expected_version: int | None = None,
    ) -> Plan:
        with self._lock:
            plan = self._checked_current(plan_id, expected_version)
            step = self._step(plan, step_id)
            if step.status != "ready":
                raise InvalidPlanTransition(f"step {step_id} cannot start from {step.status}")
            if estimated_cost_usd < 0 or plan.total_spent_cost_usd + plan.total_reserved_cost_usd + estimated_cost_usd > plan.budget_usd:
                raise StepBudgetExceeded(f"plan budget exceeded before step {step_id}")
            if step.spent_cost_usd + step.reserved_cost_usd + estimated_cost_usd > step.budget_usd:
                raise StepBudgetExceeded(f"step budget exceeded before step {step_id}")
            updated = self._with_step(
                plan,
                step.model_copy(
                    update={
                        "status": "running",
                        "estimated_cost_usd": estimated_cost_usd,
                        "reserved_cost_usd": estimated_cost_usd,
                    }
                ),
            )
            if updated.status == "ready":
                updated = updated.model_copy(update={"status": "running"})
            self._replace_current(updated)
            self._event(updated, "step_started", {"step_id": str(step_id), "estimated_cost_usd": estimated_cost_usd})
            self._changed()
            return updated

    def record_observation(
        self,
        plan_id: UUID,
        step_id: UUID,
        observation: dict[str, Any],
        *,
        actual_cost_usd: float = 0.0,
        expected_version: int | None = None,
    ) -> Plan:
        with self._lock:
            plan = self._checked_current(plan_id, expected_version)
            step = self._step(plan, step_id)
            if step.status != "running":
                raise InvalidPlanTransition(f"step {step_id} cannot be observed from {step.status}")
            if actual_cost_usd < 0 or step.spent_cost_usd + actual_cost_usd > step.budget_usd:
                raise StepBudgetExceeded(f"step budget exceeded after step {step_id}")
            total = plan.total_spent_cost_usd - step.spent_cost_usd + actual_cost_usd
            total += plan.total_reserved_cost_usd - step.reserved_cost_usd
            if total > plan.budget_usd:
                raise StepBudgetExceeded(f"plan budget exceeded after step {step_id}")
            updated_step = step.model_copy(
                update={
                    "status": "observed",
                    "observation": dict(observation),
                    "spent_cost_usd": round(step.spent_cost_usd + actual_cost_usd, 10),
                    "reserved_cost_usd": 0.0,
                }
            )
            updated = self._with_step(plan, updated_step)
            self._replace_current(updated)
            self._event(updated, "observation_added", {"step_id": str(step_id), "actual_cost_usd": actual_cost_usd})
            self._changed()
            return updated

    def verify_step(
        self,
        plan_id: UUID,
        step_id: UUID,
        facts: dict[str, Any] | None = None,
        *,
        expected_version: int | None = None,
    ) -> Plan:
        with self._lock:
            plan = self._checked_current(plan_id, expected_version)
            step = self._step(plan, step_id)
            if step.status != "observed":
                raise InvalidPlanTransition(f"step {step_id} cannot verify from {step.status}")
            source = dict(step.observation or {})
            if facts:
                source.update(facts)
            if not self._conditions_pass(step.postconditions, source):
                updated = self._with_step(plan, step.model_copy(update={"status": "failed", "error": "postcondition not met"}))
                updated = updated.model_copy(update={"status": "failed"})
                self._replace_current(updated)
                self._event(updated, "step_verification_failed", {"step_id": str(step_id)})
                self._changed()
                raise PostconditionNotMet(f"step {step_id} postconditions are not satisfied")
            updated = self._with_step(plan, step.model_copy(update={"status": "verified", "error": None}))
            updated = updated.model_copy(update={"status": self._plan_status_after_step(updated)})
            self._replace_current(updated)
            self._event(updated, "step_verified", {"step_id": str(step_id), "plan_status": updated.status})
            self._changed()
            return updated

    def fail_step(self, plan_id: UUID, step_id: UUID, reason: str, *, expected_version: int | None = None) -> Plan:
        if not reason.strip():
            raise PlanEngineError("failure reason must not be empty")
        with self._lock:
            plan = self._checked_current(plan_id, expected_version)
            step = self._step(plan, step_id)
            if step.status not in {"ready", "running", "observed"}:
                raise InvalidPlanTransition(f"step {step_id} cannot fail from {step.status}")
            updated = self._with_step(
                plan,
                step.model_copy(update={"status": "failed", "error": reason, "reserved_cost_usd": 0.0}),
            )
            updated = updated.model_copy(update={"status": "failed"})
            self._replace_current(updated)
            self._event(updated, "step_failed", {"step_id": str(step_id), "reason": reason})
            self._changed()
            return updated

    def mark_step_uncertain(
        self,
        plan_id: UUID,
        step_id: UUID,
        reason: str,
        *,
        expected_version: int | None = None,
    ) -> Plan:
        if not reason.strip():
            raise PlanEngineError("uncertainty reason must not be empty")
        with self._lock:
            plan = self._checked_current(plan_id, expected_version)
            step = self._step(plan, step_id)
            if step.status not in {"running", "observed"}:
                raise InvalidPlanTransition(f"step {step_id} cannot become uncertain from {step.status}")
            updated = self._with_step(
                plan,
                step.model_copy(update={"status": "uncertain", "error": reason, "reserved_cost_usd": 0.0}),
            )
            self._replace_current(updated)
            self._event(updated, "step_uncertain", {"step_id": str(step_id), "reason": reason})
            self._changed()
            return updated

    def snapshot(self) -> list[dict[str, Any]]:
        with self._lock:
            return [plan.model_dump(mode="json") for history in self._versions.values() for plan in history.values()]

    @classmethod
    def from_snapshot(
        cls,
        plans: list[dict[str, Any]],
        *,
        journal: MissionJournal | None = None,
        on_change: Callable[[], None] | None = None,
    ) -> "PlanEngine":
        return cls(
            plans=[Plan.model_validate(item) for item in plans],
            journal=journal,
            on_change=on_change,
        )

    def _changed(self) -> None:
        self._on_change()

    def _event(self, plan: Plan, event_type: str, payload: dict[str, Any]) -> None:
        if self.journal is not None:
            self.journal.append(
                plan.mission_id,
                event_type,
                "plan_engine",
                {"plan_id": str(plan.plan_id), "version": plan.version, **payload},
            )

    def _checked_current(self, plan_id: UUID, expected_version: int | None) -> Plan:
        plan = self.get_plan(plan_id)
        if expected_version is not None and plan.version != expected_version:
            raise ConcurrentPlanModification(
                f"plan {plan_id} is at v{plan.version}, expected v{expected_version}"
            )
        return plan

    def _replace_current(self, plan: Plan) -> None:
        self._versions[plan.plan_id][plan.version] = plan

    def _with_step(self, plan: Plan, step: Step) -> Plan:
        steps = [step if item.step_id == step.step_id else item for item in plan.steps]
        return plan.model_copy(
            update={
                "steps": steps,
                "updated_at": datetime.now(timezone.utc),
                "spent_cost_usd": round(sum(item.spent_cost_usd for item in steps), 10),
            }
        )

    @staticmethod
    def _step(plan: Plan, step_id: UUID) -> Step:
        for step in plan.steps:
            if step.step_id == step_id:
                return step
        raise UnknownStep(f"unknown step {step_id} in plan {plan.plan_id}")

    @staticmethod
    def _dependencies_verified(plan: Plan, step: Step) -> bool:
        statuses = {item.step_id: item.status for item in plan.steps}
        return all(statuses.get(dependency) == "verified" for dependency in step.depends_on)

    @staticmethod
    def _conditions_pass(conditions: list[DeterministicCondition], facts: dict[str, Any]) -> bool:
        return all(condition.evaluate(facts) for condition in conditions)

    def _plan_status_after_step(self, plan: Plan) -> PlanStatus:
        active_statuses = {step.status for step in plan.steps if step.status != "obsolete"}
        if active_statuses == {"verified"}:
            return "succeeded"
        if "failed" in active_statuses or "uncertain" in active_statuses:
            return "failed"
        if plan.status in {"draft", "ready"}:
            return "running"
        return plan.status

    def _validate_history(self, plan_id: UUID) -> None:
        versions = sorted(self._versions[plan_id])
        if versions != list(range(1, len(versions) + 1)):
            raise PlanValidationError(f"plan {plan_id} has non-contiguous version history")
        for plan in self._versions[plan_id].values():
            self._validate_plan(plan)

    def _validate_plan(self, plan: Plan) -> None:
        if len(plan.steps) > plan.max_steps:
            raise PlanValidationError("plan exceeds max_steps")
        if plan.budget_usd < 0:
            raise PlanValidationError("plan budget must be non-negative")
        step_ids = {step.step_id for step in plan.steps}
        if not step_ids:
            raise PlanValidationError("plan must contain at least one step")
        if any(step.action_ref.strip() == "" for step in plan.steps):
            raise PlanValidationError("every step requires an action_ref")
        if any(step.budget_usd < 0 for step in plan.steps):
            raise PlanValidationError("step budgets must be non-negative")
        if any(step.spent_cost_usd + step.reserved_cost_usd > step.budget_usd for step in plan.steps):
            raise PlanValidationError("step consumed and reserved costs exceed step budget")
        if plan.total_spent_cost_usd + plan.total_reserved_cost_usd > plan.budget_usd:
            raise PlanValidationError("consumed and reserved costs exceed plan budget")
        if sum(step.budget_usd for step in plan.steps) > plan.budget_usd:
            raise PlanValidationError("sum of step budgets exceeds plan budget")
        graph = {step.step_id: set(step.depends_on) for step in plan.steps}
        for step_id, dependencies in graph.items():
            missing = dependencies - step_ids
            if missing:
                raise PlanValidationError(f"step {step_id} has missing dependencies: {sorted(map(str, missing))}")
            if step_id in dependencies:
                raise PlanValidationError(f"step {step_id} cannot depend on itself")
        self._assert_acyclic(graph)

    @staticmethod
    def _assert_acyclic(graph: dict[UUID, set[UUID]]) -> None:
        visiting: set[UUID] = set()
        visited: set[UUID] = set()

        def visit(node: UUID) -> None:
            if node in visiting:
                raise PlanValidationError("plan dependencies contain a cycle")
            if node in visited:
                return
            visiting.add(node)
            for dependency in graph[node]:
                visit(dependency)
            visiting.remove(node)
            visited.add(node)

        for node in graph:
            visit(node)
