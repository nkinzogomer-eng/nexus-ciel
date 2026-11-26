from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from threading import RLock
from typing import TYPE_CHECKING, Any, Callable, Iterable, Literal
from uuid import UUID

from nexus.planning import (
    DeterministicCondition,
    PlanEngine,
    PlanEngineError,
    PostconditionNotMet,
    Step,
)

from .models import (
    CognitiveCycle,
    CognitiveDecision,
    CompiledMission,
    GoalUnderstanding,
    Hypothesis,
    MissingInformation,
    ObservationAssessment,
    StrategyCandidate,
    StrategySelection,
)

if TYPE_CHECKING:
    from nexus.core.mission_journal import MissionJournal


class CognitiveEngineError(ValueError):
    """Base error for controlled cognitive-cycle operations."""


class MissionCompilationError(CognitiveEngineError):
    """Raised when a structured goal is incoherent or insufficiently defined."""


class StrategySelectionError(CognitiveEngineError):
    """Raised when no candidate satisfies deterministic constraints."""


class GoalUnderstandingEngine:
    """Normalise and validate the structured goal boundary."""

    @staticmethod
    def validate(goal: GoalUnderstanding) -> GoalUnderstanding:
        if not goal.objective.strip():
            raise MissionCompilationError("objective must not be blank")
        if any(not result.strip() for result in goal.expected_results):
            raise MissionCompilationError("expected results must not be blank")
        if any(not criterion.strip() for criterion in goal.success_criteria):
            raise MissionCompilationError("success criteria must not be blank")
        if len(set(goal.expected_results)) != len(goal.expected_results):
            raise MissionCompilationError("expected results must be unique")
        if float(goal.constraints.get("budget_usd", 0.0)) < 0:
            raise MissionCompilationError("budget constraint must be non-negative")
        forbidden = set(goal.constraints.get("forbidden_results", []))
        if forbidden.intersection(goal.expected_results):
            raise MissionCompilationError("constraints forbid an expected result")
        if goal.confidence < 0.5 and not goal.hypotheses:
            raise MissionCompilationError("low-confidence goal requires explicit hypotheses")
        return goal


class MissionCompiler:
    """Compile a goal into bounded, inspectable mission structure."""

    def compile(self, goal: GoalUnderstanding) -> CompiledMission:
        goal = GoalUnderstandingEngine.validate(goal)
        subgoals = list(goal.expected_results)
        dependencies = {subgoal: subgoals[:index] for index, subgoal in enumerate(subgoals)}
        details: list[MissingInformation] = []
        for item in goal.unknowns:
            if item not in goal.known_facts:
                details.append(
                    MissingInformation(
                        name=item,
                        classification="non_blocking",
                        reason="unknown but not declared indispensable",
                    )
                )

        for item in goal.constraints.get("required_information", []):
            if isinstance(item, dict):
                name = str(item.get("name", "")).strip()
                classification = item.get("classification", "blocking")
                reason = str(item.get("reason", "required by mission constraints"))
            else:
                name = str(item).strip()
                classification = "blocking"
                reason = "required by mission constraints"
            if name and name not in goal.known_facts:
                details.append(MissingInformation(name=name, classification=classification, reason=reason))
        unique_details = {item.name: item for item in details}
        details = list(unique_details.values())
        missing = list(unique_details)
        blocking = [item.name for item in details if item.classification == "blocking"]
        if goal.constraints.get("require_complete_information") and blocking:
            raise MissionCompilationError(f"mission is missing blocking information: {blocking}")
        return CompiledMission(
            objective=goal.objective,
            expected_results=subgoals,
            subgoals=subgoals,
            dependencies=dependencies,
            constraints=dict(goal.constraints),
            success_criteria=list(goal.success_criteria),
            missing_information=missing,
            missing_information_details=details,
            assumptions=list(goal.hypotheses),
            confidence=goal.confidence,
        )


class StrategyEngine:
    """Generate and compare strategies without a model or external effect."""

    def propose(self, mission: CompiledMission) -> list[StrategyCandidate]:
        dependencies = dict(mission.dependencies)
        blocking = [
            item.name
            for item in mission.missing_information_details
            if item.classification == "blocking"
        ]
        return [
            StrategyCandidate(
                name="direct-bounded",
                objective=mission.objective,
                planned_steps=list(mission.subgoals),
                dependencies=dependencies,
                preconditions=blocking,
                estimated_cost_usd=round(max(len(mission.subgoals), 1) * 0.5, 10),
                estimated_duration_s=float(max(len(mission.subgoals), 1) * 60),
                risks=["limited correction path"],
                advantages=["shortest deterministic path"],
                limits=["requires complete observations"],
                success_criteria=list(mission.success_criteria),
                score=1.0,
                risk_level=0.5,
                uncertainty=0.3,
                required_information=blocking,
                score_justification=["fewer steps", "higher declared correction risk"],
            ),
            StrategyCandidate(
                name="staged-verified",
                objective=mission.objective,
                planned_steps=[f"verify:{item}" for item in mission.subgoals],
                dependencies=dependencies,
                preconditions=blocking,
                estimated_cost_usd=round(max(len(mission.subgoals), 1) * 0.75, 10),
                estimated_duration_s=float(max(len(mission.subgoals), 1) * 90),
                risks=["higher declared cost"],
                advantages=["explicit verification boundary", "safer correction point"],
                limits=["requires an observation per stage"],
                success_criteria=list(mission.success_criteria),
                score=1.2,
                risk_level=0.2,
                uncertainty=0.1,
                required_information=blocking,
                score_justification=["stronger verification", "lower uncertainty"],
            ),
            StrategyCandidate(
                name="cost-minimal-checkpointed",
                objective=mission.objective,
                planned_steps=[f"checkpoint:{item}" for item in mission.subgoals],
                dependencies=dependencies,
                preconditions=blocking,
                estimated_cost_usd=round(max(len(mission.subgoals), 1) * 0.25, 10),
                estimated_duration_s=float(max(len(mission.subgoals), 1) * 120),
                risks=["slower progress", "higher uncertainty"],
                advantages=["lowest declared cost", "reversible checkpoints"],
                limits=["not suitable for urgent deadlines"],
                success_criteria=list(mission.success_criteria),
                score=0.85,
                risk_level=0.7,
                uncertainty=0.5,
                required_information=blocking,
                score_justification=["lowest cost", "penalized for risk and duration"],
            ),
        ]

    def choose(
        self,
        candidates: Iterable[StrategyCandidate],
        *,
        budget_usd: float,
        available_information: set[str] | None = None,
        constraints: dict[str, Any] | None = None,
    ) -> StrategySelection:
        candidates = list(candidates)
        available = available_information or set()
        constraints = constraints or {}
        rejected_reasons: dict[UUID, str] = {}
        eligible = []
        for candidate in candidates:
            if candidate.estimated_cost_usd > budget_usd:
                rejected_reasons[candidate.strategy_id] = "estimated cost exceeds budget"
            elif candidate.constraint_violations:
                rejected_reasons[candidate.strategy_id] = "candidate violates mandatory constraints"
            elif set(candidate.required_information) - available:
                rejected_reasons[candidate.strategy_id] = "required information is unavailable"
            elif constraints.get("require_reversible") and not candidate.reversible:
                rejected_reasons[candidate.strategy_id] = "candidate is not reversible"
            else:
                eligible.append(candidate)
        if not eligible:
            details = "; ".join(rejected_reasons.values()) or "no candidate satisfies constraints"
            raise StrategySelectionError(f"no strategy is acceptable: {details}")
        ordered = sorted(
            eligible,
            key=lambda item: (
                -(item.score - item.risk_level * 0.2 - item.uncertainty * 0.2),
                item.estimated_cost_usd,
                item.name,
                str(item.strategy_id),
            ),
        )
        winner = ordered[0]
        rejected = [candidate.strategy_id for candidate in candidates if candidate.strategy_id != winner.strategy_id]
        deterministic_key = "|".join(
            f"{candidate.name}:{candidate.score}:{candidate.estimated_cost_usd}"
            for candidate in ordered
        )
        return StrategySelection(
            strategy_id=winner.strategy_id,
            candidate_name=winner.name,
            reasons=[
                f"highest deterministic adjusted score ({winner.score - winner.risk_level * 0.2 - winner.uncertainty * 0.2:.3f})",
                f"estimated cost {winner.estimated_cost_usd} <= budget {budget_usd}",
                *winner.score_justification,
            ],
            rejected_candidates=rejected,
            deterministic_key=deterministic_key,
        )


class CognitiveDecisionEngine:
    """Final authority for internal decisions; LLM advice remains non-authoritative."""

    def select_strategy(
        self,
        candidates: Iterable[StrategyCandidate],
        *,
        budget_usd: float,
        llm_recommendation: str | None = None,
        available_information: set[str] | None = None,
        constraints: dict[str, Any] | None = None,
    ) -> tuple[StrategySelection, CognitiveDecision]:
        candidates = list(candidates)
        selection = StrategyEngine().choose(
            candidates,
            budget_usd=budget_usd,
            available_information=available_information,
            constraints=constraints,
        )
        digest = None
        if llm_recommendation is not None:
            digest = hashlib.sha256(llm_recommendation.encode()).hexdigest()
        decision = CognitiveDecision(
            kind="select_strategy",
            subject_id=selection.strategy_id,
            reasons=list(selection.reasons),
            evidence=["deterministic candidate comparison"],
            llm_advice_digest=digest,
        )
        return selection, decision

    @staticmethod
    def assess_observation(
        cycle_id: UUID,
        step_id: UUID,
        observation: dict[str, Any],
        *,
        expected: list[str],
        verified: bool,
        outcome_override: Literal["success", "failure", "partial", "uncertain"] | None = None,
    ) -> tuple[ObservationAssessment, CognitiveDecision]:
        requested_outcome = outcome_override or ("success" if verified else "failure")
        outcome = "failure" if requested_outcome == "success" and not verified else requested_outcome
        divergence = [] if verified else ["observed data did not satisfy deterministic postconditions"]
        assessment = ObservationAssessment(
            step_id=step_id,
            outcome=outcome,
            observed=dict(observation),
            expected=expected,
            divergence=divergence,
            evidence=["step observation"],
        )
        decision = CognitiveDecision(
            kind="keep" if outcome == "success" else ("suspend" if outcome in {"partial", "uncertain"} else "revise"),
            subject_id=cycle_id,
            reasons=["postconditions verified" if outcome == "success" else f"declared outcome {requested_outcome} was not accepted: {outcome}"],
            evidence=[str(assessment.observation_id)],
        )
        return assessment, decision


class ControlledReplanner:
    """Create a new plan version without replaying an external action."""

    def revise_after_failure(
        self,
        plan_engine: PlanEngine,
        plan_id: UUID,
        *,
        reason: str,
        correction_title: str = "controlled-correction",
        correction_tool: str = "calculate",
    ):
        current = plan_engine.get_plan(plan_id)
        failed = [step for step in current.steps if step.status == "failed"]
        if not failed:
            raise CognitiveEngineError("replanning requires a failed step")
        failed_ids = {step.step_id for step in failed}
        failed_target = failed[-1]
        preserved = []
        impacted_step_ids: set[UUID] = set()
        for step in current.steps:
            if step.step_id in failed_ids or step.status == "obsolete":
                continue
            budget = step.budget_usd
            if step.status == "verified":
                budget = step.spent_cost_usd
            elif step.status == "uncertain":
                budget = step.spent_cost_usd
            dependencies = [dependency for dependency in step.depends_on if dependency not in failed_ids]
            if any(dependency in failed_ids for dependency in step.depends_on):
                impacted_step_ids.add(step.step_id)
            status = step.status
            preserved.append(
                step.model_copy(
                    update={
                        "depends_on": dependencies,
                        "status": "planned" if any(dependency in failed_ids for dependency in step.depends_on) else status,
                        "budget_usd": budget,
                        "reserved_cost_usd": 0.0,
                    }
                )
            )
        future_budget = sum(
            step.budget_usd for step in preserved if step.status in {"planned", "ready"}
        )
        remaining = round(current.budget_usd - current.total_spent_cost_usd - future_budget, 10)
        if remaining <= 0:
            raise CognitiveEngineError("no remaining budget for controlled correction")
        correction = Step(
            ordinal=failed_target.ordinal,
            title=correction_title,
                action_ref=f"tool:{correction_tool}",
            depends_on=[
                dependency
                for dependency in failed_target.depends_on
                if any(step.step_id == dependency and step.status == "verified" for step in preserved)
            ],
            postconditions=[DeterministicCondition(key="ok", expected=True)],
            idempotency_key=f"correction:{current.plan_id}:{current.version}:{failed_target.step_id}",
            justification=reason,
            budget_usd=remaining,
            estimated_cost_usd=remaining,
        )
        rewritten = []
        for step in preserved:
            dependencies = list(step.depends_on)
            if step.step_id in impacted_step_ids:
                dependencies.append(correction.step_id)
            rewritten.append(step.model_copy(update={"depends_on": list(dict.fromkeys(dependencies))}))
        return plan_engine.revise_plan(
            plan_id,
            sorted([*rewritten, correction], key=lambda step: step.ordinal),
            expected_version=current.version,
            rationale=reason,
            budget_usd=current.budget_usd,
            max_steps=current.max_steps,
        )


class CognitiveEngine:
    """Persistent deterministic cognitive-cycle coordinator."""

    def __init__(
        self,
        *,
        plan_engine: PlanEngine,
        action_executor: Any | None = None,
        journal: MissionJournal | None = None,
        cycles: Iterable[CognitiveCycle] | None = None,
        on_change: Callable[[], None] | None = None,
        mode: Literal["CORE_ONLY", "AI_ENABLED"] = "CORE_ONLY",
        ai_enabled: bool | None = None,
    ) -> None:
        self.plan_engine = plan_engine
        self.action_executor = action_executor
        self.journal = journal
        self._on_change = on_change or (lambda: None)
        self.mode = "AI_ENABLED" if ai_enabled is True else ("CORE_ONLY" if ai_enabled is False else mode)
        self._lock = RLock()
        self._cycles = {cycle.cycle_id: cycle for cycle in cycles or []}

    def start(
        self,
        goal: GoalUnderstanding,
        *,
        budget_usd: float | None = None,
        llm_recommendation: str | None = None,
        action_tool: str | None = None,
    ) -> CognitiveCycle:
        with self._lock:
            mission = MissionCompiler().compile(goal)
            budget = mission.constraints.get("budget_usd", 5.0) if budget_usd is None else budget_usd
            candidates = StrategyEngine().propose(mission)
            selection, decision = CognitiveDecisionEngine().select_strategy(
                candidates,
                budget_usd=float(budget),
                llm_recommendation=llm_recommendation if self.mode == "AI_ENABLED" else None,
                available_information=set(goal.known_facts),
                constraints=mission.constraints,
            )
            chosen = next(candidate for candidate in candidates if candidate.strategy_id == selection.strategy_id)
            per_step = round(chosen.estimated_cost_usd / len(chosen.planned_steps), 10)
            step_by_subgoal = {
                subgoal: index
                for index, subgoal in enumerate(mission.subgoals, start=1)
                if index <= len(chosen.planned_steps)
            }
            steps = [
                Step(
                    ordinal=index,
                    title=title,
                    action_ref=(f"tool:{action_tool}" if action_tool else f"cognitive:{chosen.strategy_id}:{index}"),
                    depends_on=[],
                    postconditions=[DeterministicCondition(key="ok", expected=True)],
                    idempotency_key=f"cognitive:{mission.mission_id}:{chosen.strategy_id}:{index}",
                    budget_usd=per_step,
                )
                for index, title in enumerate(chosen.planned_steps, start=1)
            ]
            steps = [
                item.model_copy(
                    update={
                        "depends_on": [steps[dependency - 1].step_id for dependency in [
                            step_by_subgoal[name]
                            for name in chosen.dependencies.get(mission.subgoals[index - 1], [])
                            if name in step_by_subgoal and step_by_subgoal[name] < index
                        ]]
                    }
                )
                for index, item in enumerate(steps, start=1)
            ]
            plan = self.plan_engine.create_plan(
                mission.mission_id,
                steps,
                budget_usd=float(budget),
                rationale=f"strategy selected: {chosen.name}",
            )
            self.plan_engine.validate_plan(plan.plan_id)
            cycle = CognitiveCycle(
                goal=goal,
                mission=mission,
                candidates=candidates,
                selection=selection,
                plan_id=plan.plan_id,
                mode=self.mode,
                decisions=[decision],
                status="running",
            )
            self._cycles[cycle.cycle_id] = cycle
            self._event(cycle, "cognitive_cycle_started", {"plan_id": str(plan.plan_id)})
            self._changed()
            return cycle

    def execute_action(
        self,
        cycle_id: UUID,
        step_id: UUID,
        request: Any,
        *,
        granted_permissions: set[str] | None = None,
        facts: dict[str, Any] | None = None,
        approval: bool = False,
    ) -> Any:
        """Execute one registered action for the exact current plan step."""
        if self.action_executor is None:
            raise CognitiveEngineError("action executor is not configured")
        cycle = self._cycles[cycle_id]
        if request.mission_id != cycle.mission.mission_id or request.plan_id != cycle.plan_id or request.step_id != step_id:
            raise CognitiveEngineError("action request is not bound to the cognitive cycle and step")
        plan = self.plan_engine.get_plan(cycle.plan_id)
        step = next(item for item in plan.steps if item.step_id == step_id)
        if step.action_ref != f"tool:{request.tool_name}":
            raise CognitiveEngineError("requested tool does not match the registered plan step")
        if step.status == "planned":
            self.plan_engine.make_step_ready(cycle.plan_id, step_id, facts or {})
        spec = self.action_executor.registry.get(request.tool_name)
        if spec is None:
            raise CognitiveEngineError("requested tool is not registered")
        if (spec.requires_approval or spec.risk_level == "high") and not approval:
            from nexus.actions import ApprovalRequired

            raise ApprovalRequired(f"approval required for tool {spec.name}")
        if step.status in {"planned", "ready"}:
            self.plan_engine.start_step(cycle.plan_id, step_id, estimated_cost_usd=spec.estimated_cost_usd)
        try:
            result = self.action_executor.execute(
                request,
                granted_permissions=granted_permissions,
                facts=facts,
                approval=approval,
                budget_remaining_usd=self.plan_engine.get_plan(cycle.plan_id).budget_usd - self.plan_engine.get_plan(cycle.plan_id).total_spent_cost_usd,
            )
        except Exception:
            raise
        if result.status in {"succeeded", "partial", "uncertain", "interrupted_uncertain"}:
            self.observe(cycle_id, step_id, result.observation, actual_cost_usd=result.actual_cost_usd, outcome=result.outcome or "uncertain")
        elif result.status in {"failed", "rejected"}:
            self.plan_engine.fail_step(cycle.plan_id, step_id, result.error or "action rejected")
        return result

    def observe(
        self,
        cycle_id: UUID,
        step_id: UUID,
        observation: dict[str, Any],
        *,
        actual_cost_usd: float = 0.0,
        outcome: Literal["auto", "success", "failure", "partial", "uncertain"] = "auto",
    ) -> ObservationAssessment:
        with self._lock:
            cycle = self._cycles[cycle_id]
            plan = self.plan_engine.get_plan(cycle.plan_id)
            step = next(step for step in plan.steps if step.step_id == step_id)
            plan = self.plan_engine.record_observation(
                cycle.plan_id, step_id, observation, actual_cost_usd=actual_cost_usd
            )
            verified = False
            if outcome in {"partial", "uncertain"}:
                self.plan_engine.mark_step_uncertain(
                    cycle.plan_id,
                    step_id,
                    f"observation classified as {outcome}; external verification required",
                )
            elif outcome == "failure":
                self.plan_engine.fail_step(cycle.plan_id, step_id, "observation explicitly failed")
            else:
                try:
                    self.plan_engine.verify_step(cycle.plan_id, step_id)
                    verified = True
                except PostconditionNotMet:
                    verified = False
            assessment, decision = CognitiveDecisionEngine.assess_observation(
                cycle_id, step_id, observation,
                expected=[condition.key for condition in step.postconditions],
                verified=verified,
                outcome_override=None if outcome == "auto" else outcome,
            )
            updated = cycle.model_copy(
                deep=True,
                update={
                    "observations": [*cycle.observations, assessment],
                    "decisions": [*cycle.decisions, decision],
                    "status": "succeeded" if verified and self.plan_engine.get_plan(cycle.plan_id).status == "succeeded" else ("suspended" if outcome in {"partial", "uncertain"} else ("failed" if not verified else "running")),
                    "updated_at": datetime.now(timezone.utc),
                },
            )
            self._cycles[cycle_id] = updated
            self._event(updated, "cognitive_observation_assessed", {"step_id": str(step_id), "outcome": assessment.outcome})
            self._changed()
            return assessment

    def revise_after_failure(self, cycle_id: UUID, *, reason: str) -> CognitiveCycle:
        with self._lock:
            cycle = self._cycles[cycle_id]
            plan = ControlledReplanner().revise_after_failure(self.plan_engine, cycle.plan_id, reason=reason)
            decision = CognitiveDecision(
                kind="revise",
                subject_id=cycle.plan_id,
                reasons=[reason],
                evidence=["failed observation"],
            )
            updated = cycle.model_copy(
                deep=True,
                update={"decisions": [*cycle.decisions, decision], "status": "running", "updated_at": datetime.now(timezone.utc)},
            )
            self._cycles[cycle_id] = updated
            self._event(updated, "cognitive_plan_revised", {"plan_id": str(plan.plan_id), "version": plan.version, "reason": reason})
            self._changed()
            return updated

    def get_cycle(self, cycle_id: UUID) -> CognitiveCycle:
        with self._lock:
            return self._cycles[cycle_id]

    def snapshot(self) -> list[dict[str, Any]]:
        with self._lock:
            return [cycle.model_dump(mode="json") for cycle in self._cycles.values()]

    @classmethod
    def from_snapshot(
        cls,
        plans: list[dict[str, Any]],
        *,
        plan_engine: PlanEngine,
        action_executor: Any | None = None,
        journal: MissionJournal | None = None,
        on_change: Callable[[], None] | None = None,
    ) -> "CognitiveEngine":
        return cls(
            plan_engine=plan_engine,
            action_executor=action_executor,
            journal=journal,
            cycles=[CognitiveCycle.model_validate(item) for item in plans],
            on_change=on_change,
        )

    def _changed(self) -> None:
        self._on_change()

    def _event(self, cycle: CognitiveCycle, event_type: str, payload: dict[str, Any]) -> None:
        if self.journal is not None:
            self.journal.append(cycle.mission.mission_id, event_type, "cognitive_engine", payload)
