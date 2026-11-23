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
        if goal.confidence < 0.5 and not goal.hypotheses:
            raise MissionCompilationError("low-confidence goal requires explicit hypotheses")
        return goal


class MissionCompiler:
    """Compile a goal into bounded, inspectable mission structure."""

    def compile(self, goal: GoalUnderstanding) -> CompiledMission:
        goal = GoalUnderstandingEngine.validate(goal)
        subgoals = list(goal.expected_results)
        dependencies = {subgoal: subgoals[:index] for index, subgoal in enumerate(subgoals)}
        missing = list(dict.fromkeys(goal.unknowns))
        if goal.constraints.get("required_information"):
            missing.extend(str(item) for item in goal.constraints["required_information"])
        missing = list(dict.fromkeys(item for item in missing if item.strip()))
        if goal.constraints.get("require_complete_information") and missing:
            raise MissionCompilationError(f"mission is missing information: {missing}")
        return CompiledMission(
            objective=goal.objective,
            expected_results=subgoals,
            subgoals=subgoals,
            dependencies=dependencies,
            constraints=dict(goal.constraints),
            success_criteria=list(goal.success_criteria),
            missing_information=missing,
            assumptions=list(goal.hypotheses),
            confidence=goal.confidence,
        )


class StrategyEngine:
    """Generate and compare strategies without a model or external effect."""

    def propose(self, mission: CompiledMission) -> list[StrategyCandidate]:
        return [
            StrategyCandidate(
                name="direct-bounded",
                objective=mission.objective,
                planned_steps=list(mission.subgoals),
                preconditions=list(mission.missing_information),
                estimated_cost_usd=round(max(len(mission.subgoals), 1) * 0.5, 10),
                risks=["limited correction path"],
                advantages=["shortest deterministic path"],
                limits=["requires complete observations"],
                success_criteria=list(mission.success_criteria),
                score=1.0,
            ),
            StrategyCandidate(
                name="staged-verified",
                objective=mission.objective,
                planned_steps=[f"verify:{item}" for item in mission.subgoals],
                preconditions=list(mission.missing_information),
                estimated_cost_usd=round(max(len(mission.subgoals), 1) * 0.75, 10),
                risks=["higher declared cost"],
                advantages=["explicit verification boundary", "safer correction point"],
                limits=["requires an observation per stage"],
                success_criteria=list(mission.success_criteria),
                score=1.2,
            ),
        ]

    def choose(self, candidates: Iterable[StrategyCandidate], *, budget_usd: float) -> StrategySelection:
        candidates = list(candidates)
        eligible = [candidate for candidate in candidates if candidate.estimated_cost_usd <= budget_usd]
        if not eligible:
            raise StrategySelectionError("budget is insufficient for every strategy")
        ordered = sorted(
            eligible,
            key=lambda item: (-item.score, item.estimated_cost_usd, item.name, str(item.strategy_id)),
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
                f"highest deterministic score ({winner.score})",
                f"estimated cost {winner.estimated_cost_usd} <= budget {budget_usd}",
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
    ) -> tuple[StrategySelection, CognitiveDecision]:
        candidates = list(candidates)
        selection = StrategyEngine().choose(candidates, budget_usd=budget_usd)
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
    ) -> tuple[ObservationAssessment, CognitiveDecision]:
        outcome = "success" if verified else "failure"
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
            kind="keep" if verified else "revise",
            subject_id=cycle_id,
            reasons=["postconditions verified" if verified else "postconditions not verified"],
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
    ):
        current = plan_engine.get_plan(plan_id)
        preserved = [step for step in current.steps if step.status == "verified"]
        failed = [step for step in current.steps if step.status == "failed"]
        if not failed:
            raise CognitiveEngineError("replanning requires a failed step")
        remaining = round(current.budget_usd - sum(step.budget_usd for step in current.steps), 10)
        if remaining <= 0:
            raise CognitiveEngineError("no remaining budget for controlled correction")
        correction = Step(
            ordinal=max(step.ordinal for step in current.steps) + 1,
            title=correction_title,
            action_ref=f"cognitive.correction:{failed[-1].step_id}",
            depends_on=[step.step_id for step in preserved[-1:]],
            postconditions=[DeterministicCondition(key="ok", expected=True)],
            idempotency_key=f"correction:{current.plan_id}:{current.version}:{failed[-1].step_id}",
            budget_usd=remaining,
        )
        return plan_engine.revise_plan(
            plan_id,
            preserved + [correction],
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
        journal: MissionJournal | None = None,
        cycles: Iterable[CognitiveCycle] | None = None,
        on_change: Callable[[], None] | None = None,
        mode: Literal["CORE_ONLY", "AI_ENABLED"] = "CORE_ONLY",
        ai_enabled: bool | None = None,
    ) -> None:
        self.plan_engine = plan_engine
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
    ) -> CognitiveCycle:
        with self._lock:
            mission = MissionCompiler().compile(goal)
            budget = mission.constraints.get("budget_usd", 5.0) if budget_usd is None else budget_usd
            candidates = StrategyEngine().propose(mission)
            selection, decision = CognitiveDecisionEngine().select_strategy(
                candidates,
                budget_usd=float(budget),
                llm_recommendation=llm_recommendation if self.mode == "AI_ENABLED" else None,
            )
            chosen = next(candidate for candidate in candidates if candidate.strategy_id == selection.strategy_id)
            per_step = round(chosen.estimated_cost_usd / len(chosen.planned_steps), 10)
            steps = [
                Step(
                    ordinal=index,
                    title=title,
                    action_ref=f"cognitive:{chosen.strategy_id}:{index}",
                    depends_on=[],
                    postconditions=[DeterministicCondition(key="ok", expected=True)],
                    idempotency_key=f"cognitive:{mission.mission_id}:{chosen.strategy_id}:{index}",
                    budget_usd=per_step,
                )
                for index, title in enumerate(chosen.planned_steps, start=1)
            ]
            steps = [
                item.model_copy(update={"depends_on": [steps[index - 2].step_id] if index > 1 else []})
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

    def observe(
        self,
        cycle_id: UUID,
        step_id: UUID,
        observation: dict[str, Any],
        *,
        actual_cost_usd: float = 0.0,
    ) -> ObservationAssessment:
        with self._lock:
            cycle = self._cycles[cycle_id]
            plan = self.plan_engine.get_plan(cycle.plan_id)
            step = next(step for step in plan.steps if step.step_id == step_id)
            plan = self.plan_engine.record_observation(
                cycle.plan_id, step_id, observation, actual_cost_usd=actual_cost_usd
            )
            try:
                self.plan_engine.verify_step(cycle.plan_id, step_id)
                verified = True
            except PostconditionNotMet:
                verified = False
            assessment, decision = CognitiveDecisionEngine.assess_observation(
                cycle_id, step_id, observation,
                expected=[condition.key for condition in step.postconditions],
                verified=verified,
            )
            updated = cycle.model_copy(
                deep=True,
                update={
                    "observations": [*cycle.observations, assessment],
                    "decisions": [*cycle.decisions, decision],
                    "status": "succeeded" if verified and self.plan_engine.get_plan(cycle.plan_id).status == "succeeded" else ("failed" if not verified else "running"),
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
        journal: MissionJournal | None = None,
        on_change: Callable[[], None] | None = None,
    ) -> "CognitiveEngine":
        return cls(
            plan_engine=plan_engine,
            journal=journal,
            cycles=[CognitiveCycle.model_validate(item) for item in plans],
            on_change=on_change,
        )

    def _changed(self) -> None:
        self._on_change()

    def _event(self, cycle: CognitiveCycle, event_type: str, payload: dict[str, Any]) -> None:
        if self.journal is not None:
            self.journal.append(cycle.mission.mission_id, event_type, "cognitive_engine", payload)
