from __future__ import annotations
import hashlib
import json
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

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

class MissionJournal:
    def __init__(self) -> None:
        self._entries: list[JournalEntry] = []

    def append(self, mission_id: UUID, event_type: str, actor: str, payload: dict[str, Any] | None = None) -> JournalEntry:
        payload = payload or {}
        previous = self._entries[-1].signature if self._entries else "GENESIS"
        body = json.dumps({"seq": len(self._entries) + 1, "mission_id": str(mission_id), "type": event_type, "actor": actor, "payload": payload, "precedent_hash": previous}, sort_keys=True)
        signature = hashlib.sha256(body.encode()).hexdigest()
        entry = JournalEntry(len(self._entries) + 1, mission_id, event_type, actor, payload, signature, previous)
        self._entries.append(entry)
        return entry

    def entries(self, mission_id: UUID | None = None) -> list[JournalEntry]:
        return [e for e in self._entries if mission_id is None or e.mission_id == mission_id]

    def verify_chain(self) -> bool:
        previous = "GENESIS"
        for entry in self._entries:
            if entry.precedent_hash != previous:
                return False
            previous = entry.signature
        return True
