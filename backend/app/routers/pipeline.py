import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
import pandas as pd

from ..database import db_manager
from ..repo import get_dataset, MetadataUnavailable
from ..analysis import analyst
from ..modeling import tournament
from ..healing import engine as healing_engine
from ..ingestion import registry
from ..verification.engine import run_verification_gates

logger = logging.getLogger("mkpath.pipeline")

router = APIRouter(prefix="/api", tags=["pipeline"])


def _require_db() -> None:
    if db_manager.get_database() is None:
        raise HTTPException(status_code=503, detail={"code": "METADATA_UNAVAILABLE", "message": "Metadata store unavailable."})


class AnalysisPlanRequest(BaseModel):
    business_goal: str
    dataset_id: str


class AnalysisExecuteRequest(BaseModel):
    plan: Dict[str, Any]
    dataset_id: str


class TournamentRequest(BaseModel):
    dataset_id: str
    target: str
    is_temporal: bool = False


class HealingPlanRequest(BaseModel):
    dataset_id: str


class HealingApplyRequest(BaseModel):
    dataset_id: str
    plan: Dict[str, Any]


@router.post("/analysis/plan")
async def create_analysis_plan(req: AnalysisPlanRequest) -> Dict[str, Any]:
    _require_db()
    ds_doc = await get_dataset(req.dataset_id)
    if not ds_doc:
        raise HTTPException(status_code=404, detail="Dataset not found.")

    schema = ds_doc.get("schema", {})
    profile = ds_doc.get("profile", {})
    
    from ..semantic import service as semantic_service
    semantic_ctx = await semantic_service.get_latest_context(req.dataset_id) or {}

    plan = analyst.generate_plan(req.business_goal, schema, profile, semantic_ctx)
    return {"dataset_id": req.dataset_id, "plan": plan}


@router.post("/analysis/execute")
async def execute_analysis_plan(req: AnalysisExecuteRequest) -> Dict[str, Any]:
    _require_db()
    ds_doc = await get_dataset(req.dataset_id)
    if not ds_doc:
        raise HTTPException(status_code=404, detail="Dataset not found.")

    table_name = ds_doc.get("table_name", "dataset")
    normalized_path = ds_doc.get("normalized_path")
    results = analyst.execute_plan(req.plan, {
        "dataset_id": req.dataset_id,
        "table_name": table_name,
        "normalized_path": normalized_path
    })
    return {"dataset_id": req.dataset_id, "results": results}


@router.post("/models/tournament")
async def run_tournament(req: TournamentRequest) -> Dict[str, Any]:
    _require_db()
    ds_doc = await get_dataset(req.dataset_id)
    if not ds_doc:
        raise HTTPException(status_code=404, detail="Dataset not found.")

    try:
        registry.ensure_view(req.dataset_id, ds_doc.get("normalized_path"))
        conn = registry.get_conn()
        v_name = registry.view_name(req.dataset_id)
        df = conn.execute(f'SELECT * FROM "{v_name}"').df()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Failed to load dataset view: {exc}")

    res = tournament.run_model_tournament(df, req.target, is_temporal=req.is_temporal)
    return res


@router.post("/healing/plan")
async def create_healing_plan(req: HealingPlanRequest) -> Dict[str, Any]:
    _require_db()
    ds_doc = await get_dataset(req.dataset_id)
    if not ds_doc:
        raise HTTPException(status_code=404, detail="Dataset not found.")

    profile = ds_doc.get("profile", {})
    plan = healing_engine.generate_healing_plan(req.dataset_id, profile)
    return {"dataset_id": req.dataset_id, "plan": plan.model_dump()}


@router.post("/healing/apply")
async def apply_data_healing(req: HealingApplyRequest) -> Dict[str, Any]:
    _require_db()
    ds_doc = await get_dataset(req.dataset_id)
    if not ds_doc:
        raise HTTPException(status_code=404, detail="Dataset not found.")

    try:
        registry.ensure_view(req.dataset_id, ds_doc.get("normalized_path"))
        conn = registry.get_conn()
        v_name = registry.view_name(req.dataset_id)
        df = conn.execute(f'SELECT * FROM "{v_name}"').df()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Failed to load dataset view: {exc}")

    plan_obj = healing_engine.TransformationPlan(**req.plan)
    event = healing_engine.apply_healing(df, plan_obj, req.dataset_id)
    event_dict = event.model_dump()
    event_dict["dataset_id"] = req.dataset_id
    event_dict["project_id"] = ds_doc.get("project_id")

    from ..audit import record_audit
    await record_audit(
        "HEALING_APPLIED",
        project_id=ds_doc.get("project_id"),
        dataset_id=req.dataset_id,
        details={
            "derived_dataset_id": event_dict.get("derived_dataset_id"),
            "derived_path": event_dict.get("derived_path"),
            "improvements": event_dict.get("quality_report", {}).get("improvements", [])
        },
        status="ok"
    )

    coll = db_manager.get_collection("healing_events")
    if coll is not None:
        try:
            await coll.insert_one(dict(event_dict))
        except Exception:
            pass

    return event_dict


@router.get("/healing/events")
async def list_healing_events(
    dataset_id: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100)
) -> Dict[str, Any]:
    _require_db()
    coll = db_manager.get_collection("healing_events")
    if coll is None:
        return {"events": []}
    query: Dict[str, Any] = {}
    if dataset_id:
        query["dataset_id"] = dataset_id
    cursor = coll.find(query, {"_id": 0}).sort("timestamp", -1).limit(limit)
    events = [doc async for doc in cursor]
    return {"events": events}


@router.get("/verification/gates")
async def get_verification_gates(
    project_id: str = Query("project_1"),
    run_id: str = Query("run_1"),
    quality_score: float = Query(100.0)
) -> Dict[str, Any]:
    report = run_verification_gates(project_id, run_id, {
        "data_quality_score": quality_score,
        "temporal_leakage_risk": "LOW"
    })
    return report.model_dump()


@router.get("/artifacts")
async def list_artifacts(
    project_id: Optional[str] = Query(None),
    run_id: Optional[str] = Query(None)
) -> Dict[str, Any]:
    _require_db()
    coll = db_manager.get_collection("runs")
    if coll is None:
        raise HTTPException(status_code=503, detail="Database not ready.")
    query: Dict[str, Any] = {}
    if project_id:
        query["project_id"] = project_id
    if run_id:
        query["run_id"] = run_id

    cursor = coll.find(query, {"_id": 0}).sort("created_at", -1)
    artifacts = []
    async for doc in cursor:
        run_arts = doc.get("artifacts") or []
        for a in run_arts:
            if isinstance(a, dict):
                art_entry = dict(a)
                art_entry["project_id"] = doc.get("project_id")
                art_entry["run_id"] = a.get("run_id") or doc.get("run_id")
                art_entry["created_at"] = doc.get("created_at")
                artifacts.append(art_entry)
    return {"artifacts": artifacts}


@router.get("/audit")
async def list_audit_events(
    project_id: Optional[str] = Query(None),
    dataset_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200)
) -> Dict[str, Any]:
    _require_db()
    coll = db_manager.get_collection("audit_events")
    if coll is None:
        raise HTTPException(status_code=503, detail="Database not ready.")

    query: Dict[str, Any] = {}
    if project_id:
        query["project_id"] = project_id
    if dataset_id:
        query["dataset_id"] = dataset_id

    cursor = coll.find(query, {"_id": 0, "secrets": 0, "api_key": 0}).sort("created_at", -1).limit(limit)
    events = []
    async for doc in cursor:
        if "created_at" in doc and hasattr(doc["created_at"], "isoformat"):
            doc["created_at"] = doc["created_at"].isoformat()
        if "action" not in doc:
            doc["action"] = doc.get("event_type", "EVENT")
        if "timestamp" not in doc or not doc["timestamp"]:
            doc["timestamp"] = doc.get("created_at")
        events.append(doc)
    return {"events": events, "total": len(events)}
