"""FastAPI Router for Fault-Injection Benchmark for Verification Gates (FIB-VG).

Exposes typed, audited endpoints for:
- Listing and inspecting registered scenario catalog
- Triggering authorized benchmark runs (all, category, or subset)
- Polling run status, aggregate metrics, and scenario-level evidence
- Comparing benchmark runs
- Inspecting versioned release policies and historical runs
"""
import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from ..benchmark.catalog import get_scenario, list_scenarios
from ..benchmark.models import FaultCategory, Severity
from ..benchmark.policy import POLICIES
from ..benchmark.service import benchmark_service
from ..database import db_manager

logger = logging.getLogger("mkpath.benchmark.router")

router = APIRouter(prefix="/api/verification-benchmark", tags=["verification-benchmark"])


def _require_db() -> None:
    if db_manager.get_database() is None:
        raise HTTPException(
            status_code=503,
            detail={"code": "METADATA_UNAVAILABLE", "message": "Metadata store unavailable."},
        )


class RunBenchmarkRequest(BaseModel):
    project_id: str
    scenario_ids: Optional[List[str]] = None
    category: Optional[FaultCategory] = None
    policy_id: Optional[str] = "FIB-RELEASE-POLICY-v1.0"
    dataset_fingerprint: Optional[str] = None


class CompareRunsRequest(BaseModel):
    run_id_a: str
    run_id_b: str


@router.get("/policies")
async def get_benchmark_policies() -> Dict[str, Any]:
    """Retrieve available versioned release policies."""
    return {
        "policies": [p.model_dump() for p in POLICIES.values()],
        "default_policy_id": "FIB-RELEASE-POLICY-v1.0",
    }


@router.get("/scenarios")
async def get_scenario_catalog(
    category: Optional[FaultCategory] = Query(None),
    severity: Optional[Severity] = Query(None),
) -> Dict[str, Any]:
    """Retrieve the registered scenario catalog with optional filters."""
    specs = list_scenarios(category=category, severity=severity)
    return {
        "catalog_version": "FIB-CATALOG-v1.0",
        "total_scenarios": len(specs),
        "scenarios": [s.model_dump() for s in specs],
    }


@router.get("/scenarios/{scenario_id}")
async def get_scenario_detail(scenario_id: str) -> Dict[str, Any]:
    """Retrieve detail of a specific registered scenario."""
    try:
        spec = get_scenario(scenario_id)
        return {"scenario": spec.model_dump()}
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Scenario '{scenario_id}' not found in catalog.")


@router.post("/runs")
async def execute_benchmark_run(req: RunBenchmarkRequest) -> Dict[str, Any]:
    """Start an authorized benchmark run against registered scenario specifications."""
    try:
        record = await benchmark_service.execute_benchmark_run(
            project_id=req.project_id,
            scenario_ids=req.scenario_ids,
            category=req.category,
            policy_id=req.policy_id or "FIB-RELEASE-POLICY-v1.0",
            dataset_fingerprint=req.dataset_fingerprint,
        )
        return record.model_dump()
    except Exception as exc:
        logger.error("Failed to execute benchmark run: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Benchmark execution failed: {type(exc).__name__}: {exc}")


@router.get("/runs/{run_id}")
async def get_run_status(run_id: str) -> Dict[str, Any]:
    """Retrieve the summary status and gate decision of a benchmark run."""
    run = await benchmark_service.get_benchmark_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Benchmark run '{run_id}' not found.")
    return run


@router.get("/runs/{run_id}/results")
async def get_run_results(
    run_id: str,
    category: Optional[FaultCategory] = Query(None),
) -> Dict[str, Any]:
    """Retrieve scenario-level results and evidence references for a benchmark run."""
    run = await benchmark_service.get_benchmark_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Benchmark run '{run_id}' not found.")
    results = await benchmark_service.get_scenario_results(run_id, category=category)
    return {
        "run_id": run_id,
        "total_results": len(results),
        "results": results,
    }


@router.get("/runs/{run_id}/metrics")
async def get_run_metrics(run_id: str) -> Dict[str, Any]:
    """Retrieve calculated deterministic metrics for a benchmark run."""
    run = await benchmark_service.get_benchmark_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Benchmark run '{run_id}' not found.")
    return {
        "run_id": run_id,
        "aggregate_metrics": run.get("aggregate_metrics"),
        "gate_decision": run.get("gate_decision"),
    }


@router.get("/runs/{run_id}/audit")
async def get_run_audit_trail(run_id: str) -> Dict[str, Any]:
    """Retrieve audit events associated with a benchmark run."""
    db = db_manager.get_database()
    if db is None:
        raise HTTPException(status_code=503, detail="Database not ready.")
    cursor = db["audit_events"].find({"run_id": run_id}, {"_id": 0}).sort("created_at", -1)
    events = [doc async for doc in cursor]
    return {"run_id": run_id, "audit_events": events, "total": len(events)}


@router.get("/history")
async def list_benchmark_history(
    project_id: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> Dict[str, Any]:
    """List historical benchmark runs with pagination."""
    runs = await benchmark_service.list_benchmark_runs(project_id=project_id, limit=limit, offset=offset)
    return {
        "project_id": project_id,
        "total": len(runs),
        "runs": runs,
    }


@router.post("/compare")
async def compare_benchmark_runs(req: CompareRunsRequest) -> Dict[str, Any]:
    """Compare two benchmark runs to assess performance deltas and regressions."""
    try:
        return await benchmark_service.compare_runs(req.run_id_a, req.run_id_b)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
