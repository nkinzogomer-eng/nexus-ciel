from __future__ import annotations
from nexus.bus import AsyncEventBus
from nexus.schemas import Event, Mission, Report
from .capability_registry import CapabilityRegistry
from .mission_journal import MissionJournal
from .state_graph import StateGraph

class NexusRuntime:
    def __init__(self) -> None:
        self.bus = AsyncEventBus()
        self.state_graph = StateGraph()
        self.journal = MissionJournal()
        self.registry = CapabilityRegistry()
        self.reports: dict[str, Report] = {}

    async def accept(self, mission: Mission) -> str:
        state = self.state_graph.create(mission)
        self.journal.append(mission.mission_id, "mission_accepted", "manas", mission.model_dump(mode="json"))
        await self.bus.publish(Event(type="MissionAccepted", mission_id=mission.mission_id, payload={"objective": mission.objective}))
        self.state_graph.update(mission.mission_id, status="in_progress", iterations=1)
        report = Report(mission_id=mission.mission_id, verdict="PASS", objective=mission.objective, summary="Phase 0 trivial execution completed", iterations=1, validation={"criteria": [{"name": "objective accepted", "passed": True}]})
        self.reports[str(mission.mission_id)] = report
        self.state_graph.update(mission.mission_id, status="validated")
        self.journal.append(mission.mission_id, "mission_validated", "validation_engine", report.model_dump(mode="json"))
        await self.bus.publish(Event(type="MissionValidated", mission_id=mission.mission_id, payload={"verdict": report.verdict}))
        return str(mission.mission_id)

    def report(self, mission_id: str) -> Report | None:
        return self.reports.get(mission_id)
