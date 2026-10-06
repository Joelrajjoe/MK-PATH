from datetime import datetime, timezone
import logging
import uuid
from typing import Any, Dict, List
import pandas as pd
from pydantic import BaseModel

from ..config import settings

logger = logging.getLogger("mkpath.healing.engine")


class TransformationPlan(BaseModel):
    problem_detected: str
    remediation_proposal: str
    estimated_impact: str
    requires_approval: bool
    columns_affected: List[str]


class BeforeAfterQualityReport(BaseModel):
    before_score: float
    after_score: float
    improvements: List[str]


class HealingEvent(BaseModel):
    plan: TransformationPlan
    status: str
    derived_dataset_id: str
    derived_path: str
    quality_report: BeforeAfterQualityReport
    timestamp: str


def generate_healing_plan(dataset_id: str, profile: Any) -> TransformationPlan:
    """
    Generate healing plan from actual profile findings.
    """
    if hasattr(profile, "model_dump"):
        profile = profile.model_dump()
    elif hasattr(profile, "dict"):
        profile = profile.dict()
    elif not isinstance(profile, dict):
        profile = {}

    quality_score = profile.get("quality_score", 100.0)
    issue_count = profile.get("issue_count", 0)
    
    # Identify affected columns from profile summary or columns list
    columns_affected = []
    col_profiles = profile.get("column_profiles", {})
    if isinstance(col_profiles, dict):
        for col_name, c_prof in col_profiles.items():
            if isinstance(c_prof, dict) and c_prof.get("null_count", 0) > 0:
                columns_affected.append(col_name)

    if not columns_affected and profile.get("columns"):
        columns_affected = [c["name"] for c in profile.get("columns", []) if c.get("null_count", 0) > 0]

    if not columns_affected:
        return TransformationPlan(
            problem_detected=f"Data Quality Score is {quality_score} with {issue_count} minor issue(s).",
            remediation_proposal="No transformation required; data quality is optimal.",
            estimated_impact="0 rows modified",
            requires_approval=False,
            columns_affected=[]
        )

    return TransformationPlan(
        problem_detected=f"Missing values detected in {len(columns_affected)} column(s): {', '.join(columns_affected[:5])}.",
        remediation_proposal="Forward-fill and back-fill missing values, preserving row integrity.",
        estimated_impact=f"Impute missing values across {len(columns_affected)} column(s) without dropping rows.",
        requires_approval=False,
        columns_affected=columns_affected
    )


def apply_healing(dataset: pd.DataFrame, plan: TransformationPlan, dataset_id: str) -> HealingEvent:
    """
    Apply safe autonomous data transformation on actual dataframe and calculate real before/after metrics.
    """
    logger.info("Applying safe autonomous data transformation.")

    # 1. Never modify original data
    derived_df = dataset.copy()

    # Calculate actual before statistics
    before_nulls = int(derived_df.isna().sum().sum())
    total_cells = int(derived_df.size)
    before_score = float(max(0.0, min(100.0, 100.0 - (before_nulls / total_cells * 100.0)))) if total_cells > 0 else 100.0

    # 2. Apply transformations
    if plan.columns_affected:
        derived_df[plan.columns_affected] = derived_df[plan.columns_affected].ffill().bfill().fillna(0)

    after_nulls = int(derived_df.isna().sum().sum())
    after_score = float(max(0.0, min(100.0, 100.0 - (after_nulls / total_cells * 100.0)))) if total_cells > 0 else 100.0
    imputed_count = before_nulls - after_nulls

    # Save derived dataset
    derived_id = str(uuid.uuid4().hex)
    derived_dir = settings.DATA_DIR / "derived"
    derived_dir.mkdir(parents=True, exist_ok=True)
    derived_path = derived_dir / f"{derived_id}.parquet"

    derived_df.to_parquet(derived_path)

    # 3. Real BeforeAfter quality report
    report = BeforeAfterQualityReport(
        before_score=round(before_score, 2),
        after_score=round(after_score, 2),
        improvements=[f"Successfully imputed {imputed_count} missing cell value(s) across {len(plan.columns_affected)} column(s)."]
    )

    return HealingEvent(
        plan=plan,
        status="COMPLETED",
        derived_dataset_id=derived_id,
        derived_path=str(derived_path),
        quality_report=report,
        timestamp=datetime.now(timezone.utc).isoformat()
    )
