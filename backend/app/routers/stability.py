"""FastAPI Router for Plan-Multiverse Stability Gate (PMSG).

Exposes typed, audited endpoints for:
- Proposing and validating analytical plans
- Previewing proposed variants without executing them
- Executing the deterministic multiverse engine against real DuckDB views
- Polling run status, variant breakdowns, and stability metrics
- Retrieving versioned gate policies and comparing historical runs
"""
import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from ..database import db_manager
from ..repo import get_dataset
from ..stability import service
from ..stability.gate import POLICIES
from ..stability.generator import generate_variants
from ..stability.models import (
    AnalysisPlanSpec,
    AnalysisVariant,
    GateDecision,
    PmsgRunRecord,
)

logger = logging.getLogger("mkpath.stability.router")

router = APIRouter(prefix="/api/stability", tags=["stability"])


def _require_db() -> None:
    if db_manager.get_database() is None:
        raise HTTPException(
            status_code=503,
            detail={"code": "METADATA_UNAVAILABLE", "message": "Metadata store unavailable."},
        )


class PlanProposalRequest(BaseModel):
    dataset_id: str
    project_id: str
    business_goal: Optional[str] = None


class VariantPreviewRequest(BaseModel):
    dataset_id: str
    plan: Dict[str, Any]
    max_variants: int = Field(default=15, ge=1, le=50)


class RunMultiverseRequest(BaseModel):
    dataset_id: str
    project_id: str
    plan: Optional[Dict[str, Any]] = None
    policy_id: Optional[str] = "PMSG-POLICY-v1.0"


class CompareRunsRequest(BaseModel):
    run_id_a: str
    run_id_b: str


@router.get("/policies")
async def get_stability_policies() -> Dict[str, Any]:
    """Retrieve available versioned stability gate policies."""
    return {
        "policies": [p.model_dump() for p in POLICIES.values()],
        "default_policy_id": "PMSG-POLICY-v1.0",
    }


@router.post("/plan")
async def propose_plan(req: PlanProposalRequest) -> Dict[str, Any]:
    """
    Propose a sound, typed analysis specification for a dataset and goal.
    """
    _require_db()
    ds_doc = await get_dataset(req.dataset_id)
    if not ds_doc:
        raise HTTPException(status_code=404, detail=f"Dataset {req.dataset_id} not found.")

    schema_cols = [c.get("name") for c in ds_doc.get("schema", []) if isinstance(c, dict) and "name" in c]
    if not schema_cols:
        from ..ingestion import registry
        registry.ensure_view(req.dataset_id, ds_doc.get("normalized_path"))
        conn = registry.get_conn()
        v_name = registry.view_name(req.dataset_id)
        desc = conn.execute(f'DESCRIBE "{v_name}"').fetchall()
        schema_cols = [c[0] for c in desc]

    plan = service.propose_accident_plan(req.dataset_id, req.project_id, schema_cols)
    if req.business_goal:
        plan.analysis_question = f"Evaluate finding robustness for: {req.business_goal.strip()}"

    return {"plan": plan.model_dump(), "dataset_name": ds_doc.get("name") or ds_doc.get("table_name")}


@router.post("/variants/preview")
async def preview_variants(req: VariantPreviewRequest) -> Dict[str, Any]:
    """
    Generate and preview analytical variants without executing queries.
    """
    _require_db()
    ds_doc = await get_dataset(req.dataset_id)
    if not ds_doc:
        raise HTTPException(status_code=404, detail=f"Dataset {req.dataset_id} not found.")

    schema_cols = [c.get("name") for c in ds_doc.get("schema", []) if isinstance(c, dict) and "name" in c]
    col_types = {c.get("name"): c.get("type", "") for c in ds_doc.get("schema", []) if isinstance(c, dict) and "name" in c}

    if not schema_cols:
        from ..ingestion import registry
        registry.ensure_view(req.dataset_id, ds_doc.get("normalized_path"))
        conn = registry.get_conn()
        v_name = registry.view_name(req.dataset_id)
        desc = conn.execute(f'DESCRIBE "{v_name}"').fetchall()
        schema_cols = [c[0] for c in desc]
        col_types = {c[0]: c[1] for c in desc}

    plan_spec = AnalysisPlanSpec(**req.plan)
    variants = generate_variants(plan_spec, schema_cols, col_types, max_variants=req.max_variants)

    comparable_count = len([v for v in variants if v.variant_class in ("IMPLEMENTATION", "SPECIFICATION")])
    estimand_count = len([v for v in variants if v.variant_class == "ESTIMAND_CHANGE"])
    invalid_count = len([v for v in variants if v.variant_class == "INVALID"])

    return {
        "variants": [v.model_dump() for v in variants],
        "summary": {
            "total_variants": len(variants),
            "comparable_variants": comparable_count,
            "estimand_change_variants": estimand_count,
            "incompatible_variants": invalid_count,
            "execution_budget": req.max_variants,
        },
    }


@router.post("/run")
async def run_multiverse(req: RunMultiverseRequest) -> Dict[str, Any]:
    """
    Execute deterministic multiverse stability analysis against real dataset in DuckDB.
    Persists results and decision to MongoDB Atlas.
    """
    _require_db()
    try:
        run_record = await service.execute_stability_run(
            dataset_id=req.dataset_id,
            project_id=req.project_id,
            plan_dict=req.plan,
            policy_id=req.policy_id,
        )
        return run_record.model_dump()
    except ValueError as val_err:
        raise HTTPException(status_code=400, detail=str(val_err))
    except Exception as exc:
        logger.error("Failed to execute stability multiverse: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Stability multiverse execution failed: {exc}")


@router.get("/runs/{run_id}")
async def get_run_details(run_id: str) -> Dict[str, Any]:
    """Retrieve full execution record and gate decision for a run."""
    _require_db()
    run = await service.get_stability_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found.")
    return run


@router.get("/runs")
async def list_runs(
    project_id: Optional[str] = Query(None),
    dataset_id: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
) -> Dict[str, Any]:
    """List historical stability gate runs."""
    _require_db()
    runs = await service.list_stability_runs(project_id, dataset_id, limit=limit)
    return {"runs": runs, "total": len(runs)}


@router.post("/compare")
async def compare_runs(req: CompareRunsRequest) -> Dict[str, Any]:
    """Compare two explicit stability runs."""
    _require_db()
    run_a = await service.get_stability_run(req.run_id_a)
    run_b = await service.get_stability_run(req.run_id_b)

    if not run_a:
        raise HTTPException(status_code=404, detail=f"Run '{req.run_id_a}' not found.")
    if not run_b:
        raise HTTPException(status_code=404, detail=f"Run '{req.run_id_b}' not found.")

    m_a = run_a.get("stability_metrics", {})
    m_b = run_b.get("stability_metrics", {})
    d_a = run_a.get("gate_decision", {})
    d_b = run_b.get("gate_decision", {})

    return {
        "run_a": {
            "run_id": run_a.get("run_id"),
            "dataset_id": run_a.get("dataset_id"),
            "status": d_a.get("overall_status"),
            "persistence": m_a.get("top_category_persistence"),
            "spearman_rho": m_a.get("spearman_rank_correlation"),
            "reversal_rate": m_a.get("conclusion_reversal_rate"),
        },
        "run_b": {
            "run_id": run_b.get("run_id"),
            "dataset_id": run_b.get("dataset_id"),
            "status": d_b.get("overall_status"),
            "persistence": m_b.get("top_category_persistence"),
            "spearman_rho": m_b.get("spearman_rank_correlation"),
            "reversal_rate": m_b.get("conclusion_reversal_rate"),
        },
        "deltas": {
            "persistence_delta": round((m_b.get("top_category_persistence", 0) - m_a.get("top_category_persistence", 0)), 4),
            "spearman_rho_delta": round((m_b.get("spearman_rank_correlation", 0) - m_a.get("spearman_rank_correlation", 0)), 4),
            "reversal_rate_delta": round((m_b.get("conclusion_reversal_rate", 0) - m_a.get("conclusion_reversal_rate", 0)), 4),
        },
    }
