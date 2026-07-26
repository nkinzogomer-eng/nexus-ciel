from __future__ import annotations
import hashlib
import json
from datetime import datetime, timezone
from typing import Any
from uuid import UUID


def _signature(
    seq: int,
    mission_id: UUID,
    event_type: str,
    actor: str,
    payload: dict[str, Any],
    previous_hash: str,
) -> str:
    """Deterministic signature over an entry's full content.

    Everything that gives the entry its meaning goes into the hash. Without
    that, the chain proves ordering only, never integrity.
    """
    body = json.dumps(
        {
            "seq": seq,
            "mission_id": str(mission_id),
            "type": event_type,
            "actor": actor,
            "payload": payload,
            "precedent_hash": previous_hash,
        },
        sort_keys=True,
        default=str,
    )
    return hashlib.sha256(body.encode()).hexdigest()


class JournalEntry:
    def __init__(self, seq: int, mission_id: UUID, event_type: str, actor: str, payload: dict[str, Any], signature: str, previous_hash: str):
        self.seq, self.mission_id, self.type, self.actor = seq, mission_id, event_type, actor
        self.payload, self.signature, self.precedent_hash = payload, signature, previous_hash
        self.timestamp = datetime.now(timezone.utc).isoformat()

    def as_dict(self) -> dict[str, Any]:
        """JSON-serialisable snapshot of the entry (UUID rendered as text)."""
        data = self.__dict__.copy()
        data["mission_id"] = str(self.mission_id)
        return data

    def recomputed_signature(self) -> str:
        """Signature the entry's current content would produce today."""
        return _signature(
            self.seq, self.mission_id, self.type, self.actor, self.payload, self.precedent_hash
        )


class MissionJournal:
    def __init__(self) -> None:
        self._entries: list[JournalEntry] = []

    def append(self, mission_id: UUID, event_type: str, actor: str, payload: dict[str, Any] | None = None) -> JournalEntry:
        payload = payload or {}
        previous = self._entries[-1].signature if self._entries else "GENESIS"
        seq = len(self._entries) + 1
        signature = _signature(seq, mission_id, event_type, actor, payload, previous)
        entry = JournalEntry(seq, mission_id, event_type, actor, payload, signature, previous)
        self._entries.append(entry)
        return entry

    def entries(self, mission_id: UUID | None = None) -> list[JournalEntry]:
        return [e for e in self._entries if mission_id is None or e.mission_id == mission_id]

    def verify_chain(self) -> bool:
        """True only if every entry is correctly linked *and* unmodified.

        Checking links alone made the journal tamper-tolerant: rewriting a
        payload in place left every precedent_hash intact and went unnoticed.
        """
        previous = "GENESIS"
        for position, entry in enumerate(self._entries, start=1):
            if entry.seq != position:
                return False
            if entry.precedent_hash != previous:
                return False
            if entry.signature != entry.recomputed_signature():
                return False
            previous = entry.signature
        return True

    def tampered_entries(self) -> list[int]:
        """Sequence numbers whose content no longer matches their signature."""
        return [e.seq for e in self._entries if e.signature != e.recomputed_signature()]
