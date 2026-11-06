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

    def execution_limits(self, mission: Mission) -> dict[str, float | int]:
        """Return strict per-mission bounds; reject malformed overrides."""
        limits: dict[str, float | int] = {
            "deadline_seconds": 60.0,
            "max_iterations": 8,
            "max_tokens": 8192,
            "tool_timeout_seconds": 5.0,
        }
        absolute_maxima = {
            "deadline_seconds": 300.0,
            "max_iterations": 32,
            "max_tokens": 32768,
            "tool_timeout_seconds": 30.0,
        }
        for key in limits:
            if key not in mission.constraints:
                continue
            raw = mission.constraints[key]
            if isinstance(raw, bool) or not isinstance(raw, (int, float)):
                raise MissionGuardViolation(f"{key} must be a positive finite number")
            value = float(raw)
            if not math.isfinite(value) or value <= 0:
                raise MissionGuardViolation(f"{key} must be a positive finite number")
            if value > absolute_maxima[key]:
                raise MissionGuardViolation(f"{key} exceeds the system maximum of {absolute_maxima[key]}")
            if key in {"max_iterations", "max_tokens"} and not value.is_integer():
                raise MissionGuardViolation(f"{key} must be a positive integer")
            limits[key] = int(value) if key in {"max_iterations", "max_tokens"} else value
        return limits
