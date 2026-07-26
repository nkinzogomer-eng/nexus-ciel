from fastapi import FastAPI, HTTPException, status
from nexus.persistence import build_runtime
from nexus.providers import LocalProvider, SecondaryProvider
from nexus.router import AdaptiveRouter
from nexus.schemas import Mission
app = FastAPI(title="Nexus Ciel", version="0.1.0")
router = AdaptiveRouter([LocalProvider(), SecondaryProvider()])
runtime = build_runtime(router=router)
@app.post("/mission", status_code=status.HTTP_202_ACCEPTED)
async def create_mission(mission: Mission) -> dict[str, str]:
    return {"mission_id": await runtime.accept(mission)}
@app.get("/mission/{mission_id}")
async def get_mission(mission_id: str):
    from uuid import UUID
    try: state = runtime.state_graph.get(UUID(mission_id))
    except ValueError: raise HTTPException(status_code=404, detail="mission not found")
    if state is None: raise HTTPException(status_code=404, detail="mission not found")
    return state.model_dump(mode="json")
@app.get("/mission/{mission_id}/report")
async def get_report(mission_id: str):
    report = runtime.report(mission_id)
    if report is None: raise HTTPException(status_code=404, detail="report not found")
    return report.model_dump(mode="json")
@app.get("/capabilities")
async def capabilities(): return [cap.model_dump(mode="json") for cap in runtime.registry.list()]
@app.get("/policy")
async def policy(): return {"source": router.policy.source_path, "version": router.policy.version, "schema_version": router.policy.schema_version, "confidence_threshold": router.policy.confidence_threshold, "stages": list(router.policy.stages), "owner": router.policy.owner, "router_access": router.policy.router_access}
@app.get("/health")
async def health(): return {"status": "ok", "version": "0.1.0", "routed": runtime.router is not None, "journal_chain_valid": runtime.journal.verify_chain()}
