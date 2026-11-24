from __future__ import annotations

import math

from nexus.schemas import Mission


class MissionGuardViolation(ValueError):
    """A mission's declared resource constraints are invalid."""


class MissionGuard:
    """Validate hard resource limits before any provider is invoked."""

    def budget_limit(self, mission: Mission) -> float | None:
        raw = mission.constraints.get("budget_usd")
        if raw is None:
            return None
        if isinstance(raw, bool) or not isinstance(raw, (int, float)):
            raise MissionGuardViolation("budget_usd must be a finite non-negative number")
        value = float(raw)
        if not math.isfinite(value) or value < 0:
            raise MissionGuardViolation("budget_usd must be a finite non-negative number")
        return value
