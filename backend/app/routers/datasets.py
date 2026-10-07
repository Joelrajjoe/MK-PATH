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

    for doc in result["datasets"]:
        doc["created_at"] = utcnow()
        if project_id:
            doc["project_id"] = project_id
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
                "original_filename": d["original_filename"],
                "source_format": d["source_format"],
                "table_name": d["table_name"],
                "row_count": d["row_count"],
                "column_count": d["column_count"],
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
    if not profile and doc.get("ingestion_status") == "completed":
        try:
            report = await run_in_threadpool(build_quality_report, doc)
            profile = profile_summary(report)
            await repo.update_dataset(dataset_id, {"profile": profile})
        except Exception as exc:
            logger.warning(f"On-the-fly profiling failed for {dataset_id}: {exc}")

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
