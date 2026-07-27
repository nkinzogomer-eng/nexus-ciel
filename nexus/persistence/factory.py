from __future__ import annotations
import os
from nexus.core import NexusRuntime
from .postgres import PostgresSnapshotStore
from .runtime import FileSnapshotStore, PersistentRuntime
DATABASE_URL_ENV = "NEXUS_DATABASE_URL"
SNAPSHOT_PATH_ENV = "NEXUS_RUNTIME_SNAPSHOT"
def build_runtime(router: object | None = None) -> NexusRuntime:
    snapshot_path = os.environ.get(SNAPSHOT_PATH_ENV)
    if snapshot_path:
        return PersistentRuntime(FileSnapshotStore(snapshot_path), router=router)
    database_url = os.environ.get(DATABASE_URL_ENV)
    if database_url:
        return PersistentRuntime(PostgresSnapshotStore(database_url), router=router)
    return NexusRuntime(router=router)
