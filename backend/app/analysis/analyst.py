import re
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

class AnalysisFilter(BaseModel):
    column: str
    operator: str = "ILIKE"
    value: str
    metric: Optional[str] = None

class AnalysisPlan(BaseModel):
    objective: str = Field(description="The analytical objective")
    metrics: List[str] = Field(default_factory=list, description="List of metrics to calculate (column names)")
    dimensions: List[str] = Field(default_factory=list, description="List of dimensions for grouping/segmentation (column names)")
    filters: List[Dict[str, Any]] = Field(default_factory=list, description="Filters applied to calculation")
    time_dimension: Optional[str] = Field(default=None, description="Column name to use for time-based analysis")

def generate_plan(
    business_goal: str,
    schema: Dict[str, Any],
    profile: Dict[str, Any],
    semantic_context: Dict[str, Any],
) -> AnalysisPlan:
    """
    Propose structured analytical plan aligned directly with the user's business goal.
    Extracts explicit metrics, dimensions, and filter conditions from user natural language query.
    """
    logger.info("Generating analytical plan for business goal: %s", business_goal)

    cols = []
    num_cols = []
    cat_cols = []
    time_col = None

    if isinstance(schema, dict) and "columns" in schema:
        cols = [c["name"] for c in schema["columns"] if isinstance(c, dict) and "name" in c]
        for c in schema["columns"]:
            if isinstance(c, dict) and "name" in c:
                t = str(c.get("type", "")).lower()
                if any(k in t for k in ["int", "float", "double", "num", "decimal"]):
                    num_cols.append(c["name"])
                elif any(k in t for k in ["date", "time"]):
                    time_col = c["name"]
                else:
                    cat_cols.append(c["name"])
    elif isinstance(schema, list):
        cols = [c.get("name") for c in schema if isinstance(c, dict) and "name" in c]
        for c in schema:
            if isinstance(c, dict) and "name" in c:
                t = str(c.get("type", "")).lower()
                if any(k in t for k in ["int", "float", "double", "num", "decimal"]):
                    num_cols.append(c["name"])
                elif any(k in t for k in ["date", "time"]):
                    time_col = c["name"]
                else:
                    cat_cols.append(c["name"])

    if isinstance(profile, dict) and "column_profiles" in profile:
        p_num = []
        p_cat = []
        for c_name, c_info in profile["column_profiles"].items():
            if isinstance(c_info, dict):
                k = c_info.get("type_kind") or c_info.get("kind")
                if k in ("numeric", "float", "int", "integer"):
                    p_num.append(c_name)
                elif k in ("datetime", "date", "timestamp"):
                    time_col = c_name
                else:
                    p_cat.append(c_name)
        if p_num:
            num_cols = p_num
        if p_cat:
            cat_cols = p_cat

    goal_lower = (business_goal or "").lower()

    # 1. Detect requested metrics
    selected_metrics = []
    # Check each numeric column against user goal
    for col in num_cols:
        col_clean = re.sub(r'[^a-zA-Z0-9]', '', col.lower())
        if col.lower() in goal_lower or (len(col_clean) > 2 and col_clean in goal_lower):
            selected_metrics.append(col)

    # Common aliases (e.g. "sales" -> Sales, "profit" -> Profit)
    if "profit" in goal_lower and "Profit" in num_cols and "Profit" not in selected_metrics:
        selected_metrics.append("Profit")
    if "sales" in goal_lower and "Sales" in num_cols and "Sales" not in selected_metrics:
        selected_metrics.append("Sales")
    if "quantity" in goal_lower and "Quantity" in num_cols and "Quantity" not in selected_metrics:
        selected_metrics.append("Quantity")
    if "discount" in goal_lower and "Discount" in num_cols and "Discount" not in selected_metrics:
        selected_metrics.append("Discount")

    # If no specific metric was mentioned, filter out pure ID/Code columns
    if not selected_metrics:
        usable_metrics = [c for c in num_cols if not any(id_word in c.lower() for id_word in ["id", "postal", "zip", "code", "index"])]
        selected_metrics = usable_metrics[:4] if usable_metrics else num_cols[:2]

    # 2. Detect requested dimensions (handle common typos like "segement" -> Segment)
    selected_dimensions = []
    dimension_aliases = {
        "segment": "Segment",
        "segement": "Segment",
        "region": "Region",
        "category": "Category",
        "sub-category": "Sub-Category",
        "subcategory": "Sub-Category",
        "ship mode": "Ship Mode",
        "shipping mode": "Ship Mode",
        "state": "State",
        "city": "City",
        "country": "Country",
        "customer": "Customer Name",
    }
    for alias, dim_name in dimension_aliases.items():
        if alias in goal_lower and dim_name in cat_cols and dim_name not in selected_dimensions:
            selected_dimensions.append(dim_name)

    for col in cat_cols:
        if col.lower() in goal_lower and col not in selected_dimensions:
            selected_dimensions.append(col)

    if not selected_dimensions:
        usable_dims = [c for c in cat_cols if not any(id_word in c.lower() for id_word in ["id", "date"])]
        selected_dimensions = usable_dims[:2] if usable_dims else cat_cols[:1]

    # 3. Detect filters (e.g., "furniture", "technology", "office supplies")
    detected_filters = []
    category_keywords = {
        "furniture": ("Category", "Furniture"),
        "technology": ("Category", "Technology"),
        "office supplies": ("Category", "Office Supplies"),
    }
    for kw, (f_col, f_val) in category_keywords.items():
        if kw in goal_lower:
            detected_filters.append({
                "column": f_col,
                "operator": "ILIKE",
                "value": f_val,
                "metric": "Profit" if "profit" in goal_lower else ("Sales" if "sales" in goal_lower else None)
            })

    # Time dimension check
    if any(w in goal_lower for w in ["time", "month", "year", "quarter", "trend", "daily", "annual"]):
        time_dim = time_col
    else:
        time_dim = None

    objective = f"Analyze {business_goal or 'dataset metrics & segment distributions'}"

    return AnalysisPlan(
        objective=objective,
        metrics=selected_metrics,
        dimensions=selected_dimensions,
        filters=detected_filters,
        time_dimension=time_dim
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
        "filtered_results": [],
        "provenance": [],
        "summary": "",
        "executive_summary": ""
    }

    # 1. Calculate overall KPIs
    summary_parts = []
    for metric in plan_obj.metrics:
        col_q = f'"{metric}"'
        try:
            query_kpi = f'SELECT SUM({col_q}) as sum_val, AVG({col_q}) as avg_val, MIN({col_q}) as min_val, MAX({col_q}) as max_val FROM "{v_name}"'
            res_df = conn.execute(query_kpi).df()
            res_dict = res_df.to_dict(orient="records")[0] if not res_df.empty else {}
            
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

    # 2. Calculate Segmentation Breakdowns
    if plan_obj.dimensions:
        dim = plan_obj.dimensions[0]
        dim_q = f'"{dim}"'
        
        # Build aggregations for up to 2 primary metrics
        metric_aggs = []
        for m in plan_obj.metrics[:2]:
            metric_aggs.append(f'ROUND(SUM("{m}"), 2) as total_{m.lower().replace(" ", "_")}')
            metric_aggs.append(f'ROUND(AVG("{m}"), 2) as avg_{m.lower().replace(" ", "_")}')
        
        agg_clause = ", " + ", ".join(metric_aggs) if metric_aggs else f', COUNT(*) as count'
        query_seg = f'SELECT {dim_q} as segment, COUNT(*) as record_count{agg_clause} FROM "{v_name}" GROUP BY {dim_q} ORDER BY record_count DESC LIMIT 15'
        
        try:
            res_df = conn.execute(query_seg).df()
            res_records = res_df.to_dict(orient="records") if not res_df.empty else []
            
            seg_key = f"{dim}_breakdown"
            report["segments"][seg_key] = res_records
            report["provenance"].append({
                "dataset": dataset_id,
                "table": v_name,
                "columns": [dim] + plan_obj.metrics[:2],
                "query": query_seg,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            
            # Add to executive summary
            top_segments = [f"{r['segment']} ({r.get('total_sales', r.get('record_count'))})" for r in res_records[:3]]
            summary_parts.append(f"Top {dim}s: {', '.join(top_segments)}.")
        except Exception as e:
            logger.warning(f"Failed to calculate segment for '{dim}': {e}")

    # 3. Calculate Targeted Filters (e.g. Furniture category profit)
    for flt in plan_obj.filters:
        col = flt.get("column")
        val = flt.get("value")
        target_m = flt.get("metric") or (plan_obj.metrics[0] if plan_obj.metrics else None)
        
        if col and val:
            col_q = f'"{col}"'
            m_clause = f', ROUND(SUM("{target_m}"), 2) as total_{target_m.lower()}' if target_m else ""
            query_flt = f"SELECT COUNT(*) as record_count{m_clause} FROM \"{v_name}\" WHERE LOWER(CAST({col_q} AS VARCHAR)) LIKE LOWER('%{val}%')"
            
            try:
                flt_df = conn.execute(query_flt).df()
                flt_records = flt_df.to_dict(orient="records")[0] if not flt_df.empty else {}
                filter_info = {
                    "filter": f"{col} = '{val}'",
                    "results": flt_records
                }
                report["filtered_results"].append(filter_info)
                report["provenance"].append({
                    "dataset": dataset_id,
                    "table": v_name,
                    "columns": [col] + ([target_m] if target_m else []),
                    "query": query_flt,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })
                
                if target_m and f"total_{target_m.lower()}" in flt_records:
                    summary_parts.append(
                        f"For {col} '{val}': Total {target_m} is {flt_records[f'total_{target_m.lower()}']:,} across {flt_records['record_count']:,} records."
                    )
            except Exception as e:
                logger.warning(f"Failed to calculate filter {flt}: {e}")

    exec_summary = " ".join(summary_parts) if summary_parts else f"Deterministic execution completed for objective: {plan_obj.objective}."
    report["summary"] = exec_summary
    report["executive_summary"] = exec_summary

    return report

