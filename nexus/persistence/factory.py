from __future__ import annotations
import os
from nexus.core import NexusRuntime
from .postgres import PostgresSnapshotStore
from .runtime import PersistentRuntime
DATABASE_URL_ENV = "NEXUS_DATABASE_URL"
def build_runtime(router: object | None = None) -> NexusRuntime:
    dsn = os.environ.get(DATABASE_URL_ENV)
    if not dsn:
        return NexusRuntime(router=router)
    return PersistentRuntime(PostgresSnapshotStore(dsn), router=router)
