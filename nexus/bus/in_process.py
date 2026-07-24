from __future__ import annotations
from collections import defaultdict
from typing import Awaitable, Callable
from nexus.schemas import Event

Handler = Callable[[Event], Awaitable[None]]

class AsyncEventBus:
    def __init__(self) -> None:
        self._subscribers: dict[str, list[Handler]] = defaultdict(list)
        self.events: list[Event] = []

    async def publish(self, event: Event) -> None:
        self.events.append(event)
        for handler in tuple(self._subscribers.get(event.type, [])):
            await handler(event)

    async def subscribe(self, event_type: str, handler: Handler) -> None:
        self._subscribers[event_type].append(handler)
