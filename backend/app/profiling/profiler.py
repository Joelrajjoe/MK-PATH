"""MK-Path deterministic profiling engine (Phase 5) - ZERO LLM.

Spec section 7: the LLM must NOT perform calculations. Every number in the
DataQualityReport is computed deterministically with DuckDB, PyArrow and
Pandas over the dataset's normalized Parquet file.

Quality score formula (documented, reproducible):
    score  = 100
            - min(40, 40 * overall_missing_ratio)
            - min(20, 20 * duplicate_row_ratio)
            - min(20, 10 * number_of_constant_columns)
            - min(20, 10 * high_severity_issues)
            - min(10,  5 * medium_severity_issues)
            floor 0, one decimal
    grade  = A >= 90 | B >= 80 | C >= 70 | D >= 60 | F < 60
"""
import math
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq

ENGINE_TAG = "deterministic:v1:duckdb+pyarrow+pandas"

# Thresholds (deterministic constants - documented in docs/DATA_INGESTION.md)
CATEGORICAL_MAX_UNIQUE = 50
TEXT_AVG_LEN = 50.0
TEXT_UNIQ_RATIO = 0.9
ID_UNIQ_RATIO = 0.95
LEAKAGE_CORR = 0.98
CORRELATION_REPORT_MIN = 0.7
MAX_PAIRWISE_COLUMNS = 20
DATE_NAME_RE = re.compile(
    r"(^|_)(date|time|datetime|timestamp|ts|day|month|year)(_|$)|_at$|_at_|_dt$",
    re.IGNORECASE,
)
TARGET_NAME_RE = re.compile(
    r"(^|_)(target|label|class|churn|outcome|response|result|price|amount|"
    r"sales|revenue|y)(_|$)",
    re.IGNORECASE,
)
ID_NAME_RE = re.compile(r"(^|_)(id|uuid|guid|key|code)(_|$)", re.IGNORECASE)
LEAK_NAME_RE = re.compile(
    r"(^|_)(leak|leaked|future|after|forward|next_|tomorrow|would_be|post_)(_|$)",
    re.IGNORECASE,
)


def _round(value: Optional[float], digits: int = 4) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    return round(float(value), digits)


def _grade(score: float) -> str:
    if score >= 90:
        return "A"
    if score >= 80:
        return "B"
    if score >= 70:
        return "C"
    if score >= 60:
        return "D"
    return "F"


def _arrow_kind(pa_type: pa.DataType) -> str:
    if pa.types.is_boolean(pa_type):
        return "boolean"
    if pa.types.is_integer(pa_type) or pa.types.is_floating(pa_type):
        return "numeric"
    if pa.types.is_timestamp(pa_type) or pa.types.is_date(pa_type) or pa.types.is_time(pa_type):
        return "datetime"
    if pa.types.is_string(pa_type) or pa.types.is_large_string(pa_type):
        return "string"
    if pa.types.is_decimal(pa_type):
        return "numeric"
    return "other"


def build_quality_report(dataset: Dict[str, Any]) -> Dict[str, Any]:
    """Compute the full DataQualityReport. Synchronous; run in a worker thread.

    `dataset` is the MongoDB dataset document (needs normalized_path,
    dataset_id, original_filename).
    """
    dataset_id = dataset.get("dataset_id", "")
    path = dataset.get("normalized_path") or ""
    warnings: List[str] = []

    pf = pq.ParquetFile(path)
    arrow_schema = pf.schema_arrow
    fields = list(arrow_schema)
    row_count = pf.metadata.num_rows
    column_count = len(fields)

    conn = duckdb.connect(database=":memory:")
    lit = path.replace("'", "''")
    conn.execute(f'CREATE VIEW src AS SELECT * FROM read_parquet(\'{lit}\')')

    issues: List[Dict[str, Any]] = []
    recommendations: List[str] = []
    schema_entries: List[Dict[str, Any]] = []
    statistics: Dict[str, Any] = {
        "row_count": row_count,
        "column_count": column_count,
        "numeric": {},
        "correlations": [],
    }

    roles: Dict[str, List[str]] = {
        "numeric_columns": [],
        "categorical_columns": [],
        "boolean_columns": [],
        "text_columns": [],
        "datetime_columns": [],
        "potential_ids": [],
        "potential_targets": [],
        "leakage_candidates": [],
        "constant_columns": [],
        "date_time_detected": [],
    }

    if row_count == 0:
        issues.append(
            {
                "code": "EMPTY_DATASET",
                "severity": "high",
                "column": None,
                "message": "Dataset has zero rows.",
            }
        )
        recommendations.append("The dataset is empty; re-upload a file with data rows.")

    total_missing = 0
    col_meta: Dict[str, Dict[str, Any]] = {}

    for field in fields:
        col = field.name
        quoted = '"' + col.replace('"', '""') + '"'
        kind = _arrow_kind(field.type)

        missing, uniq, non_null = conn.execute(
            f"SELECT count(*) - count({quoted}), count(DISTINCT {quoted}), "
            f"count({quoted}) FROM src"
        ).fetchone()

        missing = int(missing)
        uniq = int(uniq)
        non_null = int(non_null)
        total_missing += missing
        missing_pct = round(100.0 * missing / row_count, 2) if row_count else 0.0
        cardinality = round(uniq / row_count, 4) if row_count else 0.0
        is_constant = non_null > 0 and uniq == 1

        entry: Dict[str, Any] = {
            "name": col,
            "type": str(field.type),
            "kind": kind,
            "nullable": bool(field.nullable),
            "missing_count": missing,
            "missing_pct": missing_pct,
            "unique_count": uniq,
            "cardinality_ratio": cardinality,
            "constant": is_constant,
        }

        # --- role classification (deterministic) ---
        role = None
        if kind == "boolean":
            role = "boolean"
            roles["boolean_columns"].append(col)
        elif kind == "datetime":
            role = "datetime"
            roles["datetime_columns"].append(col)
            roles["date_time_detected"].append(col)
        elif kind == "numeric":
            role = "numeric"
            roles["numeric_columns"].append(col)
        elif kind == "string":
            avg_len = None
            if non_null:
                avg_len = conn.execute(
                    f"SELECT avg(length({quoted})) FROM src WHERE {quoted} IS NOT NULL"
                ).fetchone()[0]
            avg_len = float(avg_len) if avg_len is not None else 0.0
            entry["avg_length"] = round(avg_len, 2)
            if uniq <= CATEGORICAL_MAX_UNIQUE:
                role = "categorical"
                roles["categorical_columns"].append(col)
            elif avg_len >= TEXT_AVG_LEN or (
                cardinality > TEXT_UNIQ_RATIO and uniq > CATEGORICAL_MAX_UNIQUE
            ):
                role = "text"
                roles["text_columns"].append(col)
            else:
                role = "categorical"
                roles["categorical_columns"].append(col)
        else:
            role = "other"

        # Date/time detection for strings (name pattern + sample parse).
        if kind == "string" and DATE_NAME_RE.search(col) and non_null:
            sample = [
                r[0]
                for r in conn.execute(
                    f"SELECT {quoted} FROM src WHERE {quoted} IS NOT NULL LIMIT 1000"
                ).fetchall()
            ]
            import pandas as pd

            parsed = pd.to_datetime(pd.Series(sample), errors="coerce", format="mixed")
            if len(sample) and float(parsed.notna().mean()) >= 0.9:
                role = "datetime"
                roles["datetime_columns"].append(col)
                roles["date_time_detected"].append(col)
                # remove the earlier string-based classification: a column has
                # exactly one role.
                for bucket in ("categorical_columns", "text_columns"):
                    if col in roles[bucket]:
                        roles[bucket].remove(col)
                entry["kind"] = "datetime"
                warnings.append(
                    f"Column '{col}' detected as date/time by name pattern + parse."
                )
                entry["date_time_inferred"] = True

        # Potential ID detection (never for datetime columns: a date being
        # unique in a small table is coincidence, not identifier semantics).
        if role != "datetime":
            if row_count and uniq == row_count and row_count > 1:
                roles["potential_ids"].append(col)
                entry["potential_id"] = True
            elif kind == "string" and ID_NAME_RE.search(col) and cardinality >= ID_UNIQ_RATIO:
                roles["potential_ids"].append(col)
                entry["potential_id"] = True

        # Potential target candidates (name pattern or binary column).
        if role != "datetime" and TARGET_NAME_RE.search(col) and kind in ("numeric", "string", "boolean"):
            roles["potential_targets"].append(col)
            entry["potential_target"] = "name pattern matches target/label semantics"
        elif (
            role != "datetime"
            and uniq == 2
            and non_null == row_count
            and col not in roles["potential_ids"]
            and row_count > 1
        ):
            roles["potential_targets"].append(col)
            entry["potential_target"] = "binary column (possible classification label)"

        # Leakage by name.
        if LEAK_NAME_RE.search(col):
            roles["leakage_candidates"].append(col)
            issues.append(
                {
                    "code": "POTENTIAL_LEAKAGE",
                    "severity": "high",
                    "column": col,
                    "message": f"Column name '{col}' suggests temporal/target leakage.",
                }
            )

        if is_constant and row_count:
            roles["constant_columns"].append(col)
            issues.append(
                {
                    "code": "CONSTANT_COLUMN",
                    "severity": "medium",
                    "column": col,
                    "message": f"Column '{col}' is constant (zero information).",
                }
            )
        if missing and row_count:
            severity = "high" if missing_pct > 50 else "medium"
            issues.append(
                {
                    "code": "MISSING_VALUES",
                    "severity": severity,
                    "column": col,
                    "message": f"Column '{col}' is {missing_pct}% missing ({missing} rows).",
                }
            )
            if missing_pct > 50:
                recommendations.append(
                    f"Column '{col}' exceeds 50% missing - drop it or impute with evidence."
                )
            elif missing:
                recommendations.append(
                    f"Column '{col}' has {missing} missing values - impute or exclude them."
                )

        # --- numeric statistics + outliers ---
        if kind == "numeric":
            stats_row = conn.execute(
                f"SELECT count({quoted}), min({quoted}), max({quoted}), "
                f"avg({quoted}), stddev_samp({quoted}), "
                f"median({quoted}), quantile_cont({quoted}, 0.25), "
                f"quantile_cont({quoted}, 0.75) FROM src"
            ).fetchone()
            n, mn, mx, mean, std, med, q1, q3 = stats_row
            outliers_low = outliers_high = 0
            if q1 is not None and q3 is not None:
                iqr = float(q3) - float(q1)
                lo = float(q1) - 1.5 * iqr
                hi = float(q3) + 1.5 * iqr
                row = conn.execute(
                    f"SELECT count(*) FILTER (WHERE {quoted} < {float(lo)}), "
                    f"count(*) FILTER (WHERE {quoted} > {float(hi)}) "
                    f"FROM src WHERE {quoted} IS NOT NULL"
                ).fetchone()
                outliers_low, outliers_high = int(row[0]), int(row[1])
            num_stats = {
                "count": int(n),
                "min": _round(mn, 6),
                "max": _round(mx, 6),
                "mean": _round(mean, 6),
                "std": _round(std, 6),
                "median": _round(med, 6),
                "q1": _round(q1, 6),
                "q3": _round(q3, 6),
                "outliers_low": int(outliers_low),
                "outliers_high": int(outliers_high),
                "outliers_present": bool(outliers_low or outliers_high),
            }
            statistics["numeric"][col] = num_stats
            entry["statistics"] = num_stats
            if num_stats["outliers_present"]:
                issues.append(
                    {
                        "code": "OUTLIERS_PRESENT",
                        "severity": "low",
                        "column": col,
                        "message": (
                            f"Column '{col}' has {outliers_low + outliers_high} "
                            "IQR-based outlier(s)."
                        ),
                    }
                )

        schema_entries.append(entry)

    # --- duplicate rows (exact) ---
    distinct_rows = conn.execute("SELECT count(*) FROM (SELECT DISTINCT * FROM src)").fetchone()[0]
    duplicate_rows = int(row_count - distinct_rows)
    duplicate_ratio = round(duplicate_rows / row_count, 4) if row_count else 0.0
    statistics["duplicate_rows"] = duplicate_rows
    statistics["duplicate_ratio"] = duplicate_ratio
    if duplicate_rows > 0:
        issues.append(
            {
                "code": "DUPLICATE_ROWS",
                "severity": "medium",
                "column": None,
                "message": f"{duplicate_rows} fully duplicated row(s) detected.",
            }
        )
        recommendations.append(f"Remove {duplicate_rows} duplicate row(s) before modeling.")

    overall_missing_ratio = round(total_missing / (row_count * column_count), 4) if (
        row_count and column_count
    ) else 0.0
    statistics["overall_missing_ratio"] = overall_missing_ratio
    statistics["overall_missing_cells"] = int(total_missing)

    # --- correlation summary + leakage-by-correlation ---
    numeric_cols = roles["numeric_columns"]
    if len(numeric_cols) >= 2:
        pairwise = numeric_cols[:MAX_PAIRWISE_COLUMNS]
        if len(numeric_cols) > MAX_PAIRWISE_COLUMNS:
            warnings.append(
                f"Correlation computed on first {MAX_PAIRWISE_COLUMNS} numeric columns."
            )
        pairs: List[Dict[str, Any]] = []
        for i in range(len(pairwise)):
            for j in range(i + 1, len(pairwise)):
                a, b = pairwise[i], pairwise[j]
                qa = '"' + a.replace('"', '""') + '"'
                qb = '"' + b.replace('"', '""') + '"'
                r = conn.execute(f"SELECT corr({qa}, {qb}) FROM src").fetchone()[0]
                r = _round(r, 4)
                if r is None:
                    continue
                if abs(r) >= CORRELATION_REPORT_MIN:
                    pairs.append({"columns": [a, b], "pearson": r})
                # Leakage: a NON-target column that correlates perfectly with a
                # target candidate. Pairs where BOTH are target candidates are
                # skipped (we cannot tell which one is the leak, and both are
                # already reported as candidates).
                a_target = a in roles["potential_targets"]
                b_target = b in roles["potential_targets"]
                if abs(r) >= LEAKAGE_CORR and a_target != b_target:
                    other = a if b_target else b
                    if other not in roles["leakage_candidates"]:
                        roles["leakage_candidates"].append(other)
                        issues.append(
                            {
                                "code": "POTENTIAL_LEAKAGE",
                                "severity": "high",
                                "column": other,
                                "message": (
                                    f"'{other}' correlates at {r} with target "
                                    "candidate - possible target leakage."
                                ),
                            }
                        )
        pairs.sort(key=lambda p: -abs(p["pearson"]))
        statistics["correlations"] = pairs[:50]

    if roles["leakage_candidates"]:
        recommendations.append(
            "Investigate leakage candidates before training: "
            + ", ".join(sorted(set(roles["leakage_candidates"])))
            + "."
        )
    if not roles["potential_ids"]:
        recommendations.append(
            "No unique identifier column detected - assign stable keys upstream if needed."
        )

    conn.close()

    # --- deterministic quality score (no LLM, ever) ---
    high_issues = sum(1 for i in issues if i["severity"] == "high")
    medium_issues = sum(1 for i in issues if i["severity"] == "medium")
    score = 100.0
    score -= min(40.0, 40.0 * overall_missing_ratio)
    score -= min(20.0, 20.0 * duplicate_ratio)
    score -= min(20.0, 10.0 * len(roles["constant_columns"]))
    score -= min(20.0, 10.0 * high_issues)
    score -= min(10.0, 5.0 * medium_issues)
    score = max(0.0, round(score, 1))

    if duplicate_rows and "Remove duplicate rows" not in " ".join(recommendations):
        pass  # recommendation already appended above

    return {
        "dataset_id": dataset_id,
        "original_filename": dataset.get("original_filename"),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "engine": ENGINE_TAG,
        "quality_score": score,
        "quality_grade": _grade(score),
        "issues": issues,
        "warnings": warnings,
        "statistics": statistics,
        "schema": schema_entries,
        "recommendations": recommendations,
        "roles": roles,
    }


def profile_summary(report: Dict[str, Any]) -> Dict[str, Any]:
    """Compact summary stored in MongoDB (raw report stays on E:)."""
    issues = report.get("issues", [])
    return {
        "quality_score": report["quality_score"],
        "quality_grade": report["quality_grade"],
        "engine": report["engine"],
        "generated_at": report["generated_at"],
        "issue_count": len(issues),
        "issues_by_severity": {
            sev: sum(1 for i in issues if i["severity"] == sev)
            for sev in ("high", "medium", "low")
        },
        "top_issues": issues[:10],
        "recommendation_count": len(report.get("recommendations", [])),
        "duplicate_rows": report["statistics"].get("duplicate_rows", 0),
        "overall_missing_ratio": report["statistics"].get(
            "overall_missing_ratio", 0.0
        ),
        "row_count": report["statistics"].get("row_count", 0),
        "column_count": report["statistics"].get("column_count", 0),
    }
