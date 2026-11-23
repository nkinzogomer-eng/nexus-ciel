#!/usr/bin/env bash
set -euo pipefail

# End-to-end proof that a mission snapshot survives a full Compose stack stop/start.
# "docker compose down" intentionally omits --volumes; the named PostgreSQL volume
# must remain intact until the second API process has recovered the mission.
export POSTGRES_PORT="${POSTGRES_PORT:-55432}"
PROJECT="nexus-ciel-compose-persistence-gate"

compose() {
  docker compose --project-name "$PROJECT" -f docker-compose.yml "$@"
}

cleanup() {
  compose down --volumes --remove-orphans >/dev/null 2>&1 || true
}
trap cleanup EXIT

compose down --remove-orphans >/dev/null 2>&1 || true
compose up -d --build

python - <<'PY'
import json
import time
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:8000"

def request(path, method="GET", payload=None):
    data = None if payload is None else json.dumps(payload).encode()
    req = urllib.request.Request(
        BASE + path,
        data=data,
        headers={"Content-Type": "application/json"} if data is not None else {},
        method=method,
    )
    with urllib.request.urlopen(req, timeout=10) as response:
        return json.load(response)

def wait_for_api():
    last_error = None
    for _ in range(60):
        try:
            health = request("/health")
            if health.get("status") == "ok":
                return health
        except Exception as exc:
            last_error = exc
        time.sleep(2)
    raise RuntimeError(f"API did not become healthy: {last_error}")

wait_for_api()
accepted = request("/mission", method="POST", payload={
    "objective": "CI Compose persistence proof"
})
mission_id = accepted["mission_id"]

state = None
report = None
for _ in range(30):
    state = request(f"/mission/{mission_id}")
    try:
        report = request(f"/mission/{mission_id}/report")
    except urllib.error.HTTPError as exc:
        if exc.code != 404:
            raise
    if report is not None and state.get("status") in {"validated", "partial", "abandoned"}:
        break
    time.sleep(1)

if report is None:
    raise RuntimeError("mission report was not persisted before Compose shutdown")

with open("/tmp/nexus-ciel-compose-before.json", "w", encoding="utf-8") as stream:
    json.dump({"mission_id": mission_id, "state": state, "report": report}, stream)
print(f"Persisted mission {mission_id}: {state['status']} / {report['verdict']}")
PY

# Stop both services but preserve the named PostgreSQL volume.
compose down
compose up -d --build

python - <<'PY'
import json
import time
import urllib.request

BASE = "http://127.0.0.1:8000"

def get(path):
    with urllib.request.urlopen(BASE + path, timeout=10) as response:
        return json.load(response)

last_error = None
for _ in range(60):
    try:
        health = get("/health")
        if health.get("status") == "ok":
            break
    except Exception as exc:
        last_error = exc
    time.sleep(2)
else:
    raise RuntimeError(f"API did not recover after Compose restart: {last_error}")

with open("/tmp/nexus-ciel-compose-before.json", encoding="utf-8") as stream:
    before = json.load(stream)

mission_id = before["mission_id"]
after_state = get(f"/mission/{mission_id}")
after_report = get(f"/mission/{mission_id}/report")

assert after_state == before["state"], (
    f"mission state changed across Compose restart: {before['state']} != {after_state}"
)
assert after_report == before["report"], (
    "mission report changed or disappeared across Compose restart"
)
assert health.get("journal_chain_valid") is True, "Mission Journal chain is invalid after restart"

print(
    "PASS: Compose stop/start preserved mission state and report; "
    "Mission Journal chain remains valid."
)
PY
