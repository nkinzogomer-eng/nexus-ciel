from __future__ import annotations

import time

from nexus.bus import AsyncEventBus
from nexus.schemas import Event, Mission, Report

from .capability_registry import CapabilityRegistry
from .mission_journal import MissionJournal
from .state_graph import StateGraph


class NexusRuntime:
    """Minimal mission runtime.

    Without a router it keeps the Phase 0 trivial behaviour. With a router it
    actually executes the objective through the economic cascade and reports
    the real cost and escalation trace.
    """

    def __init__(self, router: object | None = None) -> None:
        self.bus = AsyncEventBus()
        self.state_graph = StateGraph()
        self.journal = MissionJournal()
        self.registry = CapabilityRegistry()
        self.reports: dict[str, Report] = {}
        self.router = router

    async def accept(self, mission: Mission) -> str:
        started = time.perf_counter()
        self.state_graph.create(mission)
        self.journal.append(mission.mission_id, "mission_accepted", "manas", mission.model_dump(mode="json"))
        await self.bus.publish(
            Event(type="MissionAccepted", mission_id=mission.mission_id, payload={"objective": mission.objective})
        )
        self.state_graph.update(mission.mission_id, status="in_progress", iterations=1)

        if self.router is None:
            report = Report(
                mission_id=mission.mission_id,
                verdict="PASS",
                objective=mission.objective,
                summary="Phase 0 trivial execution completed",
                iterations=1,
                validation={"criteria": [{"name": "objective accepted", "passed": True}]},
                duration_s=round(time.perf_counter() - started, 6),
            )
        else:
            report = await self._execute_routed(mission, started)

        self.reports[str(mission.mission_id)] = report
        self.state_graph.update(
            mission.mission_id,
            status="validated" if report.verdict == "PASS" else "abandoned",
        )
        self.journal.append(mission.mission_id, "mission_validated", "validation_engine", report.model_dump(mode="json"))
        await self.bus.publish(
            Event(type="MissionValidated", mission_id=mission.mission_id, payload={"verdict": report.verdict})
        )
        return str(mission.mission_id)

    async def _execute_routed(self, mission: Mission, started: float) -> Report:
        from nexus.providers import CompletionRequest
        from nexus.router import RoutingExhausted

        request = CompletionRequest(
            prompt=mission.objective,
            mission_id=str(mission.mission_id),
            critical=mission.priority == "urgent",
        )
        before = len(self.router.decisions)
        try:
            result = await self.router.complete(request)
        except RoutingExhausted as exc:
            trace = self.router.trace()[before:]
            self.journal.append(
                mission.mission_id, "routing_exhausted", "router", {"detail": str(exc), "trace": trace}
            )
            return Report(
                mission_id=mission.mission_id,
                verdict="FAIL",
                objective=mission.objective,
                summary=str(exc),
                iterations=max(len(trace), 1),
                cost_usd=round(sum(step["cost_usd"] for step in trace), 10),
                duration_s=round(time.perf_counter() - started, 6),
                actions=trace,
                validation={"criteria": [{"name": "confidence threshold reached", "passed": False}]},
            )

        trace = self.router.trace()[before:]
        chosen = trace[-1] if trace else {"stage": "unknown", "provider": "unknown"}
        self.journal.append(
            mission.mission_id,
            "routing_decided",
            "router",
            {"stage": chosen["stage"], "provider": chosen["provider"], "trace": trace},
        )
        return Report(
            mission_id=mission.mission_id,
            verdict="PASS",
            objective=mission.objective,
            summary=f"served by {chosen['provider']} at stage {chosen['stage']}",
            iterations=max(len(trace), 1),
            cost_usd=round(sum(step["cost_usd"] for step in trace), 10),
            duration_s=round(time.perf_counter() - started, 6),
            actions=trace,
            validation={
                "criteria": [
                    {"name": "objective accepted", "passed": True},
                    {"name": "confidence threshold reached", "passed": True},
                ],
                "confidence": result.confidence,
            },
        )

    def report(self, mission_id: str) -> Report | None:
        return self.reports.get(mission_id)
