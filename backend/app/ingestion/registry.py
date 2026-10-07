"""DuckDB registration + query helpers for ingested datasets (Phase 4).

Each dataset is registered as a uniquely-named view (ds_<dataset_id>) over
its normalized Parquet file, so registrations can never collide across
uploads. All queries go through DuckDB - deterministic, zero LLM.
"""
import threading
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

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
    return Path(value).as_posix().replace("'", "''")


def register(dataset_id: str, parquet_path: str) -> str:
    """Register a normalized Parquet file as a DuckDB view. Lazy (view)."""
    if not dataset_id:
        raise ValueError("dataset_id must be provided and non-empty")
    conn = get_conn()
    view = view_name(dataset_id)
    quoted = _quote_literal(parquet_path)
    conn.execute(
        f'CREATE OR REPLACE VIEW "{view}" AS '
        f"SELECT * FROM read_parquet('{quoted}')"
    )
    return view


def ensure_view(dataset_id: str, parquet_path: Optional[str] = None) -> str:
    """Ensure DuckDB view exists for dataset_id, dynamically registering if needed."""
    if not dataset_id:
        raise ValueError("dataset_id must be provided and non-empty")
    conn = get_conn()
    view = view_name(dataset_id)
    try:
        conn.execute(f'SELECT 1 FROM "{view}" LIMIT 1')
        return view
    except Exception:
        pass

    path_to_use: Optional[str] = None
    if parquet_path and Path(parquet_path).exists():
        path_to_use = str(parquet_path)
    else:
        from ..config import settings
        # Search DATA_DIR
        candidates = list(settings.DATA_DIR.glob(f"**/{dataset_id}.parquet"))
        if not candidates:
            # Search DATASETS_DIR
            candidates = list(settings.DATASETS_DIR.glob(f"**/{dataset_id}.parquet"))
        if candidates:
            path_to_use = str(candidates[0])
        else:
            # Check metadata file
            meta_path = settings.DATA_DIR / "metadata" / "datasets.json"
            if meta_path.exists():
                import json
                try:
                    with open(meta_path, "r", encoding="utf-8") as f:
                        docs = json.load(f)
                        for d in docs:
                            if d.get("dataset_id") == dataset_id:
                                norm = d.get("normalized_path")
                                if norm and Path(norm).exists():
                                    path_to_use = str(norm)
                                    break
                except Exception:
                    pass

    if not path_to_use or not Path(path_to_use).exists():
        raise FileNotFoundError(
            f"No parquet file found for dataset '{dataset_id}' on disk."
        )

    return register(dataset_id, path_to_use)


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


def preview(dataset_id: str, limit: int, parquet_path: Optional[str] = None) -> Dict[str, Any]:
    """First `limit` rows of a registered dataset (JSON-safe)."""
    ensure_view(dataset_id, parquet_path)
    conn = get_conn()
    view = view_name(dataset_id)
    result = conn.execute(f'SELECT * FROM "{view}" LIMIT {int(limit)}')
    if hasattr(result, "arrow"):
        table = result.arrow()
        columns = list(table.schema.names)
        rows = [{k: _jsonable(v) for k, v in row.items()} for row in table.to_pylist()]
    elif hasattr(result, "fetch_arrow_table"):
        table = result.fetch_arrow_table()
        columns = list(table.schema.names)
        rows = [{k: _jsonable(v) for k, v in row.items()} for row in table.to_pylist()]
    else:
        df = result.df()
        columns = list(df.columns)
        rows = [{k: _jsonable(v) for k, v in row.items()} for row in df.to_dict(orient="records")]
    return {"columns": columns, "rows": rows, "row_count_returned": len(rows)}


def describe(dataset_id: str, parquet_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Column name/type/nullability via DuckDB DESCRIBE."""
    ensure_view(dataset_id, parquet_path)
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
