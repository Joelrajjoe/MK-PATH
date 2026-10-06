from typing import Any, Dict, List
from fastapi import APIRouter, HTTPException
from ..database import db_manager

router = APIRouter(prefix="/api/runs", tags=["runs"])

def _require_db() -> None:
    if db_manager.get_database() is None:
        raise HTTPException(status_code=503, detail={"code": "METADATA_UNAVAILABLE", "message": "Metadata store unavailable."})

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
        
    # Exclude secrets or raw API keys if they somehow made it in
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
