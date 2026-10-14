"""Deterministic DuckDB execution engine for Plan-Multiverse Stability Gate.

Executes each analytical variant against real dataset views in DuckDB.
Captures exact row counts, exclusions, numerators, denominators, timings,
and query hashes with complete provenance.
"""
import hashlib
import logging
import re
import time
from typing import Any, Dict, List, Optional, Tuple

import duckdb
from ..ingestion import registry
from .models import (
    AnalysisPlanSpec,
    AnalysisVariant,
    CategoryPolicy,
    MissingValuePolicy,
    OutlierPolicy,
    TimeWindowPolicy,
    VariantClass,
    VariantExecutionResult,
)

logger = logging.getLogger("mkpath.stability.executor")


def _sanitize_ident(name: str) -> str:
    """Safe column/table identifier quoting."""
    clean = re.sub(r'[^a-zA-Z0-9_]', '', name)
    return f'"{clean}"'


def execute_variant(
    conn: duckdb.DuckDBPyConnection,
    table_name: str,
    variant: AnalysisVariant,
    plan: AnalysisPlanSpec,
) -> VariantExecutionResult:
    """
    Execute a single analytical variant against DuckDB view and return provenance.
    """
    if variant.compatibility_status == "INCOMPATIBLE":
        return VariantExecutionResult(
            variant_id=variant.variant_id,
            variant_name=variant.name,
            variant_class=variant.variant_class,
            estimand_family=variant.estimand_family,
            status="INCOMPATIBLE",
            error_message=variant.incompatibility_reason or "Incompatible with dataset schema.",
            primary_finding_summary=f"Skipped: {variant.incompatibility_reason}",
        )

    t0 = time.perf_counter()
    grp_col = plan.grouping_column
    target_col = plan.target_variable
    params = variant.parameters

    mv_policy = params.get("missing_value_policy", plan.missing_value_policy.value)
    denom_def = params.get("denominator_definition", plan.denominator_definition)
    outlier_policy = params.get("outlier_policy", plan.outlier_policy.value)
    cat_policy = params.get("category_policy", plan.category_policy.value)
    time_window = params.get("time_window", plan.time_window.value)
    date_col = params.get("date_column", plan.date_column)

    try:
        # Base count in table
        total_in_table = conn.execute(f'SELECT count(*) FROM "{table_name}"').fetchone()[0]

        where_clauses: List[str] = []
        exclusions: Dict[str, int] = {}

        # 1. Missing value handling
        if mv_policy == MissingValuePolicy.EXCLUDE_MISSING.value:
            where_clauses.append(f'"{grp_col}" IS NOT NULL AND trim(cast("{grp_col}" as varchar)) != \'\'')
            cnt_valid = conn.execute(f'SELECT count(*) FROM "{table_name}" WHERE "{grp_col}" IS NOT NULL AND trim(cast("{grp_col}" as varchar)) != \'\'').fetchone()[0]
            exclusions["missing_grouping"] = total_in_table - cnt_valid
            grp_expr = f'"{grp_col}"'
        else:
            # INCLUDE_UNKNOWN
            grp_expr = f'COALESCE(NULLIF(trim(cast("{grp_col}" as varchar)), \'\'), \'Unknown\')'
            exclusions["missing_grouping"] = 0

        # 2. Outlier policy
        outlier_col = params.get("outlier_column")
        if outlier_policy == OutlierPolicy.QUANTILE_TRIM_99.value and outlier_col:
            q_res = conn.execute(f'SELECT percentile_cont(0.99) WITHIN GROUP (ORDER BY "{outlier_col}") FROM "{table_name}" WHERE "{outlier_col}" IS NOT NULL').fetchone()
            if q_res and q_res[0] is not None:
                p99 = float(q_res[0])
                where_clauses.append(f'("{outlier_col}" IS NULL OR "{outlier_col}" <= {p99})')
                outlier_dropped = conn.execute(f'SELECT count(*) FROM "{table_name}" WHERE "{outlier_col}" > {p99}').fetchone()[0]
                exclusions["outliers_trimmed"] = outlier_dropped

        # 3. Time window policy
        if time_window in (TimeWindowPolicy.EARLY_WINDOW.value, TimeWindowPolicy.LATE_WINDOW.value) and date_col:
            med_res = conn.execute(f'SELECT "{date_col}" FROM "{table_name}" WHERE "{date_col}" IS NOT NULL ORDER BY "{date_col}" LIMIT 1 OFFSET (SELECT CAST(count(*)/2 AS BIGINT) FROM "{table_name}" WHERE "{date_col}" IS NOT NULL)').fetchone()
            if med_res and med_res[0] is not None:
                med_val = str(med_res[0]).replace("'", "''")
                if time_window == TimeWindowPolicy.EARLY_WINDOW.value:
                    where_clauses.append(f'"{date_col}" <= \'{med_val}\'')
                else:
                    where_clauses.append(f'"{date_col}" > \'{med_val}\'')

        base_filter_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

        # 4. Category grouping policy (e.g. merge rare)
        if cat_policy == CategoryPolicy.MERGE_RARE_THRESHOLD.value:
            min_count = params.get("min_category_count", 250)
            # Find rare groups
            rare_df = conn.execute(f'''
                SELECT {grp_expr} as g, count(*) as c 
                FROM "{table_name}" 
                WHERE {base_filter_sql} 
                GROUP BY {grp_expr} 
                HAVING count(*) < {min_count}
            ''').df()
            rare_list = rare_df["g"].tolist() if not rare_df.empty else []
            if rare_list:
                escaped_list = ", ".join([f"'{str(x).replace(chr(39), chr(39)+chr(39))}'" for x in rare_list])
                final_grp_expr = f"CASE WHEN {grp_expr} IN ({escaped_list}) THEN 'Other / Rare Groups' ELSE {grp_expr} END"
            else:
                final_grp_expr = grp_expr
        else:
            final_grp_expr = grp_expr

        # 5. Build estimand query
        pop_filter = plan.population_filter or f'"{target_col}" = \'Yes\''

        if denom_def == "within_group_total":
            # ESTIMAND_CHANGE: Rate within category = (count where target_filter) / (total in that category)
            query_sql = f"""
                SELECT 
                    {final_grp_expr} as grp,
                    sum(case when {pop_filter} then 1 else 0 end) as numerator,
                    count(*) as denominator,
                    round(sum(case when {pop_filter} then 1 else 0 end) * 1.0 / nullif(count(*), 0), 6) as metric_value
                FROM "{table_name}"
                WHERE {base_filter_sql}
                GROUP BY {final_grp_expr}
                ORDER BY metric_value DESC, numerator DESC
            """
        elif denom_def == "all_records_total":
            # SPECIFICATION: Group target events / ALL records in population
            query_sql = f"""
                WITH den_cte AS (
                    SELECT count(*) as total_pop 
                    FROM "{table_name}" 
                    WHERE {base_filter_sql}
                )
                SELECT 
                    {final_grp_expr} as grp,
                    count(*) as numerator,
                    den_cte.total_pop as denominator,
                    round(count(*) * 1.0 / nullif(den_cte.total_pop, 0), 6) as metric_value
                FROM "{table_name}", den_cte
                WHERE {base_filter_sql} AND ({pop_filter})
                GROUP BY {final_grp_expr}, den_cte.total_pop
                ORDER BY metric_value DESC, numerator DESC
            """
        else:
            # Baseline / valid_population_total: Group target events / total target events
            query_sql = f"""
                WITH den_cte AS (
                    SELECT count(*) as total_events 
                    FROM "{table_name}" 
                    WHERE {base_filter_sql} AND ({pop_filter})
                )
                SELECT 
                    {final_grp_expr} as grp,
                    count(*) as numerator,
                    den_cte.total_events as denominator,
                    round(count(*) * 1.0 / nullif(den_cte.total_events, 0), 6) as metric_value
                FROM "{table_name}", den_cte
                WHERE {base_filter_sql} AND ({pop_filter})
                GROUP BY {final_grp_expr}, den_cte.total_events
                ORDER BY metric_value DESC, numerator DESC
            """

        df = conn.execute(query_sql).df()
        duration_ms = (time.perf_counter() - t0) * 1000.0

        query_hash = hashlib.sha256(query_sql.strip().encode("utf-8")).hexdigest()[:12]

        rankings: List[Dict[str, Any]] = []
        metric_values: Dict[str, float] = {}
        sample_size = 0

        for idx, row in df.iterrows():
            grp = str(row["grp"])
            num = float(row["numerator"]) if row["numerator"] is not None else 0.0
            den = float(row["denominator"]) if row["denominator"] is not None else 0.0
            val = float(row["metric_value"]) if row["metric_value"] is not None else 0.0
            if idx == 0 and denom_def != "within_group_total":
                sample_size = int(den)
            elif denom_def == "within_group_total":
                sample_size += int(den)

            metric_values[grp] = val
            rankings.append({
                "rank": idx + 1,
                "group": grp,
                "numerator": num,
                "denominator": den,
                "metric_value": val,
            })

        top_cat = rankings[0]["group"] if rankings else None
        top_val = rankings[0]["metric_value"] if rankings else None
        total_excluded = sum(exclusions.values())

        if denom_def == "within_group_total":
            summary = f"Top occurrence rate: {top_cat} ({top_val:.2%}) with N={sample_size} total group observations."
        else:
            summary = f"Top share: {top_cat} ({top_val:.2%}) with N={sample_size} analyzed denominator."

        return VariantExecutionResult(
            variant_id=variant.variant_id,
            variant_name=variant.name,
            variant_class=variant.variant_class,
            estimand_family=variant.estimand_family,
            status="SUCCESS",
            sample_size=sample_size,
            excluded_rows=total_excluded,
            exclusion_reasons=exclusions,
            metric_values=metric_values,
            rankings=rankings,
            top_category=top_cat,
            top_value=top_val,
            primary_finding_summary=summary,
            query_sql=query_sql.strip(),
            query_hash=query_hash,
            duration_ms=round(duration_ms, 2),
        )

    except Exception as exc:
        duration_ms = (time.perf_counter() - t0) * 1000.0
        logger.error("Variant %s execution error: %s", variant.variant_id, exc)
        return VariantExecutionResult(
            variant_id=variant.variant_id,
            variant_name=variant.name,
            variant_class=variant.variant_class,
            estimand_family=variant.estimand_family,
            status="FAILED",
            error_message=str(exc),
            primary_finding_summary=f"Execution error: {exc}",
            duration_ms=round(duration_ms, 2),
        )


def execute_multiverse(
    dataset_id: str,
    normalized_path: Optional[str],
    variants: List[AnalysisVariant],
    plan: AnalysisPlanSpec,
) -> Tuple[List[VariantExecutionResult], float]:
    """
    Execute all declared variants against the registered DuckDB dataset view.
    """
    registry.ensure_view(dataset_id, normalized_path)
    conn = registry.get_conn()
    v_name = registry.view_name(dataset_id)

    total_t0 = time.perf_counter()
    results: List[VariantExecutionResult] = []

    for var in variants:
        res = execute_variant(conn, v_name, var, plan)
        results.append(res)

    total_duration_ms = (time.perf_counter() - total_t0) * 1000.0
    return results, round(total_duration_ms, 2)
