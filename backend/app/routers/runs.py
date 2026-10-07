import uuid
import logging
from typing import Any, Dict, Optional, List
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from ..database import db_manager
from ..repo import utcnow, MetadataUnavailable
from ..orchestrator.graph import get_compiled_graph

logger = logging.getLogger("mkpath.runs")

router = APIRouter(prefix="/api/runs", tags=["runs"])


class ExecuteRunRequest(BaseModel):
    project_id: str
    dataset_id: str
    business_goal: Optional[str] = ""


def _require_db() -> None:
    if db_manager.get_database() is None:
        raise HTTPException(status_code=503, detail={"code": "METADATA_UNAVAILABLE", "message": "Metadata store unavailable."})


@router.post("/execute", status_code=201)
async def execute_run(req: ExecuteRunRequest) -> Dict[str, Any]:
    _require_db()
    run_id = uuid.uuid4().hex
    
    initial_state = {
        "project_id": req.project_id,
        "dataset_id": req.dataset_id,
        "dataset_ids": [req.dataset_id],
        "run_id": run_id,
        "business_goal": req.business_goal or "",
    }
    
    try:
        compiled_graph = get_compiled_graph()
        # Execute workflow
        config = {"configurable": {"thread_id": run_id}}
        final_state = await compiled_graph.ainvoke(initial_state, config=config)
        
        doc = {
            "run_id": run_id,
            "project_id": req.project_id,
            "dataset_id": req.dataset_id,
            "business_goal": req.business_goal or "",
            "status": final_state.get("status", "COMPLETED"),
            "state": final_state,
            "verification_results": final_state.get("verification_results"),
            "selected_model": final_state.get("selected_model"),
            "artifacts": final_state.get("artifacts"),
            "created_at": utcnow().isoformat(),
        }
        
        coll = db_manager.get_collection("runs")
        if coll is not None:
            await coll.insert_one(dict(doc))
            
        return doc
    except Exception as exc:
        logger.error(f"Run execution failed: {exc}")
        raise HTTPException(status_code=500, detail=f"Run execution failed: {type(exc).__name__}: {exc}")


@router.get("")
async def list_runs(
    project_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200)
) -> List[Dict[str, Any]]:
    _require_db()
    coll = db_manager.get_collection("runs")
    if coll is None:
        raise HTTPException(status_code=503, detail="Database not ready.")
    query = {"project_id": project_id} if project_id else {}
    cursor = coll.find(query, {"_id": 0}).sort("created_at", -1).limit(limit)
    return [doc async for doc in cursor]


@router.get("/{run_id}")
async def get_run(run_id: str) -> Dict[str, Any]:
    _require_db()
    coll = db_manager.get_collection("runs")
    if coll is None:
        raise HTTPException(status_code=503, detail="Database not ready.")
        
    doc = await coll.find_one({"run_id": run_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Run not found.")
    return doc


@router.get("/{run_id}/audit")
async def get_run_audit(run_id: str) -> Dict[str, Any]:
    _require_db()
    coll = db_manager.get_collection("audit_events")
    if coll is None:
        raise HTTPException(status_code=503, detail="Database not ready.")
        
    cursor = coll.find({"run_id": run_id}, {"_id": 0, "secrets": 0, "api_key": 0}).sort("timestamp", 1)
    events = [doc async for doc in cursor]
    
    return {"run_id": run_id, "events": events}


@router.get("/{run_id}/verification")
async def get_run_verification(run_id: str) -> Dict[str, Any]:
    _require_db()
    coll = db_manager.get_collection("runs")
    if coll is None:
        raise HTTPException(status_code=503, detail="Database not ready.")
        
    doc = await coll.find_one({"run_id": run_id}, {"_id": 0, "verification_results": 1})
    if not doc or "verification_results" not in doc:
        raise HTTPException(status_code=404, detail="Verification results not found for this run.")
        
    return {"run_id": run_id, "verification": doc.get("verification_results", {})}
