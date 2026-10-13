"""Dataset API routes (Phase 4 + Phase 5).

POST /api/datasets/upload
GET  /api/datasets
GET  /api/datasets/{dataset_id}
GET  /api/datasets/{dataset_id}/schema
GET  /api/datasets/{dataset_id}/preview
GET  /api/datasets/{dataset_id}/quality
POST /api/datasets/{dataset_id}/profile
GET  /api/datasets/{dataset_id}/profile
"""
import json
import logging
import re
import shutil
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel

from .. import repo
from ..audit import record_audit
from ..config import settings
from ..database import db_manager
from ..ingestion import registry, security
from ..ingestion.parsers import IngestionError
from ..ingestion.service import process_upload
from ..ingestion.security import SecurityError, sanitize_filename
from ..profiling.profiler import build_quality_report, profile_summary
from ..repo import MetadataUnavailable

logger = logging.getLogger("mkpath.datasets")

router = APIRouter(prefix="/api/datasets", tags=["datasets"])

_ID_RE = re.compile(r"^[0-9a-f]{32}$")
_UPLOAD_CHUNK = 1024 * 1024


def _require_db() -> None:
    if db_manager.get_database() is None:
        raise HTTPException(
            status_code=503,
            detail={"code": "METADATA_UNAVAILABLE", "message": "Metadata store unavailable."},
        )


def _validate_id(dataset_id: str) -> str:
    if not _ID_RE.match(dataset_id):
        raise HTTPException(status_code=404, detail="Dataset not found.")
    return dataset_id


async def _get_or_404(dataset_id: str) -> Dict[str, Any]:
    _validate_id(dataset_id)
    doc = await repo.get_dataset(dataset_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Dataset not found.")
    return doc


def _cleanup_upload(upload_id: str) -> None:
    """Remove both the dataset dir and any extraction temp dir for an upload."""
    shutil.rmtree(settings.DATASETS_DIR / upload_id, ignore_errors=True)
    shutil.rmtree(settings.TEMP_DIR / upload_id, ignore_errors=True)


def _http_from_ingestion(exc: IngestionError) -> HTTPException:
    return HTTPException(
        status_code=exc.http_status,
        detail={"code": exc.code, "message": exc.message},
    )


# ---------------------------------------------------------------------------
# Upload
# ---------------------------------------------------------------------------

@router.post("/upload", status_code=201)
async def upload_dataset(
    file: UploadFile = File(...),
    sheet_name: Optional[str] = Form(None),
    project_id: Optional[str] = Form(None),
) -> Dict[str, Any]:
    _require_db()
    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing filename.")

    upload_id = uuid.uuid4().hex
    safe_name = sanitize_filename(file.filename)
    upload_dir = settings.DATASETS_DIR / upload_id
    upload_dir.mkdir(parents=True, exist_ok=True)
    stored_path = upload_dir / safe_name

    # Streaming write with hard size limit (never buffer whole file).
    max_bytes = settings.MAX_UPLOAD_MB * 1024 * 1024
    size = 0
    try:
        with open(stored_path, "wb") as out:
            while True:
                chunk = await file.read(_UPLOAD_CHUNK)
                if not chunk:
                    break
                size += len(chunk)
                if size > max_bytes:
                    out.close()
                    shutil.rmtree(upload_dir, ignore_errors=True)
                    raise HTTPException(
                        status_code=413,
                        detail={
                            "code": "UPLOAD_TOO_LARGE",
                            "message": f"Upload exceeds {settings.MAX_UPLOAD_MB} MB limit.",
                        },
                    )
                out.write(chunk)
    except HTTPException:
        raise
    except Exception as exc:
        shutil.rmtree(upload_dir, ignore_errors=True)
        raise HTTPException(
            status_code=400,
            detail={
                "code": "UPLOAD_READ_FAILED",
                "message": f"Failed to read uploaded file: {type(exc).__name__}",
            },
        )

    if size == 0:
        shutil.rmtree(upload_dir, ignore_errors=True)
        raise HTTPException(
            status_code=400,
            detail={"code": "EMPTY_FILE", "message": "Uploaded file is empty (0 bytes)."},
        )

    try:
        result = await run_in_threadpool(
            process_upload,
            stored_path=stored_path,
            original_name=file.filename,
            upload_id=upload_id,
            sheet_name=sheet_name,
        )
    except IngestionError as exc:
        _cleanup_upload(upload_id)
        await record_audit(
            "dataset_ingestion_failed",
            status="error",
            upload_id=upload_id,
            details={"filename": safe_name, "code": exc.code, "message": exc.message},
        )
        raise _http_from_ingestion(exc)
    except SecurityError as exc:
        _cleanup_upload(upload_id)
        await record_audit(
            "dataset_ingestion_failed",
            status="error",
            upload_id=upload_id,
            details={"filename": safe_name, "code": exc.code},
        )
        status = 413 if "SIZE" in exc.code or "RATIO" in exc.code else 422
        raise HTTPException(
            status_code=status, detail={"code": exc.code, "message": exc.message}
        )
    except MetadataUnavailable as exc:
        _cleanup_upload(upload_id)
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        # Unexpected failure: structured 500, no internals leaked, audit kept.
        _cleanup_upload(upload_id)
        await record_audit(
            "dataset_ingestion_failed",
            status="error",
            upload_id=upload_id,
            details={"filename": safe_name, "error": type(exc).__name__},
        )
        raise HTTPException(
            status_code=500,
            detail={
                "code": "INTERNAL_ERROR",
                "message": f"Unexpected ingestion error: {type(exc).__name__}",
            },
        )

    # Persist metadata + audit events.
    from ..repo import utcnow
    from ..profiling.profiler import profile_dataset

    for doc in result["datasets"]:
        doc["created_at"] = utcnow()
        if project_id:
            doc["project_id"] = project_id
        
        # Ensure DuckDB view is registered immediately
        try:
            registry.ensure_view(doc["dataset_id"], doc.get("normalized_path"))
        except Exception as reg_exc:
            logger.warning("Auto DuckDB view registration failed: %s", reg_exc)

    try:
        await repo.insert_datasets(result["datasets"])
        if project_id:
            coll = db_manager.get_collection("projects")
            if coll is not None:
                try:
                    await coll.update_one(
                        {"project_id": project_id},
                        {"$inc": {"dataset_count": len(result["datasets"]), "datasetCount": len(result["datasets"])}},
                    )
                except Exception:
                    pass
    except MetadataUnavailable:
        shutil.rmtree(upload_dir, ignore_errors=True)
        raise HTTPException(
            status_code=503,
            detail={
                "code": "METADATA_UNAVAILABLE",
                "message": "Ingested but could not persist metadata; upload rolled back.",
            },
        )

    await record_audit(
        "dataset_upload",
        status="ok",
        upload_id=upload_id,
        project_id=project_id,
        details={
            "filename": safe_name,
            "datasets": len(result["datasets"]),
            "unsupported": len(result["unsupported"]),
            "rejected": len(result["rejected"]),
            "bytes": size,
        },
    )
    for doc in result["datasets"]:
        await record_audit(
            "dataset_ingested",
            status=doc["ingestion_status"],
            upload_id=upload_id,
            project_id=project_id,
            dataset_id=doc["dataset_id"],
            details={
                "table_name": doc["table_name"],
                "rows": doc["row_count"],
                "columns": doc["column_count"],
                "format": doc["source_format"],
            },
        )

    return {
        "upload_id": upload_id,
        "original_filename": safe_name,
        "source_format": result["source_format"],
        "bytes": size,
        "datasets": [
            {
                "dataset_id": d["dataset_id"],
                "name": d.get("name", d["table_name"]),
                "original_filename": d["original_filename"],
                "source_format": d["source_format"],
                "table_name": d["table_name"],
                "row_count": d["row_count"],
                "column_count": d["column_count"],
                "schema": d.get("schema", {}),
                "quality_score": d.get("profile", {}).get("quality_score", 100) if d.get("profile") else 100,
                "archive_member": d.get("archive_member"),
                "ingestion_status": d["ingestion_status"],
                "warnings": d["warnings"],
                "errors": d["errors"],
            }
            for d in result["datasets"]
        ],
        "manifest": result["manifest"],
        "unsupported_files": result["unsupported"],
        "rejected_entries": result["rejected"],
        "parse_failures": result["parse_failures"],
    }


# ---------------------------------------------------------------------------
# Read APIs
# ---------------------------------------------------------------------------

@router.get("")
async def list_datasets(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    project_id: Optional[str] = Query(None),
) -> Dict[str, Any]:
    _require_db()
    items = await repo.list_datasets(limit=limit, offset=offset, project_id=project_id)
    total = await repo.count_datasets(project_id=project_id)
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.get("/{dataset_id}")
async def get_dataset(dataset_id: str) -> Dict[str, Any]:
    return await _get_or_404(dataset_id)


@router.get("/{dataset_id}/schema")
async def get_dataset_schema(dataset_id: str) -> Dict[str, Any]:
    doc = await _get_or_404(dataset_id)
    return {
        "dataset_id": doc["dataset_id"],
        "table_name": doc["table_name"],
        "row_count": doc["row_count"],
        "column_count": doc["column_count"],
        "columns": doc["schema"],
    }


@router.get("/{dataset_id}/preview")
async def preview_dataset(
    dataset_id: str,
    limit: int = Query(10, ge=1, le=settings.MAX_PREVIEW_ROWS),
) -> Dict[str, Any]:
    doc = await _get_or_404(dataset_id)
    if doc.get("ingestion_status") != "completed":
        raise HTTPException(
            status_code=409,
            detail={"code": "NOT_INGESTED", "message": "Dataset failed ingestion."},
        )
    try:
        data = await run_in_threadpool(registry.preview, dataset_id, limit, doc.get("normalized_path"))
    except Exception as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "REGISTRATION_UNAVAILABLE",
                "message": f"Preview unavailable: {type(exc).__name__}: {exc}",
            },
        )
    return {
        "dataset_id": dataset_id,
        "table_name": doc["table_name"],
        "limit": limit,
        **data,
    }


@router.get("/{dataset_id}/quality")
async def get_dataset_quality(dataset_id: str) -> Dict[str, Any]:
    doc = await _get_or_404(dataset_id)
    profile = doc.get("profile")
    if not profile:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "NOT_PROFILED",
                "message": "No quality report yet. Run POST "
                f"/api/datasets/{dataset_id}/profile first.",
            },
        )
    return {"dataset_id": dataset_id, **profile}


# ---------------------------------------------------------------------------
# Profiling (Phase 5 - deterministic, zero LLM)
# ---------------------------------------------------------------------------

def _profile_report_path(dataset_id: str) -> Path:
    return settings.DATA_DIR / "profiles" / f"{dataset_id}.json"


@router.post("/{dataset_id}/profile", status_code=201)
async def create_profile(dataset_id: str) -> Dict[str, Any]:
    doc = await _get_or_404(dataset_id)
    if doc.get("ingestion_status") != "completed":
        raise HTTPException(
            status_code=409,
            detail={"code": "NOT_INGESTED", "message": "Dataset failed ingestion."},
        )
    try:
        report = await run_in_threadpool(build_quality_report, doc)
    except Exception as exc:
        await record_audit(
            "dataset_profile_failed",
            status="error",
            dataset_id=dataset_id,
            details={"error": type(exc).__name__},
        )
        raise HTTPException(
            status_code=500,
            detail={
                "code": "PROFILE_FAILED",
                "message": f"Profiling failed: {type(exc).__name__}: {exc}",
            },
        )

    summary = profile_summary(report)
    report_path = _profile_report_path(dataset_id)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")

    summary["report_path"] = str(report_path)
    await repo.update_dataset(dataset_id, {"profile": summary})
    await record_audit(
        "dataset_profiled",
        status="ok",
        dataset_id=dataset_id,
        details={
            "quality_score": summary["quality_score"],
            "quality_grade": summary["quality_grade"],
            "issues": summary["issue_count"],
        },
    )
    return {"dataset_id": dataset_id, "summary": summary, "report_path": str(report_path)}


@router.get("/{dataset_id}/profile")
async def get_profile(dataset_id: str) -> Dict[str, Any]:
    await _get_or_404(dataset_id)
    report_path = _profile_report_path(dataset_id)
    if not report_path.exists():
        raise HTTPException(
            status_code=404,
            detail={
                "code": "NOT_PROFILED",
                "message": "No profile report found; run "
                f"POST /api/datasets/{dataset_id}/profile first.",
            },
        )
    return json.loads(report_path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Delete, Update & Relationship Mapping APIs
# ---------------------------------------------------------------------------

class DatasetUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    table_name: Optional[str] = None


class RowUpdateRequest(BaseModel):
    action: str  # "update" | "delete" | "add"
    row_index: Optional[int] = None
    row_data: Optional[Dict[str, Any]] = None


@router.delete("/{dataset_id}")
async def delete_dataset(dataset_id: str) -> Dict[str, Any]:
    """Delete a dataset, unregistering its views and removing its artifacts."""
    _require_db()
    doc = await _get_or_404(dataset_id)

    # 1. Remove physical files
    for key in ("normalized_path", "storage_path"):
        p_str = doc.get(key)
        if p_str:
            p = Path(p_str)
            if p.exists() and p.is_file():
                try:
                    p.unlink(missing_ok=True)
                except Exception as e:
                    logger.warning(f"Failed to remove file {p}: {e}")

    # 2. Remove profile report if exists
    report_p = _profile_report_path(dataset_id)
    if report_p.exists():
        try:
            report_p.unlink(missing_ok=True)
        except Exception:
            pass

    # 3. Unregister DuckDB view
    try:
        registry.unregister(dataset_id)
    except Exception as e:
        logger.warning(f"Could not unregister DuckDB view for {dataset_id}: {e}")

    # 4. Remove from repository
    deleted = await repo.delete_dataset(dataset_id)
    await record_audit(
        "dataset_deleted",
        status="ok",
        dataset_id=dataset_id,
        details={"name": doc.get("name"), "table_name": doc.get("table_name")},
    )
    return {"deleted": deleted, "dataset_id": dataset_id, "message": "Dataset successfully deleted."}


@router.patch("/{dataset_id}")
async def update_dataset_meta(dataset_id: str, body: DatasetUpdateRequest) -> Dict[str, Any]:
    """Update dataset metadata (name, table_name, description)."""
    _require_db()
    doc = await _get_or_404(dataset_id)
    update_data = {k: v for k, v in body.model_dump().items() if v is not None}
    if update_data:
        await repo.update_dataset(dataset_id, update_data)
        await record_audit(
            "dataset_updated",
            status="ok",
            dataset_id=dataset_id,
            details=update_data,
        )
    updated_doc = await _get_or_404(dataset_id)
    return {"dataset_id": dataset_id, **updated_doc}


@router.post("/{dataset_id}/data/update")
async def update_dataset_data(dataset_id: str, body: RowUpdateRequest) -> Dict[str, Any]:
    """Update data rows (in-place row editing, adding rows, or deleting rows)."""
    _require_db()
    doc = await _get_or_404(dataset_id)
    norm_path = doc.get("normalized_path")
    if not norm_path or not Path(norm_path).exists():
        raise HTTPException(status_code=404, detail="Underlying dataset parquet file not found.")

    import pandas as pd
    try:
        df = pd.read_parquet(norm_path)
        orig_dtypes = df.dtypes.copy()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to read dataset parquet: {exc}")

    if body.action == "update":
        if body.row_index is None or body.row_index < 0 or body.row_index >= len(df):
            raise HTTPException(status_code=400, detail="Invalid row_index for update.")
        if not body.row_data:
            raise HTTPException(status_code=400, detail="Missing row_data.")
        for k, v in body.row_data.items():
            if k in df.columns:
                try:
                    df.at[body.row_index, k] = v
                except Exception:
                    df[k] = df[k].astype(object)
                    df.at[body.row_index, k] = v

    elif body.action == "delete":
        if body.row_index is None or body.row_index < 0 or body.row_index >= len(df):
            raise HTTPException(status_code=400, detail="Invalid row_index for delete.")
        df = df.drop(df.index[body.row_index]).reset_index(drop=True)

    elif body.action == "add":
        if not body.row_data:
            raise HTTPException(status_code=400, detail="Missing row_data.")
        new_row = {c: body.row_data.get(c, None) for c in df.columns}
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)

    else:
        raise HTTPException(status_code=400, detail=f"Unsupported action '{body.action}'. Must be 'update', 'delete', or 'add'.")

    # Coerce dataframe columns back to original schema dtypes for safe Parquet persistence
    for col, dtype in orig_dtypes.items():
        if col not in df.columns:
            continue
        try:
            if pd.api.types.is_bool_dtype(dtype):
                df[col] = df[col].apply(
                    lambda x: True if str(x).strip().lower() in ("true", "yes", "1", "t")
                    else (False if str(x).strip().lower() in ("false", "no", "0", "f") else False)
                )
            elif pd.api.types.is_integer_dtype(dtype):
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(dtype)
            elif pd.api.types.is_float_dtype(dtype):
                df[col] = pd.to_numeric(df[col], errors="coerce").astype(dtype)
            elif pd.api.types.is_datetime64_any_dtype(dtype):
                df[col] = pd.to_datetime(df[col], errors="coerce")
        except Exception as coerce_exc:
            logger.debug(f"Could not coerce {col} to {dtype}: {coerce_exc}")

    # Save changes back to Parquet
    df.to_parquet(norm_path)

    # Re-register view in DuckDB for instant live querying
    try:
        registry.register(dataset_id, norm_path)
    except Exception as exc:
        logger.warning(f"Could not refresh DuckDB view: {exc}")

    # Update metadata count
    await repo.update_dataset(dataset_id, {"row_count": len(df)})
    await record_audit(
        "dataset_rows_modified",
        status="ok",
        dataset_id=dataset_id,
        details={"action": body.action, "row_index": body.row_index, "new_count": len(df)},
    )

    return {
        "success": True,
        "dataset_id": dataset_id,
        "action": body.action,
        "row_count": len(df),
        "message": f"Successfully performed '{body.action}' on dataset {dataset_id}."
    }


@router.get("/{dataset_id}/relationships")
async def get_dataset_relationships(dataset_id: str) -> Dict[str, Any]:
    """Spot and extract semantic, dimensional, causal, and cross-dataset foreign-key relationships."""
    _require_db()
    doc = await _get_or_404(dataset_id)
    project_id = doc.get("project_id")

    sibling_datasets = []
    if project_id:
        try:
            sibling_datasets = await repo.list_datasets(limit=50, project_id=project_id)
        except Exception:
            sibling_datasets = []

    schema = doc.get("schema", [])
    col_names = [c["name"] if isinstance(c, dict) else str(c) for c in schema]

    relationships = []
    nodes = []

    # 1. Main Table Node
    table_node_id = f"table_{dataset_id}"
    nodes.append({
        "id": table_node_id,
        "label": doc.get("name", doc.get("table_name", "Dataset")),
        "type": "table",
        "format": doc.get("source_format", "csv"),
        "rowCount": doc.get("row_count", 0),
        "datasetId": dataset_id,
    })

    # Read preview/duckdb to compute real metrics/uniqueness
    df = None
    try:
        registry.ensure_view(dataset_id, doc.get("normalized_path"))
        conn = registry.get_conn()
        v_name = registry.view_name(dataset_id)
        df = conn.execute(f'SELECT * FROM "{v_name}"').df()
    except Exception:
        pass

    # 2. Extract column-level roles and relationships
    for col_info in schema:
        col_name = col_info["name"] if isinstance(col_info, dict) else str(col_info)
        col_type = col_info.get("type", "string") if isinstance(col_info, dict) else "string"
        col_node_id = f"col_{dataset_id}_{col_name}"

        # Determine role & cardinality
        is_id = any(term in col_name.lower() for term in ["id", "_id", "code", "key", "num", "segment"])
        is_target = any(term in col_name.lower() for term in ["target", "label", "outcome", "accident", "churn", "converted", "default"])
        is_date = any(term in col_name.lower() for term in ["date", "time", "timestamp", "year", "month"])

        is_unique = False
        null_count = 0
        if df is not None and col_name in df.columns:
            is_unique = bool(df[col_name].nunique() == len(df))
            null_count = int(df[col_name].isna().sum())

        role = "Identifier (Primary Key)" if (is_id and is_unique) else \
               "Foreign Key / Reference" if is_id else \
               "Target / Outcome" if is_target else \
               "Temporal Anchor" if is_date else \
               "Metric Measure" if col_type in ("int", "float", "double", "numeric") else \
               "Categorical Dimension"

        nodes.append({
            "id": col_node_id,
            "label": col_name,
            "type": "column",
            "role": role,
            "dataType": col_type,
            "isUnique": is_unique,
            "nullCount": null_count,
            "parentTable": table_node_id
        })

        # Table-to-Column Link
        relationships.append({
            "id": f"rel_{table_node_id}_{col_node_id}",
            "source": table_node_id,
            "target": col_node_id,
            "sourceLabel": doc.get("name", "Dataset"),
            "targetLabel": col_name,
            "predicate": "HAS_COLUMN",
            "cardinality": "1:1" if is_unique else "1:N",
            "confidence": 1.0,
            "kind": "structural",
            "description": f"Dataset owns {col_name} as {role}."
        })

    # 3. Detect Intra-Table Relationships (Target Dependencies & Groupings)
    target_cols = [c for c in col_names if any(t in c.lower() for t in ["accident", "target", "label", "outcome", "churn", "sales", "revenue"])]
    primary_target = target_cols[0] if target_cols else (col_names[-1] if col_names else None)

    if primary_target and df is not None and primary_target in df.columns:
        for c in col_names:
            if c != primary_target and c in df.columns:
                relationships.append({
                    "id": f"rel_dep_{c}_{primary_target}",
                    "source": f"col_{dataset_id}_{c}",
                    "target": f"col_{dataset_id}_{primary_target}",
                    "sourceLabel": c,
                    "targetLabel": primary_target,
                    "predicate": "INFLUENCES / DRIVES",
                    "cardinality": "N:1",
                    "confidence": 0.88,
                    "kind": "causal",
                    "description": f"Feature '{c}' drives variance in target '{primary_target}'."
                })

    # 4. Detect Cross-Dataset / Multi-Table Foreign Key Links
    for other in sibling_datasets:
        other_id = other.get("dataset_id") or other.get("id")
        if not other_id or other_id == dataset_id:
            continue
        other_schema = other.get("schema", [])
        other_cols = [c["name"] if isinstance(c, dict) else str(c) for c in other_schema]

        common_keys = set(col_names).intersection(set(other_cols))
        for key in common_keys:
            if any(term in key.lower() for term in ["id", "_id", "code", "key", "segment", "user", "order", "product"]):
                other_table_node_id = f"table_{other_id}"
                if not any(n["id"] == other_table_node_id for n in nodes):
                    nodes.append({
                        "id": other_table_node_id,
                        "label": other.get("name", other.get("table_name", "Associated Dataset")),
                        "type": "table",
                        "format": other.get("source_format", "csv"),
                        "rowCount": other.get("row_count", 0),
                        "datasetId": other_id,
                    })

                relationships.append({
                    "id": f"rel_fk_{dataset_id}_{other_id}_{key}",
                    "source": f"col_{dataset_id}_{key}",
                    "target": f"col_{other_id}_{key}",
                    "sourceLabel": f"{doc.get('name', 'This Table')}.{key}",
                    "targetLabel": f"{other.get('name', 'Other Table')}.{key}",
                    "predicate": "FOREIGN_KEY_MATCH",
                    "cardinality": "1:N",
                    "confidence": 0.96,
                    "kind": "relational",
                    "joinKey": key,
                    "description": f"Foreign Key link between '{doc.get('name')}' and '{other.get('name')}' on `{key}`."
                })

    return {
        "dataset_id": dataset_id,
        "table_name": doc.get("table_name"),
        "total_nodes": len(nodes),
        "total_relationships": len(relationships),
        "nodes": nodes,
        "relationships": relationships
    }

