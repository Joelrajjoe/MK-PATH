"""Plan-Multiverse Stability Gate (PMSG) orchestration and persistence service.

Coordinates:
- Plan generation & validation
- Bounded variant preview
- Deterministic multiverse execution in DuckDB
- Mathematical stability metric evaluation
- Policy-driven gate decision
- MongoDB Atlas persistence in collection 'pmsg_runs'
- Audit trail emission to 'audit_events'
"""
from datetime import datetime, timezone
import hashlib
import logging
from typing import Any, Dict, List, Optional
import uuid

from ..audit import record_audit
from ..database import db_manager
from ..repo import get_dataset
from .executor import execute_multiverse
from .gate import evaluate_gate_decision, get_policy
from .generator import generate_variants
from .metrics import evaluate_stability
from .models import (
    AnalysisPlanSpec,
    AnalysisType,
    CategoryPolicy,
    GateDecision,
    GateStatus,
    MissingValuePolicy,
    OutlierPolicy,
    PmsgRunRecord,
    StabilityMetrics,
    TimeWindowPolicy,
    VariantClass,
)

logger = logging.getLogger("mkpath.stability.service")


def propose_accident_plan(dataset_id: str, project_id: str, available_cols: List[str]) -> AnalysisPlanSpec:
    """
    Construct supported primary plan for synthetic road accidents prevention dataset.
    """
    has_road_type = "road_type" in available_cols
    has_accident_occ = "accident_occurred" in available_cols
    has_date = "incident_date" in available_cols

    grp = "road_type" if has_road_type else available_cols[0]
    target = "accident_occurred" if has_accident_occ else (available_cols[1] if len(available_cols) > 1 else available_cols[0])

    return AnalysisPlanSpec(
        analysis_id=f"plan_{uuid.uuid4().hex[:10]}",
        project_id=project_id,
        dataset_id=dataset_id,
        dataset_version="v1",
        analysis_question="How does the distribution of recorded accidents across available road categories change under defensible denominator and missing-value policies?",
        analysis_type=AnalysisType.CATEGORY_PROPORTION,
        target_variable=target,
        grouping_column=grp,
        metric_type="proportion",
        population_filter="\"accident_occurred\" = 'Yes'" if has_accident_occ else None,
        denominator_definition="valid_population_total",
        missing_value_policy=MissingValuePolicy.EXCLUDE_MISSING,
        outlier_policy=OutlierPolicy.NONE,
        category_policy=CategoryPolicy.PRESERVE_ALL,
        time_window=TimeWindowPolicy.ALL_TIME,
        date_column="incident_date" if has_date else None,
        assumptions=[
            "Records represent distinct accident or near-miss incident reports.",
            "Road type categorization is mutually exclusive at incident time.",
            "Vehicle miles traveled (VMT) exposure is unavailable in this schema and is excluded from primary estimand."
        ],
        required_columns=[grp, target],
        estimand_family="population_share",
        predeclared_stability_policy_id="PMSG-POLICY-v1.0",
    )


async def execute_stability_run(
    dataset_id: str,
    project_id: str,
    plan_dict: Optional[Dict[str, Any]] = None,
    policy_id: Optional[str] = None,
    created_by: str = "analyst_agent",
) -> PmsgRunRecord:
    """
    Execute full deterministic multiverse stability run against DuckDB and persist to Atlas.
    """
    ds_doc = await get_dataset(dataset_id)
    if not ds_doc:
        raise ValueError(f"Dataset {dataset_id} not found in metadata repository.")

    normalized_path = ds_doc.get("normalized_path")
    schema_cols = [c.get("name") for c in ds_doc.get("schema", []) if isinstance(c, dict) and "name" in c]
    col_types = {c.get("name"): c.get("type", "") for c in ds_doc.get("schema", []) if isinstance(c, dict) and "name" in c}

    # If schema is empty, inspect DuckDB directly
    if not schema_cols:
        from ..ingestion import registry
        registry.ensure_view(dataset_id, normalized_path)
        conn = registry.get_conn()
        v_name = registry.view_name(dataset_id)
        desc = conn.execute(f'DESCRIBE "{v_name}"').fetchall()
        schema_cols = [c[0] for c in desc]
        col_types = {c[0]: c[1] for c in desc}

    # 1. Build or validate plan
    if plan_dict:
        if "analysis_id" not in plan_dict or not plan_dict["analysis_id"]:
            plan_dict["analysis_id"] = f"plan_{uuid.uuid4().hex[:10]}"
        plan_dict["dataset_id"] = dataset_id
        plan_dict["project_id"] = project_id
        plan = AnalysisPlanSpec(**plan_dict)
    else:
        plan = propose_accident_plan(dataset_id, project_id, schema_cols)

    # Validate required columns
    for req_col in plan.required_columns:
        if req_col not in schema_cols:
            raise ValueError(f"Required column '{req_col}' not present in dataset schema.")

    # 2. Generate variants
    active_policy_id = policy_id or plan.predeclared_stability_policy_id
    variants = generate_variants(plan, schema_cols, col_types, max_variants=15)

    # 3. Execute multiverse in DuckDB
    results, duration_ms = execute_multiverse(dataset_id, normalized_path, variants, plan)

    # 4. Compute stability metrics
    comparable_metrics, estimand_metrics = evaluate_stability(results, primary_variant_id="var_primary_base")

    # 5. Evaluate Gate Decision
    gate_decision = evaluate_gate_decision(comparable_metrics, active_policy_id)

    # 6. Construct Run Record
    run_id = f"pmsg_{uuid.uuid4().hex[:12]}"
    divergent_results = [r for r in results if r.variant_class == VariantClass.ESTIMAND_CHANGE or r.estimand_family != plan.estimand_family]
    standard_results = [r for r in results if r not in divergent_results]

    run_record = PmsgRunRecord(
        run_id=run_id,
        project_id=project_id,
        dataset_id=dataset_id,
        dataset_version=ds_doc.get("dataset_version", "v1"),
        dataset_fingerprint=ds_doc.get("fingerprint", hashlib.sha256(dataset_id.encode()).hexdigest()[:16]),
        question=plan.analysis_question,
        plan=plan,
        variants=variants,
        execution_results=standard_results,
        stability_metrics=comparable_metrics,
        estimand_divergent_results=divergent_results,
        estimand_metrics=estimand_metrics,
        gate_decision=gate_decision,
        created_at=datetime.now(timezone.utc).isoformat(),
        created_by=created_by,
        duration_total_ms=duration_ms,
    )

    # 7. Persist to MongoDB Atlas
    coll = db_manager.get_collection("pmsg_runs")
    if coll is not None:
        try:
            doc = run_record.model_dump()
            await coll.insert_one(doc)
            logger.info("Persisted PMSG run %s to MongoDB Atlas 'pmsg_runs'", run_id)
        except Exception as exc:
            logger.error("Failed to persist PMSG run to MongoDB Atlas: %s", exc)

    # 8. Record audit event
    await record_audit(
        "STABILITY_GATE_EVALUATED",
        project_id=project_id,
        dataset_id=dataset_id,
        run_id=run_id,
        details={
            "overall_status": gate_decision.overall_status.value,
            "policy_id": active_policy_id,
            "top_category_persistence": comparable_metrics.top_category_persistence,
            "spearman_rho": comparable_metrics.spearman_rank_correlation,
            "reversal_rate": comparable_metrics.conclusion_reversal_rate,
            "coverage_ratio": comparable_metrics.coverage_ratio,
            "eligible_for_deployment": gate_decision.eligible_for_deployment,
        },
        status="ok" if gate_decision.overall_status in (GateStatus.PASS, GateStatus.WARNING) else "blocked",
    )

    return run_record


async def get_stability_run(run_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve full persistent run record from MongoDB Atlas."""
    coll = db_manager.get_collection("pmsg_runs")
    if coll is None:
        return None
    doc = await coll.find_one({"run_id": run_id}, {"_id": 0})
    return doc


async def list_stability_runs(
    project_id: Optional[str] = None,
    dataset_id: Optional[str] = None,
    limit: int = 20,
) -> List[Dict[str, Any]]:
    """List historical PMSG runs from MongoDB Atlas."""
    coll = db_manager.get_collection("pmsg_runs")
    if coll is None:
        return []
    query: Dict[str, Any] = {}
    if project_id:
        query["project_id"] = project_id
    if dataset_id:
        query["dataset_id"] = dataset_id

    cursor = coll.find(query, {"_id": 0}).sort("created_at", -1).limit(limit)
    return [doc async for doc in cursor]


async def get_latest_stability_decision(project_id: str, dataset_id: Optional[str] = None) -> Optional[GateDecision]:
    """Retrieve the latest gate decision to feed into overall verification engine."""
    coll = db_manager.get_collection("pmsg_runs")
    if coll is None:
        return None
    query: Dict[str, Any] = {"project_id": project_id}
    if dataset_id:
        query["dataset_id"] = dataset_id

    doc = await coll.find_one(query, {"_id": 0, "gate_decision": 1}, sort=[("created_at", -1)])
    if doc and "gate_decision" in doc:
        return GateDecision(**doc["gate_decision"])
    return None
