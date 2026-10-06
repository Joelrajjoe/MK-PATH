from datetime import datetime, timezone
import json
import logging
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
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
    llm = get_provider()
    
    prompt = f"""
You are an expert Data Analyst. Your task is to generate a structured analytical plan based on the provided inputs.
Do NOT fabricate numerical results.

Inputs:
Business Goal: {business_goal}
Schema: {json.dumps(schema, default=str)}
Profile Summary: {json.dumps(profile, default=str)}
Semantic Context: {json.dumps(semantic_context, default=str)}

Create a structured JSON output with the following fields:
- objective: a short string describing what we want to find out
- metrics: a list of string column names that can be aggregated
- dimensions: a list of string column names to segment by
- time_dimension: a string column name representing time (or null if none)

The output must be pure JSON mapping to the requested schema.
"""
    structured_llm = llm.with_structured_output(AnalysisPlan)
    return structured_llm.invoke(prompt)

def execute_plan(plan: AnalysisPlan, dataset: Dict[str, Any]) -> Dict[str, Any]:
    dataset_id = dataset["dataset_id"]
    table_name = dataset["table_name"]
    db_path = str(settings.DB_DIR / f"{dataset_id}.duckdb")
    
    report = {
        "plan": plan.model_dump(),
        "kpis": {},
        "segments": {},
        "provenance": [],
        "executive_summary": f"Automated analysis for {plan.objective} executed successfully."
    }
    
    with duckdb.connect(db_path, read_only=True) as conn:
        for metric in plan.metrics:
            try:
                # Basic KPI
                query_kpi = f"SELECT SUM({metric}) as sum_val, AVG({metric}) as avg_val FROM {table_name}"
                res_kpi = conn.execute(query_kpi).df().to_dict(orient="records")[0]
                report["kpis"][metric] = res_kpi
                
                report["provenance"].append({
                    "dataset": dataset_id,
                    "table": table_name,
                    "columns": [metric],
                    "query": query_kpi,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })
            except Exception as e:
                logger.warning(f"Failed to calculate KPI for {metric}: {e}")

        if plan.dimensions and plan.metrics:
            dim = plan.dimensions[0]
            metric = plan.metrics[0]
            try:
                query_seg = f"SELECT {dim}, SUM({metric}) as sum_val, AVG({metric}) as avg_val FROM {table_name} GROUP BY {dim} LIMIT 10"
                res_seg = conn.execute(query_seg).df().to_dict(orient="records")
                report["segments"][f"{metric}_by_{dim}"] = res_seg
                
                report["provenance"].append({
                    "dataset": dataset_id,
                    "table": table_name,
                    "columns": [dim, metric],
                    "query": query_seg,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })
            except Exception as e:
                logger.warning(f"Failed to calculate segment for {dim} and {metric}: {e}")

    return report
