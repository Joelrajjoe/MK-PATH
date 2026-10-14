"""Deterministic, bounded variant generator for Plan-Multiverse Stability Gate.

Generates reproducible analytical variants across declared operators:
- Missing-value policies (exclude vs unknown)
- Denominator definitions (population valid vs all records vs within-group vs exposure)
- Outlier filtering policies (quantile trimming)
- Category policies (preserve vs merge rare)
- Date windows (all time vs temporal partitions)

Strictly separates:
- IMPLEMENTATION variants (same estimand, alternative implementation)
- SPECIFICATION variants (defensible alternative specifications of same estimand)
- ESTIMAND_CHANGE variants (materially different research questions, isolated into distinct families)
- INVALID variants (unsupported by schema or missing required columns)
"""
import hashlib
import json
import logging
from typing import Any, Dict, List, Optional, Set

from .models import (
    AnalysisPlanSpec,
    AnalysisVariant,
    CategoryPolicy,
    MissingValuePolicy,
    OutlierPolicy,
    TimeWindowPolicy,
    VariantClass,
)

logger = logging.getLogger("mkpath.stability.generator")


def _stable_hash(payload: Dict[str, Any]) -> str:
    """Generate deterministic 8-char hash for canonical variant parameters."""
    canonical_str = json.dumps(payload, sort_keys=True)
    return hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()[:8]


def generate_variants(
    plan: AnalysisPlanSpec,
    available_columns: List[str],
    column_types: Optional[Dict[str, str]] = None,
    max_variants: int = 15,
) -> List[AnalysisVariant]:
    """
    Generate a deterministic, bounded set of defensible analytical variants.
    Validates column presence and assigns appropriate VariantClass.
    """
    col_set: Set[str] = set(available_columns)
    types: Dict[str, str] = column_types or {}

    variants: List[AnalysisVariant] = []

    # 1. Base / Primary Plan Variant
    primary_params = {
        "missing_value_policy": plan.missing_value_policy.value,
        "denominator_definition": plan.denominator_definition,
        "outlier_policy": plan.outlier_policy.value,
        "category_policy": plan.category_policy.value,
        "time_window": plan.time_window.value,
        "population_filter": plan.population_filter,
    }
    variants.append(
        AnalysisVariant(
            variant_id="var_primary_base",
            name="Primary Plan (Baseline)",
            variant_class=VariantClass.IMPLEMENTATION,
            operator_category="base",
            estimand_family=plan.estimand_family,
            description="Declared primary analytical specification and baseline estimand.",
            is_primary=True,
            parameters=primary_params,
            compatibility_status="COMPATIBLE",
        )
    )

    # 2. Operator A: Missing-Value Policy Alternative
    # If primary is exclude_missing, test include_unknown
    if plan.missing_value_policy == MissingValuePolicy.EXCLUDE_MISSING:
        mv_params = dict(primary_params)
        mv_params["missing_value_policy"] = MissingValuePolicy.INCLUDE_UNKNOWN.value
        variants.append(
            AnalysisVariant(
                variant_id="var_mv_unknown",
                name="Missing Values: Explicit 'Unknown' Category",
                variant_class=VariantClass.IMPLEMENTATION,
                operator_category="missing_values",
                estimand_family=plan.estimand_family,
                description="Retains rows with missing/blank grouping values by assigning an explicit 'Unknown' category.",
                is_primary=False,
                parameters=mv_params,
                compatibility_status="COMPATIBLE",
            )
        )
    else:
        mv_params = dict(primary_params)
        mv_params["missing_value_policy"] = MissingValuePolicy.EXCLUDE_MISSING.value
        variants.append(
            AnalysisVariant(
                variant_id="var_mv_exclude",
                name="Missing Values: Complete-Case Exclusion",
                variant_class=VariantClass.IMPLEMENTATION,
                operator_category="missing_values",
                estimand_family=plan.estimand_family,
                description="Drops rows with missing/blank grouping values.",
                is_primary=False,
                parameters=mv_params,
                compatibility_status="COMPATIBLE",
            )
        )

    # 3. Operator B: Denominator Definitions
    # B1: Specification variant: All observed records in denominator (unconditional proportion)
    denom_all_params = dict(primary_params)
    denom_all_params["denominator_definition"] = "all_records_total"
    variants.append(
        AnalysisVariant(
            variant_id="var_denom_all_records",
            name="Denominator: All Dataset Records",
            variant_class=VariantClass.SPECIFICATION,
            operator_category="denominator",
            estimand_family=plan.estimand_family,
            description="Divides group events by the total count of all records in the population rather than filtered events.",
            is_primary=False,
            parameters=denom_all_params,
            compatibility_status="COMPATIBLE",
        )
    )

    # B2: ESTIMAND_CHANGE variant: Rate within each category (e.g. accidents / total records in that group)
    denom_within_params = dict(primary_params)
    denom_within_params["denominator_definition"] = "within_group_total"
    denom_within_params["metric_type"] = "rate"
    variants.append(
        AnalysisVariant(
            variant_id="var_denom_within_group_rate",
            name="Estimand Change: Group-Specific Occurrence Rate",
            variant_class=VariantClass.ESTIMAND_CHANGE,
            operator_category="denominator",
            estimand_family="within_group_rate",
            description="Calculates the occurrence rate within each category (accidents in group / total records in group). Note: Answers a fundamentally different research question than overall population share.",
            is_primary=False,
            parameters=denom_within_params,
            compatibility_status="COMPATIBLE",
        )
    )

    # B3: Incompatible Denominator Variant: Traffic exposure rate (e.g. accidents per million VMT)
    exposure_cols = [c for c in available_columns if any(k in c.lower() for k in ["vmt", "vehicle_miles", "traffic_exposure", "exposure_rate", "traffic_volume_numeric"])]
    if exposure_cols:
        denom_exp_params = dict(primary_params)
        denom_exp_params["denominator_definition"] = "traffic_exposure"
        denom_exp_params["exposure_column"] = exposure_cols[0]
        variants.append(
            AnalysisVariant(
                variant_id="var_denom_exposure",
                name="Denominator: Traffic Exposure Normalized",
                variant_class=VariantClass.SPECIFICATION,
                operator_category="denominator",
                estimand_family="exposure_rate",
                description=f"Calculates rate normalized by exposure column '{exposure_cols[0]}'.",
                is_primary=False,
                parameters=denom_exp_params,
                compatibility_status="COMPATIBLE",
            )
        )
    else:
        # Schema does not possess exposure data -> Must be recorded as INVALID with reason
        denom_exp_params = dict(primary_params)
        denom_exp_params["denominator_definition"] = "traffic_exposure"
        variants.append(
            AnalysisVariant(
                variant_id="var_denom_exposure_incompatible",
                name="Denominator: Traffic Exposure Rate (Vehicle Miles Traveled)",
                variant_class=VariantClass.INVALID,
                operator_category="denominator",
                estimand_family="exposure_rate",
                description="Traffic exposure rates cannot be calculated without vehicle miles traveled (VMT) or continuous traffic volume data.",
                is_primary=False,
                parameters=denom_exp_params,
                compatibility_status="INCOMPATIBLE",
                incompatibility_reason="Dataset schema lacks continuous traffic exposure or VMT columns. Calculating traffic exposure without exposure data is mathematically invalid.",
            )
        )

    # 4. Operator C: Outlier Filtering Policies
    # Check for continuous numeric columns to trim outliers
    numeric_controls = [
        c for c in available_columns 
        if c not in (plan.target_variable, plan.grouping_column)
        and any(k in types.get(c, "").lower() for k in ["int", "float", "double", "decimal"])
        and any(k in c.lower() for k in ["speed", "response", "time", "distance", "cost", "minutes"])
    ]
    if numeric_controls:
        control_col = numeric_controls[0]
        outlier_params = dict(primary_params)
        outlier_params["outlier_policy"] = OutlierPolicy.QUANTILE_TRIM_99.value
        outlier_params["outlier_column"] = control_col
        variants.append(
            AnalysisVariant(
                variant_id="var_outlier_q99",
                name=f"Outlier Policy: 99th Percentile Cap on '{control_col}'",
                variant_class=VariantClass.SPECIFICATION,
                operator_category="outlier",
                estimand_family=plan.estimand_family,
                description=f"Filters extreme observations above the 99th percentile of '{control_col}'.",
                is_primary=False,
                parameters=outlier_params,
                compatibility_status="COMPATIBLE",
            )
        )
    else:
        # General numeric fallback or record incompatible
        all_numeric = [c for c in available_columns if any(k in types.get(c, "").lower() for k in ["int", "float", "double"])]
        if all_numeric:
            control_col = all_numeric[0]
            outlier_params = dict(primary_params)
            outlier_params["outlier_policy"] = OutlierPolicy.QUANTILE_TRIM_99.value
            outlier_params["outlier_column"] = control_col
            variants.append(
                AnalysisVariant(
                    variant_id="var_outlier_q99",
                    name=f"Outlier Policy: 99th Percentile Cap on '{control_col}'",
                    variant_class=VariantClass.SPECIFICATION,
                    operator_category="outlier",
                    estimand_family=plan.estimand_family,
                    description=f"Filters extreme observations above the 99th percentile of '{control_col}'.",
                    is_primary=False,
                    parameters=outlier_params,
                    compatibility_status="COMPATIBLE",
                )
            )

    # 5. Operator D: Category Handling Policies
    cat_merge_params = dict(primary_params)
    cat_merge_params["category_policy"] = CategoryPolicy.MERGE_RARE_THRESHOLD.value
    cat_merge_params["min_category_count"] = 250  # Or 10%
    variants.append(
        AnalysisVariant(
            variant_id="var_cat_merge_rare",
            name="Category Handling: Merge Rare Categories (< 10%)",
            variant_class=VariantClass.SPECIFICATION,
            operator_category="category",
            estimand_family=plan.estimand_family,
            description="Groups sparse categories (< 250 observations) into a unified 'Other / Infrequent' category to prevent small-sample volatility.",
            is_primary=False,
            parameters=cat_merge_params,
            compatibility_status="COMPATIBLE",
        )
    )

    # 6. Operator E: Date Window Policies
    # Check if a date column is present
    date_cols = [c for c in available_columns if any(k in c.lower() for k in ["date", "time", "timestamp", "year", "month"])]
    if plan.date_column and plan.date_column in col_set:
        active_date_col = plan.date_column
    elif date_cols:
        active_date_col = date_cols[0]
    else:
        active_date_col = None

    if active_date_col:
        time_h1_params = dict(primary_params)
        time_h1_params["time_window"] = TimeWindowPolicy.EARLY_WINDOW.value
        time_h1_params["date_column"] = active_date_col
        variants.append(
            AnalysisVariant(
                variant_id="var_time_early_window",
                name=f"Date Window: Early Half Partition on '{active_date_col}'",
                variant_class=VariantClass.SPECIFICATION,
                operator_category="time_window",
                estimand_family=plan.estimand_family,
                description=f"Evaluates stability across the initial 50% temporal partition using '{active_date_col}'.",
                is_primary=False,
                parameters=time_h1_params,
                compatibility_status="COMPATIBLE",
            )
        )

        time_h2_params = dict(primary_params)
        time_h2_params["time_window"] = TimeWindowPolicy.LATE_WINDOW.value
        time_h2_params["date_column"] = active_date_col
        variants.append(
            AnalysisVariant(
                variant_id="var_time_late_window",
                name=f"Date Window: Late Half Partition on '{active_date_col}'",
                variant_class=VariantClass.SPECIFICATION,
                operator_category="time_window",
                estimand_family=plan.estimand_family,
                description=f"Evaluates stability across the concluding 50% temporal partition using '{active_date_col}'.",
                is_primary=False,
                parameters=time_h2_params,
                compatibility_status="COMPATIBLE",
            )
        )
    else:
        # Date column absent
        time_params = dict(primary_params)
        time_params["time_window"] = "temporal_partition"
        variants.append(
            AnalysisVariant(
                variant_id="var_time_incompatible",
                name="Date Window: Temporal Partitioning",
                variant_class=VariantClass.INVALID,
                operator_category="time_window",
                estimand_family=plan.estimand_family,
                description="Temporal window variants require a valid datetime or calendar field.",
                is_primary=False,
                parameters=time_params,
                compatibility_status="INCOMPATIBLE",
                incompatibility_reason="Dataset lacks a recognized temporal or date column. Temporal slicing cannot be performed.",
            )
        )

    # 7. Operator Interaction (Joint Specification Variant)
    # Combine Missing-value policy + Outlier trim
    joint_params = dict(primary_params)
    joint_params["missing_value_policy"] = MissingValuePolicy.INCLUDE_UNKNOWN.value
    if numeric_controls:
        joint_params["outlier_policy"] = OutlierPolicy.QUANTILE_TRIM_99.value
        joint_params["outlier_column"] = numeric_controls[0]
    variants.append(
        AnalysisVariant(
            variant_id="var_joint_unknown_trimmed",
            name="Joint Specification: Unknowns Retained + Outlier Trimming",
            variant_class=VariantClass.SPECIFICATION,
            operator_category="joint",
            estimand_family=plan.estimand_family,
            description="Evaluates combined effect of retaining unknown categories while filtering extreme values.",
            is_primary=False,
            parameters=joint_params,
            compatibility_status="COMPATIBLE",
        )
    )

    # Bound by execution budget
    return variants[:max_variants]
