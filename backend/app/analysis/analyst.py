from datetime import datetime, timezone
import json
import logging
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from decimal import Decimal
import pandas as pd
import duckdb

from ..semantic.llm import get_provider
from ..config import settings

logger = logging.getLogger("mkpath.analysis.analyst")

class AnalysisPlan(BaseModel):
    objective: str = Field(description="The analytical objective")
    metrics: List[str] = Field(description="List of metrics to calculate (column names)")
    dimensions: List[str] = Field(description="List of dimensions for grouping/segmentation (column names)")
    time_dimension: Optional[str] = Field(description="Column name to use for time-based analysis")

def generate_plan(
    business_goal: str,
    schema: Dict[str, Any],
    profile: Dict[str, Any],
    semantic_context: Dict[str, Any],
) -> AnalysisPlan:
    """
    Propose structured analytical plan from real schema, profile, and semantic context.
    """
    logger.info("Generating analytical plan for business goal: %s", business_goal)

    cols = []
    if isinstance(schema, dict) and "columns" in schema:
        cols = [c["name"] for c in schema["columns"] if isinstance(c, dict) and "name" in c]
    elif isinstance(schema, list):
        cols = [c.get("name") for c in schema if isinstance(c, dict) and "name" in c]

    num_cols = []
    cat_cols = []
    time_col = None

    if isinstance(profile, dict) and "column_profiles" in profile:
        for c_name, c_info in profile["column_profiles"].items():
            if isinstance(c_info, dict):
                k = c_info.get("type_kind") or c_info.get("kind")
                if k in ("numeric", "float", "int", "integer"):
                    num_cols.append(c_name)
                elif k in ("datetime", "date", "timestamp"):
                    time_col = c_name
                else:
                    cat_cols.append(c_name)

    if not num_cols and not cat_cols and cols:
        num_cols = cols[:2]
        cat_cols = cols[2:]

    # Extract roles from semantic context if available
    if isinstance(semantic_context, dict):
        if semantic_context.get("metrics"):
            num_cols = [m.get("name") for m in semantic_context["metrics"] if m.get("name")]
        if semantic_context.get("dimensions"):
            cat_cols = [d.get("name") for d in semantic_context["dimensions"] if d.get("name")]

    objective = f"Analyze {business_goal or 'dataset metrics & segment distributions'}"
    metrics = num_cols[:4] if num_cols else cols[:2]
    dimensions = cat_cols[:3] if cat_cols else (cols[2:4] if len(cols) > 2 else cols[:1])

    return AnalysisPlan(
        objective=objective,
        metrics=metrics,
        dimensions=dimensions,
        time_dimension=time_col
    )


def execute_plan(plan: Any, dataset: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute structured analytical plan via DuckDB on real dataset Parquet views.
    No mock data is produced; all numbers originate from SQL aggregation over user data.
    """
    if isinstance(plan, dict):
        plan_obj = AnalysisPlan(**plan)
    else:
        plan_obj = plan

    dataset_id = dataset.get("dataset_id")
    if not dataset_id:
        raise ValueError("dataset_id is required for execute_plan")

    from ..ingestion import registry
    registry.ensure_view(dataset_id, dataset.get("normalized_path"))
    conn = registry.get_conn()
    v_name = registry.view_name(dataset_id)

    report = {
        "objective": plan_obj.objective,
        "plan": plan_obj.model_dump(),
        "kpis": {},
        "segments": {},
        "provenance": [],
        "executive_summary": f"Deterministic execution completed for objective: {plan_obj.objective}."
    }

    for metric in plan_obj.metrics:
        col_q = f'"{metric}"'
        try:
            query_kpi = f'SELECT SUM({col_q}) as sum_val, AVG({col_q}) as avg_val, MIN({col_q}) as min_val, MAX({col_q}) as max_val FROM "{v_name}"'
            res_df = conn.execute(query_kpi).df()
            res_dict = res_df.to_dict(orient="records")[0] if not res_df.empty else {}
            
            # Convert non-serializable numbers
            clean_dict = {k: (float(v) if pd.notnull(v) and isinstance(v, (int, float, Decimal)) else (None if pd.isnull(v) else v)) for k, v in res_dict.items()}
            report["kpis"][metric] = clean_dict
            
            report["provenance"].append({
                "dataset": dataset_id,
                "table": v_name,
                "columns": [metric],
                "query": query_kpi,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
        except Exception as e:
            logger.warning(f"Failed to calculate KPI for metric '{metric}': {e}")

    if plan_obj.dimensions and plan_obj.metrics:
        dim = plan_obj.dimensions[0]
        metric = plan_obj.metrics[0]
        dim_q = f'"{dim}"'
        met_q = f'"{metric}"'
        try:
            query_seg = f'SELECT {dim_q} as segment, COUNT(*) as record_count, AVG({met_q}) as avg_val FROM "{v_name}" GROUP BY {dim_q} ORDER BY record_count DESC LIMIT 10'
            res_df = conn.execute(query_seg).df()
            res_records = res_df.to_dict(orient="records") if not res_df.empty else []
            
            report["segments"][f"{metric}_by_{dim}"] = res_records
            report["provenance"].append({
                "dataset": dataset_id,
                "table": v_name,
                "columns": [dim, metric],
                "query": query_seg,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
        except Exception as e:
            logger.warning(f"Failed to calculate segment for '{dim}' and '{metric}': {e}")

    return report
