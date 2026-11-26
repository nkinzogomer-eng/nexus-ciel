from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


ApprovalStatus = Literal["pending", "approved", "rejected", "expired"]


class ApprovalRequest(BaseModel):
    approval_id: UUID = Field(default_factory=uuid4)
    identity_hash: str = Field(min_length=64, max_length=64)
    action_id: UUID
    tool_name: str = Field(min_length=1)
    context: dict[str, Any] = Field(default_factory=dict)
    status: ApprovalStatus = "pending"
    requested_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime
    approved_at: datetime | None = None
    approver: str | None = None
    decision_reason: str | None = None


class ApprovalLedger:
    """Small durable approval ledger; it never grants approval implicitly."""

    def __init__(self, requests: list[ApprovalRequest] | None = None) -> None:
        self._requests = {item.identity_hash: item for item in requests or []}

    def ensure_pending(
        self,
        *,
        identity_hash: str,
        action_id: UUID,
        tool_name: str,
        context: dict[str, Any],
        ttl_s: float = 3600.0,
    ) -> ApprovalRequest:
        current = self._requests.get(identity_hash)
        if current is not None:
            self._expire_if_needed(current)
            return current
        item = ApprovalRequest(
            identity_hash=identity_hash,
            action_id=action_id,
            tool_name=tool_name,
            context=dict(context),
            expires_at=datetime.now(timezone.utc) + timedelta(seconds=ttl_s),
        )
        self._requests[identity_hash] = item
        return item

    def approve(self, identity_hash: str, *, approver: str, reason: str = "") -> ApprovalRequest:
        if not approver.strip():
            raise ValueError("approver must not be blank")
        item = self._get(identity_hash)
        self._expire_if_needed(item)
        if item.status != "pending":
            raise ValueError(f"approval is not pending: {item.status}")
        updated = item.model_copy(update={
            "status": "approved",
            "approved_at": datetime.now(timezone.utc),
            "approver": approver,
            "decision_reason": reason or None,
        })
        self._requests[identity_hash] = updated
        return updated

    def reject(self, identity_hash: str, *, approver: str, reason: str) -> ApprovalRequest:
        if not approver.strip() or not reason.strip():
            raise ValueError("approver and rejection reason are required")
        item = self._get(identity_hash)
        self._expire_if_needed(item)
        if item.status != "pending":
            raise ValueError(f"approval is not pending: {item.status}")
        updated = item.model_copy(update={
            "status": "rejected",
            "approved_at": None,
            "approver": approver,
            "decision_reason": reason,
        })
        self._requests[identity_hash] = updated
        return updated

    def is_approved(self, identity_hash: str) -> bool:
        item = self._requests.get(identity_hash)
        if item is None:
            return False
        self._expire_if_needed(item)
        return item.status == "approved"

    def get(self, identity_hash: str) -> ApprovalRequest | None:
        item = self._requests.get(identity_hash)
        if item is not None:
            self._expire_if_needed(item)
        return item

    def list(self) -> list[ApprovalRequest]:
        for item in list(self._requests.values()):
            self._expire_if_needed(item)
        return list(self._requests.values())

    def snapshot(self) -> list[dict[str, Any]]:
        return [item.model_dump(mode="json") for item in self.list()]

    @classmethod
    def from_snapshot(cls, items: list[dict[str, Any]]) -> "ApprovalLedger":
        return cls([ApprovalRequest.model_validate(item) for item in items])

    def _get(self, identity_hash: str) -> ApprovalRequest:
        item = self._requests.get(identity_hash)
        if item is None:
            raise ValueError("approval request does not exist")
        return item

    def _expire_if_needed(self, item: ApprovalRequest) -> None:
        if item.status == "pending" and item.expires_at <= datetime.now(timezone.utc):
            self._requests[item.identity_hash] = item.model_copy(update={"status": "expired"})
