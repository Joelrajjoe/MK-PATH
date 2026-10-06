"""DuckDB registration + query helpers for ingested datasets (Phase 4).

Each dataset is registered as a uniquely-named view (ds_<dataset_id>) over
its normalized Parquet file, so registrations can never collide across
uploads. All queries go through DuckDB - deterministic, zero LLM.
"""
import threading
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Tuple

import duckdb

_lock = threading.Lock()
_conn: Any = None


def get_conn() -> duckdb.DuckDBPyConnection:
    """Lazily-created in-memory DuckDB used for dataset registration."""
    global _conn
    with _lock:
        if _conn is None:
            _conn = duckdb.connect(database=":memory:")
        return _conn


def view_name(dataset_id: str) -> str:
    """Server-generated, collision-free view name (uuid hex is safe)."""
    return f"ds_{dataset_id}"


def _quote_literal(value: str) -> str:
    return value.replace("'", "''")


def register(dataset_id: str, parquet_path: str) -> str:
    """Register a normalized Parquet file as a DuckDB view. Lazy (view)."""
    conn = get_conn()
    view = view_name(dataset_id)
    conn.execute(
        f'CREATE OR REPLACE VIEW "{view}" AS '
        f"SELECT * FROM read_parquet('{_quote_literal(parquet_path)}')"
    )
    return view


def unregister(dataset_id: str) -> None:
    conn = get_conn()
    try:
        conn.execute(f'DROP VIEW IF EXISTS "{view_name(dataset_id)}"')
    except duckdb.Error:
        pass


def _jsonable(value: Any) -> Any:
    """Convert DuckDB/Arrow values into JSON-serializable Python values."""
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, bytes):
        return f"<{len(value)} bytes>"
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    if isinstance(value, dict):
        return {k: _jsonable(v) for k, v in value.items()}
    return value


def preview(dataset_id: str, limit: int) -> Dict[str, Any]:
    """First `limit` rows of a registered dataset (JSON-safe)."""
    conn = get_conn()
    view = view_name(dataset_id)
    result = conn.execute(f'SELECT * FROM "{view}" LIMIT {int(limit)}')
    table = result.to_arrow_table()
    columns = list(table.schema.names)
    rows = [{k: _jsonable(v) for k, v in row.items()} for row in table.to_pylist()]
    return {"columns": columns, "rows": rows, "row_count_returned": len(rows)}


def describe(dataset_id: str) -> List[Dict[str, Any]]:
    """Column name/type/nullability via DuckDB DESCRIBE."""
    conn = get_conn()
    view = view_name(dataset_id)
    result = conn.execute(f'DESCRIBE "{view}"')
    cols = [d[0] for d in result.description]
    out = []
    for row in result.fetchall():
        rec = dict(zip(cols, row))
        out.append(
            {
                "name": rec.get("column_name"),
                "type": rec.get("column_type"),
                "nullable": str(rec.get("null", "")).upper() in {"YES", "Y", "TRUE", "1"},
            }
        )
    return out
