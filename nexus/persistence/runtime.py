from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Iterable

from nexus.bus import AsyncEventBus
from nexus.core import NexusRuntime
from nexus.schemas import Event, Mission, Report

from .sqlite_store import SqliteRuntimeStore


class CheckpointingRuntime(NexusRuntime):
    def __init__(self, router: object | None = None, store: SqliteRuntimeStore | None = None) -> None:
        super().__init__(router=router)
        self.store = store
        self._missions: dict[str, Mission] = {}

    @classmethod
    def load(cls, store: SqliteRuntimeStore, router: object | None = None) -> "CheckpointingRuntime":
        runtime = cls(router=router, store=store)
        store.hydrate_runtime(runtime)
        runtime.bus = AsyncEventBus()
        return runtime

    def _mark_checkpointed(self, mission_ids: Iterable[str] | None = None) -> None:
        stamp = datetime.now(timezone.utc)
        targets = set(mission_ids or [str(mission_id) for mission_id in self.state_graph._states])
        for mission_id, state in list(self.state_graph._states.items()):
            if str(mission_id) not in targets:
                continue
            if state.checkpointed_at is None:
                self.state_graph._states[mission_id] = state.model_copy(update={"checkpointed_at": stamp})

    def checkpoint(self, mission_ids: Iterable[str] | None = None) -> None:
        if self.store is None:
            return
        self._mark_checkpointed(mission_ids)
        self.store.checkpoint_runtime(self)

    async def accept(self, mission: Mission) -> str:
        started = time.perf_counter()
        self._missions[str(mission.mission_id)] = mission
        self.state_graph.create(mission)
        self.journal.append(mission.mission_id, "mission_accepted", "manas", mission.model_dump(mode="json"))
        await self.bus.publish(
            Event(type="MissionAccepted", mission_id=mission.mission_id, payload={"objective": mission.objective})
        )
        self.state_graph.update(mission.mission_id, status="in_progress", iterations=1)
        self.checkpoint([str(mission.mission_id)])

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

        await self._finalise_report(mission, report)
        return str(mission.mission_id)

    async def _finalise_report(self, mission: Mission, report: Report) -> None:
        self.reports[str(mission.mission_id)] = report
        self.state_graph.update(
            mission.mission_id,
            status="validated" if report.verdict == "PASS" else "abandoned",
        )
        self.journal.append(mission.mission_id, "mission_validated", "validation_engine", report.model_dump(mode="json"))
        await self.bus.publish(
            Event(type="MissionValidated", mission_id=mission.mission_id, payload={"verdict": report.verdict})
        )
        self.checkpoint([str(mission.mission_id)])

    async def resume_pending(self) -> list[str]:
        if self.store is None:
            return []
        resumed: list[str] = []
        for pending in self.store.pending_missions():
            mission = pending.mission
            if str(mission.mission_id) in self.reports:
                continue
            started = time.perf_counter()
            if self.router is None:
                report = Report(
                    mission_id=mission.mission_id,
                    verdict="PASS",
                    objective=mission.objective,
                    summary="Phase 0 trivial execution completed",
                    iterations=max(pending.state.iterations, 1),
                    validation={"criteria": [{"name": "objective accepted", "passed": True}]},
                    duration_s=round(time.perf_counter() - started, 6),
                )
            else:
                report = await self._execute_routed(mission, started)
            await self._finalise_report(mission, report)
            resumed.append(str(mission.mission_id))
        return resumed
