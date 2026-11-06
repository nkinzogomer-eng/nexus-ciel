from __future__ import annotations

import asyncio
import hashlib
import json
import time
from typing import Any

from nexus.bus import AsyncEventBus
from nexus.schemas import Event, Mission, Report

from .capability_registry import CapabilityRegistry
from .mission_journal import MissionJournal
from .mission_guard import MissionGuard, MissionGuardViolation
from .mission_planner import DeterministicMissionCompiler, MissionPlanError
from .state_graph import StateGraph
from .tool_registry import ToolAuthorizationError, ToolExecutionError, ToolRegistry
from .verification import DeterministicOutputVerifier


class NexusRuntime:
    """Bounded multi-step mission execution with explicit proof semantics."""

    def __init__(self, router: object | None = None, verifier: object | None = None) -> None:
        self.bus = AsyncEventBus()
        self.state_graph = StateGraph()
        self.journal = MissionJournal()
        self.registry = CapabilityRegistry()
        self.tool_registry = ToolRegistry()
        self.reports: dict[str, Report] = {}
        self.router = router
        self.verifier = verifier or DeterministicOutputVerifier()
        self.guard = MissionGuard()
        self.compiler = DeterministicMissionCompiler()

    async def accept(self, mission: Mission) -> str:
        started = time.perf_counter()
        self.state_graph.create(mission)
        self.journal.append(mission.mission_id, "mission_accepted", "manas", mission.model_dump(mode="json"))
        await self.bus.publish(
            Event(type="MissionAccepted", mission_id=mission.mission_id, payload={"objective": mission.objective})
        )
        self.state_graph.update(mission.mission_id, status="in_progress", iterations=0)
        report = await self._execute_mission(mission, started)
        self.reports[str(mission.mission_id)] = report
        status = {"PASS": "validated", "PARTIAL": "partial", "FAIL": "abandoned"}[report.verdict]
        self.state_graph.update(mission.mission_id, status=status, iterations=report.iterations)
        self.journal.append(
            mission.mission_id, "mission_completed", "mission_runtime",
            {"verdict": report.verdict, "state": status, "report": report.model_dump(mode="json")},
        )
        await self.bus.publish(
            Event(type="MissionCompleted", mission_id=mission.mission_id, payload={"verdict": report.verdict})
        )
        return str(mission.mission_id)

    def _failure(self, mission: Mission, started: float, summary: str, *, iterations: int = 0,
                 actions: list[dict[str, Any]] | None = None, validation: dict[str, Any] | None = None,
                 guard_events: list[dict[str, Any]] | None = None, cost: float = 0.0,
                 tokens: int = 0) -> Report:
        return Report(
            mission_id=mission.mission_id, verdict="FAIL", objective=mission.objective,
            summary=summary, iterations=iterations, actions=actions or [], validation=validation or {},
            guard_events=guard_events or [], cost_usd=round(cost, 10), tokens_used=tokens,
            duration_s=round(time.perf_counter() - started, 6),
        )

    async def _execute_mission(self, mission: Mission, started: float) -> Report:
        from nexus.providers import CompletionRequest
        from nexus.router import RoutingExhausted

        try:
            budget = self.guard.budget_limit(mission)
        except MissionGuardViolation as exc:
            return self._failure(
                mission, started, f"mission guard rejected constraints: {exc}",
                validation={"criteria": [{"name": "mission budget valid", "passed": False}]},
                guard_events=[{"type": "invalid_budget", "detail": str(exc)}],
            )
        try:
            limits = self.guard.execution_limits(mission)
            plan = self.compiler.compile(mission)
        except (MissionGuardViolation, MissionPlanError) as exc:
            return self._failure(
                mission, started, f"mission rejected: {exc}",
                validation={"criteria": [{"name": "mission plan and limits valid", "passed": False}]},
                guard_events=[{"type": "invalid_mission", "detail": str(exc)}],
            )

        compiled = [{"id": step.step_id, "kind": step.kind, "task": step.task,
                     "tool": step.tool, "fallback_to": step.fallback_to,
                     "depends_on": list(step.depends_on)} for step in plan]
        self.journal.append(mission.mission_id, "mission_compiled", "deterministic_compiler", {"steps": compiled})
        deadline = started + float(limits["deadline_seconds"])
        max_iterations = int(limits["max_iterations"])
        max_tokens = int(limits["max_tokens"])
        tool_timeout = float(limits["tool_timeout_seconds"])
        allowed_tools = set(mission.constraints.get("allowed_tools", []))
        permissions = set(mission.constraints.get("permissions", []))
        outputs: dict[str, str] = {}
        actions: list[dict[str, Any]] = []
        iterations = tokens_used = 0
        cost = 0.0
        before = len(self.router.decisions) if self.router is not None else 0
        routed_count = 0
        index = 0
        executed: set[str] = set()

        while index < len(plan):
            step = plan[index]
            if step.step_id in executed:
                return self._failure(mission, started, "planner refused to replay a completed step",
                                     iterations=iterations, actions=actions, cost=cost, tokens=tokens_used)
            missing_dependencies = set(step.depends_on) - executed
            if missing_dependencies:
                return self._failure(
                    mission, started,
                    f"planner replan reached {step.step_id!r} with incomplete dependencies: {sorted(missing_dependencies)}",
                    iterations=iterations, actions=actions, cost=cost, tokens=tokens_used,
                    guard_events=[{"type": "replan_dependency_missing", "step_id": step.step_id,
                                   "missing": sorted(missing_dependencies)}],
                )
            if time.perf_counter() >= deadline:
                actions.append({"step_id": step.step_id, "reason": "deadline exceeded"})
                return self._failure(mission, started, "mission deadline exceeded", iterations=iterations,
                                     actions=actions, cost=cost, tokens=tokens_used,
                                     guard_events=[{"type": "deadline_exceeded"}])
            if iterations >= max_iterations:
                return self._failure(mission, started, "mission iteration limit exceeded", iterations=iterations,
                                     actions=actions, cost=cost, tokens=tokens_used,
                                     guard_events=[{"type": "iteration_limit", "limit": max_iterations}])
            iterations += 1
            self.state_graph.update(mission.mission_id, iterations=iterations)
            self.journal.append(mission.mission_id, "mission_step_started", "mission_runtime",
                                {"step_id": step.step_id, "kind": step.kind, "tool": step.tool})
            try:
                if step.kind == "tool":
                    remaining = min(tool_timeout, deadline - time.perf_counter())
                    if remaining <= 0:
                        raise ToolExecutionError("mission deadline exceeded before tool execution")
                    value = await self.tool_registry.execute(
                        step.tool or "", step.arguments or {}, allowed_tools=allowed_tools,
                        granted_permissions=permissions, timeout_s=remaining,
                    )
                    text = value if isinstance(value, str) else json.dumps(value, sort_keys=True, default=str)
                    outputs[step.step_id] = text
                    actions.append({"step_id": step.step_id, "kind": "tool", "tool": step.tool,
                                    "status": "completed", "output": text, "cost_usd": 0.0,
                                    "granted_permissions": sorted(permissions)})
                else:
                    if self.router is None:
                        return Report(
                            mission_id=mission.mission_id, verdict="PARTIAL", objective=mission.objective,
                            summary="mission plan compiled but no execution provider is configured",
                            iterations=iterations, actions=actions, tokens_used=tokens_used,
                            duration_s=round(time.perf_counter() - started, 6),
                            validation={"criteria": [{"name": "execution provider configured", "passed": False}]},
                        )
                    if outputs:
                        prior = json.dumps(outputs, sort_keys=True)
                        prompt = f"Mission: {mission.objective}\nStep: {step.task}\nCompleted step outputs: {prior}"
                    else:
                        prompt = step.task
                    request = CompletionRequest(prompt=prompt, mission_id=str(mission.mission_id),
                                               critical=mission.priority == "urgent", max_cost_usd=budget)
                    remaining = deadline - time.perf_counter()
                    if remaining <= 0:
                        raise asyncio.TimeoutError
                    try:
                        result = await asyncio.wait_for(self.router.complete(request), timeout=remaining)
                    except (RoutingExhausted, asyncio.TimeoutError) as exc:
                        if isinstance(exc, asyncio.TimeoutError):
                            raise
                        trace = self.router.trace()[before:]
                        self.journal.append(mission.mission_id, "routing_exhausted", "router",
                                            {"detail": str(exc), "trace": trace})
                        actions.extend(trace)
                        return self._failure(mission, started, str(exc), iterations=iterations,
                                             actions=actions, cost=sum(a.get("cost_usd", 0.0) for a in actions),
                                             tokens=tokens_used,
                                             validation={"criteria": [{"name": "provider returned sufficient result", "passed": False}]})
                    tokens_used += result.input_tokens + result.output_tokens
                    trace = self.router.trace()[before:]
                    actions.extend({**item, "step_id": step.step_id, "kind": "generate"}
                                   for item in trace[routed_count:])
                    routed_count = len(trace)
                    cost = round(sum(item.get("cost_usd", 0.0) for item in trace), 10)
                    outputs[step.step_id] = result.text
                    if tokens_used > max_tokens:
                        return self._failure(mission, started, "mission token limit exceeded after provider response",
                                             iterations=iterations, actions=actions, cost=cost, tokens=tokens_used,
                                             guard_events=[{"type": "token_limit", "limit": max_tokens,
                                                            "actual": tokens_used}])
                    if time.perf_counter() > deadline:
                        return self._failure(mission, started, "mission deadline exceeded during provider call",
                                             iterations=iterations, actions=actions, cost=cost, tokens=tokens_used,
                                             guard_events=[{"type": "deadline_exceeded"}])
                executed.add(step.step_id)
                self.journal.append(mission.mission_id, "mission_step_completed", "mission_runtime",
                                    {"step_id": step.step_id,
                                     "output_digest": hashlib.sha256(outputs[step.step_id].encode()).hexdigest()})
                index += 1
            except ToolExecutionError as exc:
                actions.append({"step_id": step.step_id, "kind": "tool", "tool": step.tool,
                                "status": "error", "error": str(exc), "cost_usd": 0.0})
                if step.fallback_to is None:
                    return self._failure(mission, started, str(exc), iterations=iterations, actions=actions,
                                         cost=cost, tokens=tokens_used,
                                         validation={"criteria": [{"name": "tool step completed", "passed": False}]})
                target_index = next(i for i, candidate in enumerate(plan) if candidate.step_id == step.fallback_to)
                self.journal.append(mission.mission_id, "mission_replanned", "deterministic_planner",
                                    {"failed_step": step.step_id, "fallback_step": step.fallback_to,
                                     "failed_step_replayed": False, "detail": str(exc)})
                actions.append({"step_id": step.step_id, "status": "replanned", "fallback_to": step.fallback_to})
                index = target_index
            except ToolAuthorizationError as exc:
                return self._failure(mission, started, f"tool authorization denied: {exc}",
                                     iterations=iterations, actions=actions, cost=cost, tokens=tokens_used,
                                     validation={"criteria": [{"name": "tool authorization", "passed": False}]})
            except asyncio.TimeoutError:
                actions.append({"step_id": step.step_id, "reason": "deadline exceeded"})
                return self._failure(mission, started, "mission deadline exceeded", iterations=iterations,
                                     actions=actions, cost=cost, tokens=tokens_used,
                                     guard_events=[{"type": "deadline_exceeded"}])

        trace = self.router.trace()[before:] if self.router is not None else []
        if trace:
            self.journal.append(mission.mission_id, "routing_decided", "router", {"trace": trace})
        combined = "\n".join(outputs[key] for key in outputs)
        verification = self.verifier.verify(mission, combined)
        self.journal.append(mission.mission_id, "mission_verification", "verification_engine",
                            {"verdict": verification.verdict, "criteria": verification.criteria,
                             "evidence": verification.evidence})
        return Report(
            mission_id=mission.mission_id, verdict=verification.verdict, objective=mission.objective,
            summary=f"{len(plan)} compiled step(s) executed; deterministic verification: {verification.verdict}",
            iterations=iterations, output=combined, cost_usd=cost,
            duration_s=round(time.perf_counter() - started, 6), actions=actions,
            tokens_used=tokens_used,
            validation={"compiled_steps": compiled, "criteria": verification.criteria,
                        "verification": verification.evidence, "confidence_is_not_proof": True},
        )

    def report(self, mission_id: str) -> Report | None:
        return self.reports.get(mission_id)
