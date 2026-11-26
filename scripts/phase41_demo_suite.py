from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Lock
from uuid import NAMESPACE_URL, uuid4, uuid5

from nexus.actions import ActionExecutor, ActionRecord, ActionRejected, ActionRequest, ToolRegistry, ToolSpec
from nexus.core.mission_journal import MissionJournal
from nexus.persistence import FileSnapshotStore, PersistentRuntime

ROOT = Path(__file__).parents[1]
OUT = ROOT / "reports" / "phase4-1-demos"


def request(tool="counted", key=None, **params):
    key = key or f"demo-{uuid4()}"
    return ActionRequest(
        action_id=uuid5(NAMESPACE_URL, f"ciel-demo:{key}:action"),
        mission_id=uuid5(NAMESPACE_URL, f"ciel-demo:{key}:mission"),
        plan_id=uuid5(NAMESPACE_URL, f"ciel-demo:{key}:plan"),
        step_id=uuid5(NAMESPACE_URL, f"ciel-demo:{key}:step"), tool_name=tool,
        parameters=params, idempotency_key=key, budget_usd=1.0,
    )


def registry(calls, *, explode=False):
    reg = ToolRegistry()
    if explode:
        def handler(params):
            calls.append("called")
            raise KeyError("unexpected demo exception")
    else:
        def handler(params):
            calls.append(dict(params))
            return {"ok": True, **params}
    reg.register(ToolSpec(name="counted", description="demo", permissions=["demo"], idempotency_rule="once"), handler)
    return reg


def write_report(name, data):
    OUT.mkdir(parents=True, exist_ok=True)
    data["environment"] = {"python": sys.version.split()[0], "branch": "hardening/ciel-phase4-1-reliability-recovery"}
    data["limitations"] = ["single-writer PostgreSQL", "no process sandbox", "handler timeout is observed after return and is not interruptible"]
    (OUT / f"{name}.json").write_text(json.dumps(data, indent=2, sort_keys=True, default=str) + "\n")
    lines = [f"# {data['title']}", "", f"**Objectif :** {data['objective']}", "", "## Environnement et état initial", json.dumps(data["environment"], indent=2), "", "## Étapes et événements", ""]
    for step in data.get("steps", []): lines.append(f"1. {step}")
    lines += ["", "## Résultats", "", "```json", json.dumps(data, indent=2, sort_keys=True, default=str), "```", "", "## Limites", "", *[f"- {item}" for item in data["limitations"]]]
    (OUT / f"{name}.md").write_text("\n".join(lines) + "\n")


def nominal():
    calls, journal = [], MissionJournal(); ex = ActionExecutor(registry(calls), journal=journal)
    reqs = [request(value=2, key="nominal-1"), request(value=3, key="nominal-2")]
    results = [ex.execute(req, granted_permissions={"demo"}) for req in reqs]
    write_report("01-nominal-multiple-actions", {"title": "Démonstration 1 — mission nominale", "objective": "Exécuter plusieurs actions allowlistées et journalisées.", "steps": ["Créer deux demandes distinctes", "Exécuter avec la permission demo", "Vérifier les deux résultats et la chaîne"], "actions": [r.model_dump(mode="json") for r in results], "handler_calls": len(calls), "journal_events": [e.type for e in journal.entries()], "checks": {"both_succeeded": all(r.status == "succeeded" for r in results), "journal_valid": journal.verify_chain()}})


def restore_no_replay():
    calls=[]; reg=registry(calls); req=request(value=7, key="restore-no-replay")
    rec=ActionRecord(request=req, status="running")
    journal=MissionJournal(); ex=ActionExecutor.from_snapshot([rec.model_dump(mode="json")], reg, journal=journal)
    result=ex.execute(req, granted_permissions={"demo"})
    write_report("03-restore-without-replay", {"title": "Démonstration 3 — restauration sans rejeu", "objective": "Restaurer un running et prouver le blocage sans appel handler.", "steps": ["Restaurer un record running", "Demander la même action", "Contrôler interrupted_uncertain et le journal"], "actions": [result.model_dump(mode="json")], "handler_calls": len(calls), "journal_events": [e.type for e in journal.entries()], "checks": {"blocked": result.status == "interrupted_uncertain", "no_replay": len(calls) == 0, "journal_valid": journal.verify_chain()}})


def collision():
    calls=[]; ex=ActionExecutor(registry(calls)); req=request(value=1, key="collision")
    first=ex.execute(req, granted_permissions={"demo"}); error=None
    try: ex.execute(req.model_copy(update={"budget_usd": 0.5}), granted_permissions={"demo"})
    except ActionRejected as exc: error=str(exc)
    write_report("04-idempotency-collision", {"title": "Démonstration 4 — collision d’idempotence", "objective": "Refuser une même clé liée à un budget différent.", "steps": ["Exécuter la requête originale", "Soumettre la même clé avec un budget différent", "Vérifier le refus et l’unicité d’exécution"], "actions": [first.model_dump(mode="json")], "handler_calls": len(calls), "journal_events": [], "checks": {"collision_rejected": error is not None, "error": error, "one_handler_call": len(calls) == 1}})


def unexpected():
    calls=[]; ex=ActionExecutor(registry(calls, explode=True)); req=request(value=1, key="unexpected")
    result=ex.execute(req, granted_permissions={"demo"}); replay=ex.execute(req, granted_permissions={"demo"})
    write_report("05-unexpected-exception", {"title": "Démonstration 5 — exception inattendue", "objective": "Classer une exception inconnue après démarrage comme résultat incertain terminal.", "steps": ["Lancer un handler qui lève KeyError", "Contrôler interrupted_uncertain", "Rejouer et vérifier zéro nouvel appel"], "actions": [result.model_dump(mode="json"), replay.model_dump(mode="json")], "handler_calls": len(calls), "journal_events": [], "checks": {"uncertain": result.status == "interrupted_uncertain", "no_replay": len(calls) == 1}})


def concurrent():
    calls=[]; shared_registry=registry(calls); executors=(ActionExecutor(shared_registry), ActionExecutor(shared_registry)); req=request(value=8, key="concurrent")
    with ThreadPoolExecutor(max_workers=2) as pool: results=list(pool.map(lambda ex: ex.execute(req, granted_permissions={"demo"}), executors))
    write_report("06-concurrent-same-key", {"title": "Démonstration 6 — concurrence même clé", "objective": "Prouver l’exclusion et l’idempotence entre deux instances d’ActionExecutor dans un même processus.", "steps": ["Créer deux exécuteurs distincts sur le même registre contrôlé", "Soumettre la même demande depuis deux threads", "Compter les appels handler", "Vérifier un résultat original et un replay"], "actions": [r.model_dump(mode="json") for r in results], "handler_calls": len(calls), "journal_events": [], "checks": {"one_handler_call": len(calls) == 1, "one_replay": sum(r.idempotent_replay for r in results) == 1}})


def crash_real():
    with tempfile.TemporaryDirectory() as temp:
        root=Path(temp); snapshot=root/"runtime.json"; marker=root/"calls"; reqfile=root/"request.json"
        code="""import os,signal,sys\nfrom nexus.actions import ActionRequest\nfrom nexus.persistence import FileSnapshotStore,PersistentRuntime\nfrom uuid import NAMESPACE_URL,uuid5\nkey='crash-demo'\nq=ActionRequest(action_id=uuid5(NAMESPACE_URL,'ciel-demo:'+key+':action'),mission_id=uuid5(NAMESPACE_URL,'ciel-demo:'+key+':mission'),plan_id=uuid5(NAMESPACE_URL,'ciel-demo:'+key+':plan'),step_id=uuid5(NAMESPACE_URL,'ciel-demo:'+key+':step'),tool_name='calculate',parameters={'operation':'add','values':[1,2]},idempotency_key=key,budget_usd=1)\nr=PersistentRuntime(FileSnapshotStore(sys.argv[1]))\nopen(sys.argv[3],'w').write(q.model_dump_json())\ndef h(p):\n open(sys.argv[2],'a').write('call\\n'); os.kill(os.getpid(),signal.SIGKILL)\nr.action_executor.registry._handlers['calculate']=h\nr.action_executor.execute(q,granted_permissions={'compute'})\n"""
        child=subprocess.Popen([sys.executable,"-c",code,str(snapshot),str(marker),str(reqfile)],cwd=ROOT,env={**os.environ,"PYTHONPATH":str(ROOT)})
        exit_code=child.wait(timeout=10); restarted=PersistentRuntime(FileSnapshotStore(snapshot)); q=ActionRequest.model_validate_json(reqfile.read_text()); restored=restarted.action_executor.get(q.action_id); replay=restarted.action_executor.execute(q,granted_permissions={"compute"})
        write_report("02-crash-mid-action", {"title":"Démonstration 2 — interruption brutale", "objective":"Tuer le processus au milieu du handler et restaurer sans rejeu.", "steps":["Démarrer un processus enfant", "SIGKILL après le premier appel handler", "Restaurer le snapshot et bloquer le replay"], "actions":[replay.model_dump(mode="json")], "handler_calls":len(marker.read_text().splitlines()), "journal_events":[e.type for e in restarted.journal.entries(q.mission_id)], "checks":{"sigkill":exit_code == -signal.SIGKILL,"restored_status":restored.status if restored else None,"no_second_call":len(marker.read_text().splitlines()) == 1,"journal_valid":restarted.journal.verify_chain()}})


if __name__ == "__main__":
    nominal(); crash_real(); restore_no_replay(); collision(); unexpected(); concurrent()
    print(f"wrote {len(list(OUT.glob('*.json')))} JSON and {len(list(OUT.glob('*.md')))} Markdown reports to {OUT}")
