"""Deterministic Power BI-Style Analytics Engine.

Executes pure DuckDB SQL aggregations, time intelligence, date hierarchies,
and cross-filtering over real dataset Parquet files.
Zero mock data, zero simulated metrics, zero synthetic numbers.
"""
from datetime import datetime, timezone
import hashlib
import json
import logging
import math
import re
import time
from typing import Any, Dict, List, Optional, Tuple

import duckdb
import pandas as pd

from ..config import settings
from ..ingestion import registry
from .models import (
    Card1QuarterToQuarter,
    Card2YearOverYear,
    Card3TopBottomTeams,
    Card4QuarterlyPerformance,
    Card5MeetingsAttended,
    Card6EngineeringPerformance,
    DashboardAnalyticsPayload,
    DashboardReadinessStatus,
    DataQualitySummary,
    DrilldownRequest,
    DrilldownResponse,
    FilterContext,
    FilterDimensions,
    QuarterlySeriesPoint,
    SparklinePoint,
    TopBottomTeamItem,
)

logger = logging.getLogger("mkpath.analytics.engine")


def _sanitize_col(col_name: str) -> str:
    """Safe column escaping for DuckDB."""
    return f'"{col_name.replace(chr(34), chr(34)+chr(34))}"'


def _safe_float(val: Any, default: float = 0.0) -> float:
    """Safely convert any value to float, handling None, NaN, inf, and strings."""
    if val is None:
        return default
    try:
        f = float(val)
        return default if (math.isnan(f) or math.isinf(f)) else f
    except (ValueError, TypeError):
        return default


def _build_date_parse_expr(date_col: str) -> str:
    """Return robust DuckDB expression to parse date/timestamp from column."""
    sc = _sanitize_col(date_col)
    tsc = f"TRIM(CAST({sc} AS VARCHAR))"
    return (
        f"COALESCE("
        f"TRY_STRPTIME({tsc}, '%B %d, %Y'), "
        f"TRY_STRPTIME({tsc}, '%b %d, %Y'), "
        f"TRY_STRPTIME({tsc}, '%B %d %Y'), "
        f"TRY_STRPTIME({tsc}, '%d %B %Y'), "
        f"TRY_STRPTIME({tsc}, '%d %b %Y'), "
        f"TRY_STRPTIME({tsc}, '%m/%d/%Y %H:%M'), "
        f"TRY_STRPTIME({tsc}, '%d/%m/%Y %H:%M'), "
        f"TRY_STRPTIME({tsc}, '%Y-%m-%d %H:%M:%S'), "
        f"TRY_STRPTIME({tsc}, '%m/%d/%Y'), "
        f"TRY_STRPTIME({tsc}, '%d/%m/%Y'), "
        f"TRY_STRPTIME({tsc}, '%Y-%m-%d'), "
        f"TRY_STRPTIME({tsc}, '%d-%m-%Y'), "
        f"TRY_STRPTIME({tsc}, '%Y/%m/%d'), "
        f"TRY_CAST({tsc} AS TIMESTAMP), "
        f"TRY_CAST({tsc} AS DATE), "
        f"CASE WHEN TRY_CAST({tsc} AS INTEGER) BETWEEN 20000 AND 60000 "
        f"     THEN DATE '1899-12-30' + to_days(TRY_CAST({tsc} AS INTEGER)) "
        f"     ELSE NULL END"
        f")"
    )


def _is_identifier_col(c: str) -> bool:
    """Determine if a column is a technical identifier/key rather than a business dimension."""
    cl = c.lower().replace("-", "_")
    if cl in ("id", "uuid", "guid", "key", "pk", "fk", "index", "no", "code", "num", "row_id", "rowid"):
        return True
    if cl.startswith("id_") or cl.startswith("uuid_"):
        return True
    if cl.endswith("_id") or cl.endswith("_uuid") or cl.endswith("_guid"):
        return True
    if cl.endswith("_no") or cl.endswith("_num") or cl.endswith("_code"):
        return True
    # Note: don't blanket reject columns ending in 'key' if they are business dimensions (channelKey, storeKey)
    if cl in ("saleskey", "orderkey", "linekey", "rowkey", "factkey"):
        return True
    return False


def _detect_schema_roles(
    conn: duckdb.DuckDBPyConnection,
    table_name: str
) -> Dict[str, Any]:
    """
    Introspect DuckDB schema to identify:
    - Date / Temporal column
    - Primary Categorical column (e.g. channel, team, department, category, segment)
    - Secondary Categorical column (e.g. store, region, location, city, state, country)
    - Primary Numeric metric column (e.g. sales, amount, quantity, profit, speed_limit, volume)
    - Target event column (e.g. accident_occurred, status, is_success)
    """
    desc = conn.execute(f'DESCRIBE "{table_name}"').fetchall()
    cols = [d[0] for d in desc]
    types = {d[0]: str(d[1]).lower() for d in desc}

    date_col = None
    # 1. Date column search: prefer true date/timestamp columns over integer keys
    for c in cols:
        cl = c.lower()
        if cl in ("date", "order_date", "incident_date", "invoicedate", "created_at", "transaction_date"):
            date_col = c
            break
        if any(k in types[c] for k in ["date", "timestamp"]) and not cl.endswith("key"):
            date_col = c
            break

    if not date_col:
        for c in cols:
            cl = c.lower()
            if any(k in cl for k in ["order_date", "incident_date", "invoicedate", "created_at", "date", "timestamp", "time"]):
                date_col = c
                break

    if not date_col:
        for c, t in types.items():
            if any(k in t for k in ["date", "timestamp", "time"]):
                date_col = c
                break

    # 2. Target event column (e.g. accident_occurred = 'Yes', status = 'Active', etc.)
    target_col = None
    for c in cols:
        cl = c.lower()
        if any(k in cl for k in ["accident_occurred", "occurred", "target", "converted", "is_event", "success", "outcome"]):
            target_col = c
            break

    # 3. Primary numeric column
    num_candidates = [
        c for c in cols
        if any(k in types[c] for k in ["int", "float", "double", "decimal", "numeric", "bigint"])
        and not _is_identifier_col(c)
        and not any(k in c.lower() for k in ["hour", "day", "month", "year", "index", "lat", "lon", "postal", "zip"])
    ]
    primary_num = None
    num_priority = [
        "salesamount", "revenue", "sales_amount", "total_sales", "amount",
        "forecast amount", "budget amount", "forecast_amount", "budget_amount",
        "totalcost", "profit", "margin", "speed_limit", "volume",
        "salesquantity", "quantity", "forecast quantity", "budget quantity"
    ]
    for p in num_priority:
        for c in num_candidates:
            cl = c.lower().replace("_", " ")
            if cl == p or p in cl:
                primary_num = c
                break
        if primary_num:
            break
    if not primary_num and num_candidates:
        primary_num = num_candidates[0]

    # 4. Primary category (team / channel / road_type / department / category / segment)
    cat_candidates = [
        c for c in cols
        if c not in (date_col, target_col, primary_num)
        and not _is_identifier_col(c)
        and any(k in types[c] for k in ["varchar", "string", "text", "char"])
    ]
    if not cat_candidates:
        cat_candidates = [
            c for c in cols
            if c not in (date_col, target_col, primary_num)
            and any(k in types[c] for k in ["varchar", "string", "text", "char"])
        ]
    if not cat_candidates:
        # Check for dimensional key columns in star schemas (e.g. channelKey, storeKey, productKey)
        dim_key_cols = [
            c for c in cols
            if c not in (date_col, target_col, primary_num)
            and any(k in c.lower() for k in ["channel", "store", "product", "category", "segment", "department", "geography", "region", "promo"])
        ]
        if dim_key_cols:
            cat_candidates = dim_key_cols
        else:
            cat_candidates = [c for c in cols if c not in (date_col, target_col, primary_num)]

    primary_cat = None
    for c in cat_candidates:
        cl = c.lower()
        if any(k in cl for k in ["channel", "road_type", "team", "department", "category", "segment", "division"]):
            primary_cat = c
            break
    if not primary_cat:
        for c in cat_candidates:
            cl = c.lower()
            if any(k in cl for k in ["description", "product", "item", "service", "type", "class", "group", "store"]):
                primary_cat = c
                break
    if not primary_cat and cat_candidates:
        primary_cat = cat_candidates[0]
    elif not primary_cat and cols:
        non_date = [c for c in cols if c != date_col]
        primary_cat = non_date[0] if non_date else cols[0]

    if primary_cat not in cols:
        primary_cat = cols[0] if cols else "category"

    # 5. Secondary dimension (store / region / state / city / location / country / weather)
    secondary_candidates = [c for c in cat_candidates if c != primary_cat]
    if not secondary_candidates:
        secondary_candidates = [c for c in cols if c not in (date_col, target_col, primary_num, primary_cat)]

    secondary_cat = None
    if secondary_candidates:
        for c in secondary_candidates:
            cl = c.lower()
            if any(k in cl for k in ["store", "region", "state", "city", "location", "geography", "weather", "branch", "area", "zone"]):
                secondary_cat = c
                break
        if not secondary_cat:
            secondary_cat = secondary_candidates[0]

    if not secondary_cat or secondary_cat not in cols:
        secondary_cat = primary_cat

    return {
        "date_col": date_col,
        "target_col": target_col,
        "primary_cat": primary_cat,
        "secondary_cat": secondary_cat,
        "primary_num": primary_num,
        "types": types,
        "all_cols": cols,
    }



def _resolve_column_for_value(
    conn: Optional[duckdb.DuckDBPyConnection],
    table_name: Optional[str],
    val: Optional[str],
    preferred_col: Optional[str],
    candidate_cols: List[str],
) -> Optional[str]:
    """Check if val exists in preferred_col; if not, find the first candidate_col where it exists."""
    if not val or str(val).lower() in ("all", "all teams / categories", "all categories", "all locations"):
        return preferred_col
    if not conn or not table_name:
        return preferred_col

    val_str = str(val).strip()

    # 1. Check preferred_col first
    if preferred_col:
        try:
            res = conn.execute(
                f'SELECT 1 FROM "{table_name}" WHERE CAST({_sanitize_col(preferred_col)} AS VARCHAR) = ? LIMIT 1',
                [val_str]
            ).fetchone()
            if res:
                return preferred_col
        except Exception:
            pass

    # 2. Check candidate columns
    for c in candidate_cols:
        if c == preferred_col:
            continue
        try:
            res = conn.execute(
                f'SELECT 1 FROM "{table_name}" WHERE CAST({_sanitize_col(c)} AS VARCHAR) = ? LIMIT 1',
                [val_str]
            ).fetchone()
            if res:
                return c
        except Exception:
            continue

    return preferred_col


def _build_filter_sql(
    filter_ctx: Optional[FilterContext],
    roles: Dict[str, Any],
    conn: Optional[duckdb.DuckDBPyConnection] = None,
    v_name: Optional[str] = None,
) -> Tuple[str, List[Any]]:
    """Build safe parameterized WHERE clause from FilterContext with intelligent column resolution."""
    if not filter_ctx:
        return "1=1", []

    clauses: List[str] = []
    params: List[Any] = []

    date_col = roles.get("date_col")
    primary_cat = roles.get("primary_cat")
    secondary_cat = roles.get("secondary_cat")
    types = roles.get("types", {})
    all_cols = roles.get("all_cols", [])

    cat_candidates = [
        c for c in all_cols
        if any(k in types.get(c, "") for k in ["varchar", "string", "text", "char"])
    ]

    # Resolve primary category column
    if filter_ctx.primary_col and filter_ctx.primary_col in all_cols:
        primary_cat = filter_ctx.primary_col
    elif filter_ctx.team and filter_ctx.team.lower() not in ("all", "all teams / categories", "all categories"):
        resolved_p = _resolve_column_for_value(conn, v_name, filter_ctx.team, primary_cat, cat_candidates)
        if resolved_p:
            primary_cat = resolved_p
            roles["primary_cat"] = resolved_p

    # Resolve secondary dimension column
    if filter_ctx.secondary_col and filter_ctx.secondary_col in all_cols:
        secondary_cat = filter_ctx.secondary_col
    elif filter_ctx.location and filter_ctx.location.lower() not in ("all", "all locations"):
        resolved_s = _resolve_column_for_value(conn, v_name, filter_ctx.location, secondary_cat, cat_candidates)
        if resolved_s:
            secondary_cat = resolved_s
            roles["secondary_cat"] = resolved_s

    if date_col:
        parse_expr = _build_date_parse_expr(date_col)
        if filter_ctx.date_range_start:
            clauses.append(f'{parse_expr} >= ?')
            params.append(filter_ctx.date_range_start)

        if filter_ctx.date_range_end:
            clauses.append(f'{parse_expr} <= ?')
            params.append(filter_ctx.date_range_end)

        if filter_ctx.year:
            clauses.append(f'year({parse_expr}) = ?')
            params.append(int(filter_ctx.year))

        if filter_ctx.quarter:
            q_str = str(filter_ctx.quarter).upper().replace("Q", "").strip()
            if q_str.isdigit() and int(q_str) in (1, 2, 3, 4):
                clauses.append(f'quarter({parse_expr}) = ?')
                params.append(int(q_str))

        if filter_ctx.month:
            clauses.append(f'month({parse_expr}) = ?')
            params.append(int(filter_ctx.month))

    if primary_cat and primary_cat in all_cols and filter_ctx.team and filter_ctx.team.lower() not in ("all", "all teams / categories", "all categories"):
        clauses.append(f"COALESCE(NULLIF(CAST({_sanitize_col(primary_cat)} AS VARCHAR), ''), 'Unknown') = ?")
        params.append(filter_ctx.team)

    if secondary_cat and secondary_cat in all_cols and filter_ctx.location and filter_ctx.location.lower() not in ("all", "all locations"):
        clauses.append(f"COALESCE(NULLIF(CAST({_sanitize_col(secondary_cat)} AS VARCHAR), ''), 'General') = ?")
        params.append(filter_ctx.location)

    if filter_ctx.search_query and filter_ctx.search_query.strip():
        q = f"%{filter_ctx.search_query.strip().lower()}%"
        search_subclauses = []
        for c in roles.get("all_cols", [])[:6]:
            search_subclauses.append(f'LOWER(CAST({_sanitize_col(c)} AS VARCHAR)) LIKE ?')
            params.append(q)
        if search_subclauses:
            clauses.append(f"({' OR '.join(search_subclauses)})")

    return " AND ".join(clauses) if clauses else "1=1", params


def compute_dashboard_analytics(
    dataset_id: str,
    project_id: str,
    filter_ctx: Optional[FilterContext] = None,
    dataset_name: Optional[str] = None,
) -> DashboardAnalyticsPayload:
    """
    Execute end-to-end verified analytics for Executive Performance Management Dashboard.
    Directly queries DuckDB over registered Parquet dataset view.
    """
    start_time = time.perf_counter()
    v_name = registry.ensure_view(dataset_id)
    conn = registry.get_cursor()

    # 1. Inspect Schema Roles
    roles = _detect_schema_roles(conn, v_name)

    # 2. Build Filter SQL with intelligent column resolution
    filter_sql, filter_params = _build_filter_sql(filter_ctx, roles, conn, v_name)

    date_col = roles["date_col"]
    target_col = roles["target_col"]
    primary_cat = roles["primary_cat"]
    secondary_cat = roles["secondary_cat"]
    primary_num = roles["primary_num"]

    # 3. Overall Counts & Data Quality Check
    tot_row = conn.execute(f'SELECT count(*) FROM "{v_name}"').fetchone()
    total_records = int(tot_row[0]) if tot_row else 0

    fil_row = conn.execute(
        f'SELECT count(*) FROM "{v_name}" WHERE {filter_sql}',
        filter_params
    ).fetchone()
    filtered_records = int(fil_row[0]) if fil_row else 0

    warnings: List[str] = []
    readiness = DashboardReadinessStatus.READY
    status_msg = "Data verified and live calculated via DuckDB."

    if total_records == 0:
        readiness = DashboardReadinessStatus.BLOCKED
        status_msg = "Dataset contains 0 records."
        warnings.append("Empty dataset.")

    # Check Date Boundaries
    date_min = None
    date_max = None
    date_parse_expr = None
    if date_col:
        date_parse_expr = _build_date_parse_expr(date_col)
        try:
            d_res = conn.execute(
                f'SELECT min(CAST({date_parse_expr} AS VARCHAR)), max(CAST({date_parse_expr} AS VARCHAR)) '
                f'FROM "{v_name}" WHERE {date_parse_expr} IS NOT NULL'
            ).fetchone()
            if d_res and len(d_res) >= 2 and d_res[0] is not None and d_res[1] is not None:
                date_min, date_max = str(d_res[0]), str(d_res[1])
        except Exception as exc:
            logger.warning("Could not extract date boundaries: %s", exc)
            warnings.append(f"Date parsing warning on '{date_col}': {exc}")
    else:
        warnings.append("No explicit calendar date field detected; temporal trends are evaluated sequentially.")

    # -------------------------------------------------------------------------
    # CARD 1: Quarter-to-Quarter / Overall Performance Change
    # -------------------------------------------------------------------------
    card1 = Card1QuarterToQuarter()

    # Define primary event measure expression:
    # If target_col (e.g. accident_occurred = 'Yes'), use that. Else if primary_num, sum it. Else count(*).
    if target_col:
        metric_expr = f"SUM(CASE WHEN CAST({_sanitize_col(target_col)} AS VARCHAR) IN ('Yes', '1', 'True', 'true', 'Y') THEN 1.0 ELSE 0.0 END)"
        card1.metric_label = f"(QTD {target_col.replace('_', ' ').title()})"
        card1.title = f"{target_col.replace('_', ' ').title()} - Quarter-to-Quarter"
    elif primary_num:
        metric_expr = f"SUM(CAST({_sanitize_col(primary_num)} AS DOUBLE))"
        card1.metric_label = f"(QTD {primary_num.replace('_', ' ').title()})"
        card1.title = f"{primary_num.replace('_', ' ').title()} - Quarter-to-Quarter"
    else:
        metric_expr = "COUNT(*)"
        card1.metric_label = f"(QTD Volume)"
        card1.title = f"{primary_cat.replace('_', ' ').title()} Volume - Quarter-to-Quarter"

    # Base filter without quarter or month constraint to enable comparison against prior quarter
    base_filter_ctx = filter_ctx.model_copy(deep=True) if filter_ctx else FilterContext()
    target_q_str = base_filter_ctx.quarter
    target_month = base_filter_ctx.month
    base_filter_ctx.quarter = None
    base_filter_ctx.month = None
    base_filter_sql, base_filter_params = _build_filter_sql(base_filter_ctx, roles, conn, v_name)

    has_temporal = False
    if date_col and date_parse_expr:
        try:
            q_df = conn.execute(f"""
                SELECT 
                    year({date_parse_expr}) as yr,
                    quarter({date_parse_expr}) as qtr,
                    month({date_parse_expr}) as mo,
                    {metric_expr} as m_val
                FROM "{v_name}"
                WHERE {base_filter_sql} AND {date_parse_expr} IS NOT NULL
                GROUP BY 1, 2, 3
                ORDER BY 1, 2, 3
            """, base_filter_params).df()

            if not q_df.empty:
                qtr_agg = q_df.groupby(["yr", "qtr"])["m_val"].sum().reset_index()

                # Check if user selected a specific quarter
                if target_q_str:
                    q_num = int(str(target_q_str).upper().replace("Q", "").strip())
                    target_yr = int(filter_ctx.year) if (filter_ctx and filter_ctx.year) else int(qtr_agg["yr"].max())

                    curr_q_rows = qtr_agg[(qtr_agg["yr"] == target_yr) & (qtr_agg["qtr"] == q_num)]
                    current_q = _safe_float(curr_q_rows["m_val"].iloc[0]) if not curr_q_rows.empty else 0.0

                    prior_q_num = 4 if q_num == 1 else (q_num - 1)
                    prior_yr_num = (target_yr - 1) if q_num == 1 else target_yr
                    prev_q_rows = qtr_agg[(qtr_agg["yr"] == prior_yr_num) & (qtr_agg["qtr"] == prior_q_num)]
                    prev_q = _safe_float(prev_q_rows["m_val"].iloc[0]) if not prev_q_rows.empty else 0.0

                    card1.current_value = current_q
                    card1.previous_value = prev_q
                    if prev_q > 0:
                        change = ((current_q - prev_q) / prev_q) * 100.0
                        card1.change_pct = round(change, 1)
                        card1.change_formatted = f"{'+' if change >= 0 else ''}{change:.0f}%"
                        card1.is_positive = (change >= 0)
                    elif current_q > 0:
                        card1.change_pct = 100.0
                        card1.change_formatted = "+100%"
                        card1.is_positive = True
                    else:
                        card1.change_pct = 0.0
                        card1.change_formatted = "0%"
                        card1.is_positive = True

                    month_rows = q_df[(q_df["yr"] == target_yr) & (q_df["qtr"] == q_num)]
                    for _, row in month_rows.iterrows():
                        m_val_f = _safe_float(row["m_val"])
                        card1.sparkline_points.append(SparklinePoint(
                            label=f"M{int(row['mo'])}",
                            value=m_val_f,
                            formatted=f"{m_val_f:.0f}"
                        ))
                    has_temporal = True

                elif len(qtr_agg) >= 2:
                    current_q = _safe_float(qtr_agg.iloc[-1]["m_val"])
                    prev_q = _safe_float(qtr_agg.iloc[-2]["m_val"])
                    card1.current_value = current_q
                    card1.previous_value = prev_q
                    if prev_q > 0:
                        change = ((current_q - prev_q) / prev_q) * 100.0
                        card1.change_pct = round(change, 1)
                        card1.change_formatted = f"{'+' if change >= 0 else ''}{change:.0f}%"
                        card1.is_positive = (change >= 0)
                    elif current_q > 0:
                        card1.change_pct = 100.0
                        card1.change_formatted = "+100%"
                        card1.is_positive = True
                    else:
                        card1.change_pct = 0.0
                        card1.change_formatted = "0%"
                        card1.is_positive = True

                    recent_months = q_df.tail(6)
                    for _, row in recent_months.iterrows():
                        m_val_f = _safe_float(row["m_val"])
                        card1.sparkline_points.append(SparklinePoint(
                            label=f"M{int(row['mo'])}",
                            value=m_val_f,
                            formatted=f"{m_val_f:.0f}"
                        ))
                    has_temporal = True

                elif len(qtr_agg) == 1:
                    current_q = _safe_float(qtr_agg.iloc[0]["m_val"])
                    card1.current_value = current_q
                    if len(q_df) >= 2:
                        half_point = len(q_df) // 2
                        first_half = _safe_float(q_df.iloc[:half_point]["m_val"].sum())
                        second_half = _safe_float(q_df.iloc[half_point:]["m_val"].sum())
                        card1.previous_value = first_half
                        if first_half > 0:
                            change = ((second_half - first_half) / first_half) * 100.0
                            card1.change_pct = round(change, 1)
                            card1.change_formatted = f"{'+' if change >= 0 else ''}{change:.0f}%"
                            card1.is_positive = (change >= 0)
                        else:
                            card1.change_pct = 0.0
                            card1.change_formatted = "0%"
                            card1.is_positive = True
                    for _, row in q_df.iterrows():
                        m_val_f = _safe_float(row["m_val"])
                        card1.sparkline_points.append(SparklinePoint(
                            label=f"M{int(row['mo'])}",
                            value=m_val_f,
                            formatted=f"{m_val_f:.0f}"
                        ))
                    has_temporal = True
        except Exception as exc:
            logger.warning("Quarterly temporal computation fallback: %s", exc)

    if not has_temporal:
        tot_row_res = conn.execute(f'SELECT {metric_expr} FROM "{v_name}" WHERE {filter_sql}', filter_params).fetchone()
        tot_res = _safe_float(tot_row_res[0] if tot_row_res else 0.0)
        card1.current_value = tot_res

        safe_filtered_cnt = max(1, filtered_records)
        window_df = conn.execute(f"""
            WITH numbered AS (
                SELECT 
                    row_number() OVER() - 1 as r_num,
                    *
                FROM "{v_name}"
                WHERE {filter_sql}
            )
            SELECT 
                FLOOR(r_num * 6.0 / {safe_filtered_cnt}) as slice_idx,
                {metric_expr} as val
            FROM numbered
            GROUP BY 1
            ORDER BY 1
        """, filter_params).df()

        val_col = "val" if (not window_df.empty and "val" in window_df.columns) else (window_df.columns[-1] if not window_df.empty else "val")
        if len(window_df) >= 2 and val_col in window_df.columns:
            mid = len(window_df) // 2
            h1 = _safe_float(window_df.iloc[:mid][val_col].sum())
            h2 = _safe_float(window_df.iloc[mid:][val_col].sum())
            card1.previous_value = h1
            if h1 > 0:
                change = ((h2 - h1) / h1) * 100.0
                card1.change_pct = round(change, 1)
                card1.change_formatted = f"{'+' if change >= 0 else ''}{change:.0f}%"
                card1.is_positive = (change >= 0)
            else:
                card1.change_pct = 0.0
                card1.change_formatted = "0%"
                card1.is_positive = True
        else:
            card1.change_pct = 0.0
            card1.change_formatted = "0%"
            card1.is_positive = True

        card1.status_note = "Chronological window sequence computed across active records."
        if not window_df.empty and val_col in window_df.columns:
            for idx, row in window_df.iterrows():
                v_val = _safe_float(row[val_col])
                card1.sparkline_points.append(SparklinePoint(
                    label=f"P{idx+1}",
                    value=v_val,
                    formatted=f"{v_val:.0f}"
                ))

    # -------------------------------------------------------------------------
    # CARD 2: Year-over-Year / Trajectory Change
    # -------------------------------------------------------------------------
    card2 = Card2YearOverYear()
    card2.selected_team = primary_cat.replace("_", " ").title()
    if primary_num:
        card2.title = f"{primary_num.replace('_', ' ').title()} - Year-over-Year"
        card2.metric_label = f"(YoY {primary_num.replace('_', ' ').title()})"
    elif target_col:
        card2.title = f"{target_col.replace('_', ' ').title()} - Year-over-Year"
        card2.metric_label = f"(YoY {target_col.replace('_', ' ').title()})"
    else:
        card2.title = f"{card2.selected_team} Velocity - Year-over-Year"
        card2.metric_label = f"(YoY {card2.selected_team})"

    # Base filter without year constraint
    y_filter_ctx = filter_ctx.model_copy(deep=True) if filter_ctx else FilterContext()
    selected_year = y_filter_ctx.year
    y_filter_ctx.year = None
    y_filter_sql, y_filter_params = _build_filter_sql(y_filter_ctx, roles, conn, v_name)

    card2_computed = False
    if date_col and date_parse_expr:
        try:
            yr_df = conn.execute(f"""
                SELECT 
                    year({date_parse_expr}) as yr,
                    {metric_expr} as m_val
                FROM "{v_name}"
                WHERE {y_filter_sql} AND {date_parse_expr} IS NOT NULL
                GROUP BY 1
                ORDER BY 1
            """, y_filter_params).df()

            if len(yr_df) >= 2:
                target_y = int(selected_year) if selected_year else int(yr_df.iloc[-1]["yr"])
                curr_y_row = yr_df[yr_df["yr"] == target_y]
                prev_y_row = yr_df[yr_df["yr"] == (target_y - 1)]

                curr_yr = _safe_float(curr_y_row["m_val"].iloc[0]) if not curr_y_row.empty else _safe_float(yr_df.iloc[-1]["m_val"])
                prior_yr = _safe_float(prev_y_row["m_val"].iloc[0]) if not prev_y_row.empty else _safe_float(yr_df.iloc[-2]["m_val"])

                card2.current_value = curr_yr
                card2.prior_year_value = prior_yr
                if prior_yr > 0:
                    yoy = ((curr_yr - prior_yr) / prior_yr) * 100.0
                    card2.change_pct = round(yoy, 1)
                    card2.change_formatted = f"{'+' if yoy >= 0 else ''}{yoy:.0f}%"
                    card2.is_positive = (yoy >= 0)
                elif curr_yr > 0:
                    card2.change_pct = 100.0
                    card2.change_formatted = "+100%"
                    card2.is_positive = True
                else:
                    card2.change_pct = 0.0
                    card2.change_formatted = "0%"
                    card2.is_positive = True

                for _, row in yr_df.iterrows():
                    y_val = _safe_float(row["m_val"])
                    card2.sparkline_points.append(SparklinePoint(
                        label=str(int(row["yr"])),
                        value=y_val,
                        formatted=f"{y_val:.0f}"
                    ))
                card2_computed = True
            elif len(yr_df) == 1:
                single_yr = int(yr_df.iloc[0]["yr"])
                q_breakdown = conn.execute(f"""
                    SELECT 
                        quarter({date_parse_expr}) as qtr,
                        {metric_expr} as q_val
                    FROM "{v_name}"
                    WHERE {y_filter_sql} AND {date_parse_expr} IS NOT NULL
                    GROUP BY 1
                    ORDER BY 1
                """, y_filter_params).df()

                if not q_breakdown.empty:
                    avg_q = _safe_float(q_breakdown["q_val"].mean())
                    if filter_ctx and filter_ctx.quarter:
                        q_num = int(str(filter_ctx.quarter).upper().replace("Q", "").strip())
                        matched_q = q_breakdown[q_breakdown["qtr"] == q_num]
                        current_val = _safe_float(matched_q["q_val"].iloc[0]) if not matched_q.empty else 0.0
                    else:
                        current_val = _safe_float(q_breakdown.iloc[-1]["q_val"])

                    card2.current_value = current_val
                    card2.prior_year_value = round(avg_q, 1)
                    if avg_q > 0:
                        variance = ((current_val - avg_q) / avg_q) * 100.0
                        card2.change_pct = round(variance, 1)
                        card2.change_formatted = f"{'+' if variance >= 0 else ''}{variance:.0f}%"
                        card2.is_positive = (variance >= 0)
                    else:
                        card2.change_pct = 0.0
                        card2.change_formatted = "0%"
                        card2.is_positive = True

                    card2.status_note = f"Single-year dataset ({single_yr}): trajectory vs quarterly baseline."
                    for _, row in q_breakdown.iterrows():
                        qv = _safe_float(row["q_val"])
                        card2.sparkline_points.append(SparklinePoint(
                            label=f"Q{int(row['qtr'])}",
                            value=qv,
                            formatted=f"{qv:.0f}"
                        ))
                    card2_computed = True
        except Exception as exc:
            logger.warning("Yearly calculation fallback: %s", exc)

    if not card2_computed:
        card2.current_value = card1.current_value
        card2.prior_year_value = card1.previous_value
        card2.change_pct = card1.change_pct
        card2.change_formatted = card1.change_formatted
        card2.is_positive = card1.is_positive
        card2.status_note = "Trajectory evaluated across sequential dataset partitions."
        card2.sparkline_points = list(card1.sparkline_points)

    # -------------------------------------------------------------------------
    # CARD 3: Top and Bottom 3 Categories — Proportion / Target Breakdown
    # -------------------------------------------------------------------------
    # If the user already filtered by a specific primary team/category,
    # evaluate top & bottom 3 across secondary_cat (e.g. weather / city) to provide granular insight!
    eval_cat = primary_cat
    if filter_ctx and filter_ctx.team and filter_ctx.team.lower() not in ("all", "all teams / categories", "all categories") and secondary_cat:
        eval_cat = secondary_cat

    dim_display = eval_cat.replace("_", " ").title()
    if target_col:
        card3_title = f"Top and bottom 3 {eval_cat.replace('_', ' ')}s - {target_col.replace('_', ' ')} compliance"
        card3_basis = f"Event rate of {target_col.replace('_', ' ')}"
    elif primary_num:
        card3_title = f"Top and bottom 3 {eval_cat.replace('_', ' ')}s - by {primary_num.replace('_', ' ')}"
        card3_basis = f"Proportion of total {primary_num.replace('_', ' ')}"
    else:
        card3_title = f"Top and bottom 3 {eval_cat.replace('_', ' ')}s - Volume Share (YTD)"
        card3_basis = f"Proportion of {eval_cat.replace('_', ' ')} volume"

    card3 = Card3TopBottomTeams(
        primary_dimension=dim_display,
        title=card3_title,
        calculation_basis=card3_basis
    )

    group_rows = conn.execute(f"""
        SELECT 
            COALESCE(NULLIF(CAST({_sanitize_col(eval_cat)} AS VARCHAR), ''), 'Unknown') as cat_name,
            COUNT(*) as cat_total_rows,
            {metric_expr} as cat_metric
        FROM "{v_name}"
        WHERE {filter_sql}
        GROUP BY 1
        HAVING COUNT(*) > 0
        ORDER BY cat_metric DESC
    """, filter_params).fetchall()

    card3.eligible_record_count = filtered_records

    # Map icons
    top_icons = ["code", "design", "qa"]
    bottom_icons = ["product", "data", "analytics"]

    if group_rows:
        max_metric = float(max(_safe_float(r[2]) for r in group_rows)) if group_rows else 1.0
        if max_metric <= 0:
            max_metric = 1.0

        # Sort descending for top 3
        sorted_desc = sorted(group_rows, key=lambda x: _safe_float(x[2]), reverse=True)
        top_slice = sorted_desc[:3]
        for idx, (cat_name, cat_rows, cat_met) in enumerate(top_slice):
            cat_met_f = _safe_float(cat_met)
            pct = min(100.0, max(5.0, round((cat_met_f / max_metric) * 100.0, 1)))
            card3.top_teams.append(TopBottomTeamItem(
                name=cat_name,
                raw_value=cat_met_f,
                percentage=pct,
                rank=idx + 1,
                is_top=True,
                icon_type=top_icons[idx % len(top_icons)]
            ))

        # Bottom 3 (sorted ascending)
        sorted_asc = sorted(group_rows, key=lambda x: _safe_float(x[2]))
        bottom_slice = sorted_asc[:3]
        for idx, (cat_name, cat_rows, cat_met) in enumerate(bottom_slice):
            cat_met_f = _safe_float(cat_met)
            pct = min(100.0, max(5.0, round((cat_met_f / max_metric) * 100.0, 1)))
            card3.bottom_teams.append(TopBottomTeamItem(
                name=cat_name,
                raw_value=cat_met_f,
                percentage=pct,
                rank=len(group_rows) - idx,
                is_top=False,
                icon_type=bottom_icons[idx % len(bottom_icons)]
            ))

    # -------------------------------------------------------------------------
    # CARD 4: Quarterly / Monthly Performance (Combo Bar + Line Chart)
    # -------------------------------------------------------------------------
    card4 = Card4QuarterlyPerformance()
    distinct_cats = [r[0] for r in group_rows[:5]] if group_rows else ["General"]
    card4.available_tabs = distinct_cats
    active_tab = filter_ctx.team if (filter_ctx and filter_ctx.team and filter_ctx.team in distinct_cats) else distinct_cats[0]
    card4.active_tab = active_tab
    if target_col:
        card4.title = f"Performance Trend - {active_tab}"
        card4.legend_label = target_col.replace('_', ' ').title()
    elif primary_num:
        card4.title = f"Performance Trend - {active_tab}"
        card4.legend_label = primary_num.replace('_', ' ').title()
    else:
        card4.title = f"Volume Trend - {active_tab}"
        card4.legend_label = f"{active_tab} Count"

    # Query series for active tab
    tab_escaped = active_tab.replace("'", "''")
    if filter_ctx and filter_ctx.team and filter_ctx.team.lower() not in ("all", "all teams / categories", "all categories"):
        tab_filter = filter_sql
    else:
        tab_filter = f"{filter_sql} AND COALESCE(NULLIF(CAST({_sanitize_col(eval_cat)} AS VARCHAR), ''), 'Unknown') = '{tab_escaped}'"

    month_names = {1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr", 5: "May", 6: "Jun", 7: "Jul", 8: "Aug", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec"}

    if date_col and date_parse_expr:
        try:
            if filter_ctx and filter_ctx.quarter:
                # User selected a specific quarter: render monthly breakdown (e.g. Apr, May, Jun for Q2)
                combo_df = conn.execute(f"""
                    SELECT 
                        year({date_parse_expr}) as yr,
                        month({date_parse_expr}) as mo,
                        {metric_expr} as bar_m
                    FROM "{v_name}"
                    WHERE {tab_filter} AND {date_parse_expr} IS NOT NULL
                    GROUP BY 1, 2
                    ORDER BY 1, 2
                """, filter_params).df()

                if not combo_df.empty:
                    mean_val = _safe_float(combo_df["bar_m"].mean())
                    for _, row in combo_df.iterrows():
                        y_val = int(row["yr"])
                        mo_val = int(row["mo"])
                        b_val = _safe_float(row["bar_m"])
                        m_name = month_names.get(mo_val, f"M{mo_val}")
                        card4.series.append(QuarterlySeriesPoint(
                            period_label=f"{m_name} {y_val}",
                            year=y_val,
                            quarter=f"M{mo_val}",
                            bar_value=b_val,
                            line_value=round(mean_val, 1)
                        ))
            else:
                # All quarters: render quarterly breakdown
                combo_df = conn.execute(f"""
                    SELECT 
                        year({date_parse_expr}) as yr,
                        quarter({date_parse_expr}) as qtr,
                        {metric_expr} as bar_m
                    FROM "{v_name}"
                    WHERE {tab_filter} AND {date_parse_expr} IS NOT NULL
                    GROUP BY 1, 2
                    ORDER BY 1, 2
                """, filter_params).df()

                if not combo_df.empty:
                    mean_val = _safe_float(combo_df["bar_m"].mean())
                    for _, row in combo_df.iterrows():
                        y_val = int(row["yr"])
                        q_val = f"Q{int(row['qtr'])}"
                        b_val = _safe_float(row["bar_m"])
                        card4.series.append(QuarterlySeriesPoint(
                            period_label=f"{y_val} {q_val}",
                            year=y_val,
                            quarter=q_val,
                            bar_value=b_val,
                            line_value=round(mean_val, 1)
                        ))
        except Exception as exc:
            logger.warning("Combo series query fallback: %s", exc)

    if not card4.series:
        # Partition data into sequential chronological periods from the real dataset using CTE
        safe_filtered_cnt = max(1, filtered_records)
        slice_df = conn.execute(f"""
            WITH numbered AS (
                SELECT 
                    row_number() OVER() - 1 as r_num,
                    *
                FROM "{v_name}"
                WHERE {tab_filter}
            )
            SELECT 
                FLOOR(r_num * 6.0 / {safe_filtered_cnt}) as slice_idx,
                {metric_expr} as bar_val
            FROM numbered
            GROUP BY 1
            ORDER BY 1
        """, filter_params).fetchall()

        vals = [_safe_float(r[1]) for r in slice_df]
        mean_slice = (sum(vals) / len(vals)) if vals else 0.0
        for r in slice_df:
            s_idx = int(r[0])
            b_val = _safe_float(r[1])
            card4.series.append(QuarterlySeriesPoint(
                period_label=f"Period {s_idx + 1}",
                year=datetime.now(timezone.utc).year,
                quarter=f"P{s_idx + 1}",
                bar_value=round(b_val, 1),
                line_value=round(mean_slice, 1)
            ))

    # -------------------------------------------------------------------------
    # CARD 5: Category Breakdown / Engagement / Volume Share (Donut Gauge)
    # -------------------------------------------------------------------------
    card5 = Card5MeetingsAttended()
    card5.available_tabs = distinct_cats[:3]
    active_gauge1_tab = active_tab if active_tab in card5.available_tabs else (card5.available_tabs[0] if card5.available_tabs else "All")
    card5.active_tab = active_gauge1_tab

    # Compute actual attendance rate / within-category event rate from data
    g1_escaped = active_gauge1_tab.replace("'", "''")
    g1_stats = conn.execute(f"""
        SELECT 
            COUNT(*) as denom,
            {metric_expr} as num
        FROM "{v_name}"
        WHERE {filter_sql} AND COALESCE(NULLIF(CAST({_sanitize_col(eval_cat)} AS VARCHAR), ''), 'Unknown') = '{g1_escaped}'
    """, filter_params).fetchone()

    denom1 = _safe_float(g1_stats[0]) if (g1_stats and g1_stats[0]) else 0.0
    num1 = _safe_float(g1_stats[1]) if (g1_stats and g1_stats[1]) else 0.0

    if target_col:
        card5.title = f"{active_gauge1_tab} - {target_col.replace('_', ' ').title()} Rate (QTD)"
        card5.center_label = "Rate"
        rate1 = (num1 / denom1) * 100.0 if denom1 > 0 else 0.0
        card5.percentage = round(min(100.0, max(0.0, rate1)), 1)
        card5.metric_description = f"{card5.percentage:.1f}% positive {target_col.replace('_', ' ')} ({int(num1):,} of {int(denom1):,} records)"
    elif primary_num:
        card5.title = f"{active_gauge1_tab} - {primary_num.replace('_', ' ').title()} Share (QTD)"
        card5.center_label = "Share"
        tot_num_res = conn.execute(f'SELECT {metric_expr} FROM "{v_name}" WHERE {filter_sql}', filter_params).fetchone()
        tot_num = _safe_float(tot_num_res[0]) if (tot_num_res and tot_num_res[0]) else 1.0
        share1 = (num1 / max(1.0, tot_num)) * 100.0
        card5.percentage = round(min(100.0, max(0.0, share1)), 1)
        card5.metric_description = f"{card5.percentage:.1f}% of total {primary_num.replace('_', ' ')}"
    else:
        card5.title = f"{active_gauge1_tab} Share of {eval_cat.replace('_', ' ').title()} (QTD)"
        card5.center_label = "Share"
        share1 = (denom1 / max(1.0, float(filtered_records))) * 100.0
        card5.percentage = round(min(100.0, max(0.0, share1)), 1)
        card5.metric_description = f"{card5.percentage:.1f}% of catalog ({int(denom1):,} of {int(filtered_records):,} records)"

    card5.numerator = num1 if (target_col or primary_num) else denom1
    card5.denominator = denom1 if (target_col or primary_num) else float(filtered_records)

    # -------------------------------------------------------------------------
    # CARD 6: Secondary Dimension / Geographic Performance (Donut Gauge)
    # -------------------------------------------------------------------------
    card6 = Card6EngineeringPerformance()
    loc_rows = conn.execute(f"""
        SELECT COALESCE(NULLIF(CAST({_sanitize_col(secondary_cat)} AS VARCHAR), ''), 'General') as loc_val,
               COUNT(*) as loc_cnt
        FROM "{v_name}"
        WHERE {filter_sql} AND {_sanitize_col(secondary_cat)} IS NOT NULL
        GROUP BY 1
        ORDER BY 2 DESC
        LIMIT 5
    """, filter_params).fetchall()
    distinct_locs = [r[0] for r in loc_rows] if loc_rows else ["General"]
    card6.available_tabs = distinct_locs
    active_loc = filter_ctx.location if (filter_ctx and filter_ctx.location and filter_ctx.location in distinct_locs) else distinct_locs[0]
    card6.active_tab = active_loc

    loc_escaped = active_loc.replace("'", "''")
    loc_stats = conn.execute(f"""
        SELECT 
            COUNT(*) as denom,
            {metric_expr} as num
        FROM "{v_name}"
        WHERE {filter_sql} AND COALESCE(NULLIF(CAST({_sanitize_col(secondary_cat)} AS VARCHAR), ''), 'General') = '{loc_escaped}'
    """, filter_params).fetchone()

    denom2 = _safe_float(loc_stats[0]) if (loc_stats and loc_stats[0]) else 0.0
    num2 = _safe_float(loc_stats[1]) if (loc_stats and loc_stats[1]) else 0.0

    if target_col:
        card6.title = f"{secondary_cat.replace('_', ' ').title()} - {target_col.replace('_', ' ').title()} Rate (QTD)"
        card6.center_label = "Rate"
        rate2 = (num2 / denom2) * 100.0 if denom2 > 0 else 0.0
        card6.percentage = round(min(100.0, max(0.0, rate2)), 1)
        card6.benchmark_comparison = f"Event rate in {active_loc}: {card6.percentage:.1f}% ({int(num2):,} of {int(denom2):,})"
        card6.numerator = num2
        card6.denominator = denom2
    elif primary_num:
        card6.title = f"{secondary_cat.replace('_', ' ').title()} - {primary_num.replace('_', ' ').title()} Contribution (QTD)"
        card6.center_label = "Share"
        tot_num_res = conn.execute(f'SELECT {metric_expr} FROM "{v_name}" WHERE {filter_sql}', filter_params).fetchone()
        tot_num = _safe_float(tot_num_res[0]) if (tot_num_res and tot_num_res[0]) else 1.0
        loc_share = (num2 / max(1.0, tot_num)) * 100.0
        card6.percentage = round(min(100.0, max(0.0, loc_share)), 1)
        card6.benchmark_comparison = f"Contribution from {active_loc}: {card6.percentage:.1f}%"
        card6.numerator = num2
        card6.denominator = tot_num
    else:
        card6.title = f"{secondary_cat.replace('_', ' ').title()} Concentration (QTD)"
        card6.center_label = "Share"
        loc_share = (denom2 / max(1.0, float(filtered_records))) * 100.0
        card6.percentage = round(min(100.0, max(0.0, loc_share)), 1)
        card6.benchmark_comparison = f"Distribution in {active_loc}: {card6.percentage:.1f}% ({int(denom2):,} records)"
        card6.numerator = denom2
        card6.denominator = float(filtered_records)

    # -------------------------------------------------------------------------
    # Complete Payload Assembly
    # -------------------------------------------------------------------------
    comp_time = (time.perf_counter() - start_time) * 1000.0

    return DashboardAnalyticsPayload(
        dataset_id=dataset_id,
        dataset_name=dataset_name or v_name,
        project_id=project_id,
        readiness_status=readiness,
        status_explanation=status_msg,
        filter_context=filter_ctx or FilterContext(),
        quality_summary=DataQualitySummary(
            total_records=total_records,
            filtered_records=filtered_records,
            null_value_rate=round((total_records - filtered_records) / max(1, total_records) * 100, 2),
            date_field_identified=date_col,
            date_range_min=date_min,
            date_range_max=date_max,
            warnings=warnings,
        ),
        card1_quarter_to_quarter=card1,
        card2_year_over_year=card2,
        card3_top_bottom_teams=card3,
        card4_quarterly_performance=card4,
        card5_meetings_attended=card5,
        card6_engineering_performance=card6,
        computation_time_ms=round(comp_time, 2),
    )


def get_filter_dimensions(
    dataset_id: str,
    filter_ctx: Optional[FilterContext] = None,
) -> FilterDimensions:
    """Extract distinct dimension values for dynamic cascading filters with actual record counts."""
    v_name = registry.ensure_view(dataset_id)
    conn = registry.get_cursor()
    roles = _detect_schema_roles(conn, v_name)

    date_col = roles["date_col"]
    primary_cat = roles["primary_cat"]
    secondary_cat = roles["secondary_cat"]
    all_cols = roles.get("all_cols", [])
    types = roles.get("types", {})

    cat_candidates = [
        c for c in all_cols
        if any(k in types.get(c, "") for k in ["varchar", "string", "text", "char"])
    ]

    # Resolve dimensions if specified
    if filter_ctx:
        if filter_ctx.primary_col and filter_ctx.primary_col in all_cols:
            primary_cat = filter_ctx.primary_col
        elif filter_ctx.team and filter_ctx.team.lower() not in ("all", "all teams / categories", "all categories"):
            resolved = _resolve_column_for_value(conn, v_name, filter_ctx.team, primary_cat, cat_candidates)
            if resolved:
                primary_cat = resolved
                roles["primary_cat"] = resolved

        if filter_ctx.secondary_col and filter_ctx.secondary_col in all_cols:
            secondary_cat = filter_ctx.secondary_col
        elif filter_ctx.location and filter_ctx.location.lower() not in ("all", "all locations"):
            resolved = _resolve_column_for_value(conn, v_name, filter_ctx.location, secondary_cat, cat_candidates)
            if resolved:
                secondary_cat = resolved
                roles["secondary_cat"] = resolved

    # Extract distinct teams/categories (limit 30)
    # If date filters exist in filter_ctx, filter teams to matching records
    date_where_clauses: List[str] = []
    date_where_params: List[Any] = []
    if date_col and filter_ctx:
        parse_expr = _build_date_parse_expr(date_col)
        if filter_ctx.year:
            date_where_clauses.append(f'year({parse_expr}) = ?')
            date_where_params.append(int(filter_ctx.year))
        if filter_ctx.quarter:
            q_str = str(filter_ctx.quarter).upper().replace("Q", "").strip()
            if q_str.isdigit() and int(q_str) in (1, 2, 3, 4):
                date_where_clauses.append(f'quarter({parse_expr}) = ?')
                date_where_params.append(int(q_str))

    date_where_sql = ("WHERE " + " AND ".join(date_where_clauses)) if date_where_clauses else ""

    teams: List[str] = []
    if primary_cat and primary_cat in all_cols:
        teams = [
            str(r[0]) for r in conn.execute(
                f'SELECT DISTINCT COALESCE(NULLIF(CAST({_sanitize_col(primary_cat)} AS VARCHAR), \'\'), \'Unknown\') '
                f'FROM "{v_name}" {date_where_sql} {"AND" if date_where_sql else "WHERE"} {_sanitize_col(primary_cat)} IS NOT NULL LIMIT 30',
                date_where_params
            ).fetchall()
            if r and len(r) > 0 and r[0] is not None
        ]
        if not teams:
            teams = [
                str(r[0]) for r in conn.execute(
                    f'SELECT DISTINCT COALESCE(NULLIF(CAST({_sanitize_col(primary_cat)} AS VARCHAR), \'\'), \'Unknown\') '
                    f'FROM "{v_name}" WHERE {_sanitize_col(primary_cat)} IS NOT NULL LIMIT 30'
                ).fetchall()
                if r and len(r) > 0 and r[0] is not None
            ]

    # Cascading locations: if team is selected, get locations for that team!
    loc_where_clauses = list(date_where_clauses)
    loc_where_params = list(date_where_params)
    if filter_ctx and filter_ctx.team and filter_ctx.team.lower() not in ("all", "all teams / categories", "all categories") and primary_cat in all_cols:
        loc_where_clauses.append(f"COALESCE(NULLIF(CAST({_sanitize_col(primary_cat)} AS VARCHAR), ''), 'Unknown') = ?")
        loc_where_params.append(filter_ctx.team)

    loc_where_sql = ("WHERE " + " AND ".join(loc_where_clauses)) if loc_where_clauses else ""
    locations: List[str] = []
    if secondary_cat and secondary_cat in all_cols:
        locations = [
            str(r[0]) for r in conn.execute(
                f'SELECT DISTINCT COALESCE(NULLIF(CAST({_sanitize_col(secondary_cat)} AS VARCHAR), \'\'), \'General\') '
                f'FROM "{v_name}" {loc_where_sql} {"AND" if loc_where_sql else "WHERE"} {_sanitize_col(secondary_cat)} IS NOT NULL LIMIT 30',
                loc_where_params
            ).fetchall()
            if r and len(r) > 0 and r[0] is not None
        ]
        if not locations:
            locations = [
                str(r[0]) for r in conn.execute(
                    f'SELECT DISTINCT COALESCE(NULLIF(CAST({_sanitize_col(secondary_cat)} AS VARCHAR), \'\'), \'General\') '
                    f'FROM "{v_name}" WHERE {_sanitize_col(secondary_cat)} IS NOT NULL LIMIT 30'
                ).fetchall()
                if r and len(r) > 0 and r[0] is not None
            ]

    years: List[int] = []
    quarters: List[str] = ["Q1", "Q2", "Q3", "Q4"]
    date_min = None
    date_max = None

    if date_col:
        date_parse_expr = _build_date_parse_expr(date_col)
        try:
            d_res = conn.execute(
                f'SELECT min(CAST({date_parse_expr} AS VARCHAR)), max(CAST({date_parse_expr} AS VARCHAR)) '
                f'FROM "{v_name}" WHERE {date_parse_expr} IS NOT NULL'
            ).fetchone()
            if d_res and len(d_res) >= 2 and d_res[0] is not None and d_res[1] is not None:
                date_min, date_max = str(d_res[0]), str(d_res[1])

            yr_res = conn.execute(
                f'SELECT DISTINCT year({date_parse_expr}) '
                f'FROM "{v_name}" WHERE {date_parse_expr} IS NOT NULL ORDER BY 1'
            ).fetchall()
            years = [int(r[0]) for r in yr_res if r and len(r) > 0 and r[0] is not None]
        except Exception as exc:
            logger.warning("Could not extract filter years: %s", exc)

    # Compute row counts under filter_ctx
    tot_row = conn.execute(f'SELECT count(*) FROM "{v_name}"').fetchone()
    total_records = int(tot_row[0]) if (tot_row and len(tot_row) > 0) else 0

    filter_sql, filter_params = _build_filter_sql(filter_ctx, roles, conn, v_name)
    fil_row = conn.execute(f'SELECT count(*) FROM "{v_name}" WHERE {filter_sql}', filter_params).fetchone()
    filtered_records = int(fil_row[0]) if (fil_row and len(fil_row) > 0) else 0

    return FilterDimensions(
        years=years,
        quarters=quarters,
        teams=teams,
        locations=locations,
        date_min=date_min,
        date_max=date_max,
        primary_dim_col=primary_cat,
        primary_dim_label=primary_cat.replace('_', ' ').title() if primary_cat else "Category",
        secondary_dim_col=secondary_cat,
        secondary_dim_label=secondary_cat.replace('_', ' ').title() if secondary_cat else "Location",
        total_records=total_records,
        filtered_records=filtered_records,
    )


def get_drilldown_records(req: DrilldownRequest) -> DrilldownResponse:
    """Retrieve verified underlying records for drill-down context."""
    v_name = registry.ensure_view(req.dataset_id)
    conn = registry.get_cursor()
    roles = _detect_schema_roles(conn, v_name)

    filter_sql, filter_params = _build_filter_sql(req.filter_context, roles, conn, v_name)
    primary_cat = roles["primary_cat"]
    secondary_cat = roles["secondary_cat"]
    extra_clauses: List[str] = []
    extra_params: List[Any] = []

    description = f"Drilldown for {req.card_id}"

    if req.category_tab and primary_cat:
        extra_clauses.append(f"COALESCE(NULLIF(CAST({_sanitize_col(primary_cat)} AS VARCHAR), ''), 'Unknown') = ?")
        extra_params.append(req.category_tab)
        description = f"Underlying records for {primary_cat} = '{req.category_tab}'"

    if req.location_tab and secondary_cat:
        extra_clauses.append(f"COALESCE(NULLIF(CAST({_sanitize_col(secondary_cat)} AS VARCHAR), ''), 'General') = ?")
        extra_params.append(req.location_tab)
        description += f" in {secondary_cat} = '{req.location_tab}'"

    combined_where = filter_sql
    if extra_clauses:
        combined_where = f"({filter_sql}) AND {' AND '.join(extra_clauses)}"
    all_params = filter_params + extra_params

    total_records = conn.execute(
        f'SELECT COUNT(*) FROM "{v_name}" WHERE {combined_where}',
        all_params
    ).fetchone()[0]

    offset = (req.page - 1) * req.page_size
    df = conn.execute(
        f'SELECT * FROM "{v_name}" WHERE {combined_where} LIMIT ? OFFSET ?',
        all_params + [req.page_size, offset]
    ).df()

    columns = list(df.columns)
    rows = json.loads(df.fillna("").to_json(orient="records", date_format="iso"))

    return DrilldownResponse(
        card_id=req.card_id,
        filter_description=description,
        total_matching_records=int(total_records),
        page=req.page,
        page_size=req.page_size,
        columns=columns,
        rows=rows,
    )

