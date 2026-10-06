"""Universal Data Ingestion pipeline (Phase 4).

Upload pipeline (spec):
  File Validation -> Type Detection -> Secure Storage -> ZIP Extraction ->
  Supported File Discovery -> Format Parser -> Normalized Representation ->
  DuckDB Registration -> Dataset Metadata -> Audit Event

This module is SYNCHRONOUS by design: it is executed in a worker thread
from the async API layer so CPU-bound parsing never blocks the event loop.
"""
import logging
import shutil
import uuid
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ..config import settings
from . import registry, security
from .parsers import IngestionError, TableInfo, parse_file
from .security import SecurityError, classify_extension, sanitize_filename

logger = logging.getLogger("mkpath.ingestion")

SOURCE_FORMATS = {
    ".csv": "csv",
    ".xlsx": "xlsx",
    ".xls": "xls",
    ".json": "json",
    ".parquet": "parquet",
    ".sql": "sql",
    ".zip": "zip",
}

_TEXT_EXTENSIONS = {".csv", ".json", ".sql"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _detect_content_type(path: Path, ext: str) -> None:
    """Validate that file CONTENT matches its extension (untrusted input)."""
    head = path.read_bytes()[:8192]
    if ext == ".zip" or ext == ".xlsx":
        if not (head.startswith(b"PK\x03\x04") or head.startswith(b"PK\x05\x06")):
            raise IngestionError(
                "INVALID_ZIP",
                "File claims to be a ZIP-based format but does not have a "
                "valid ZIP signature (corrupt or mislabeled file).",
                http_status=400,
            )
    elif ext == ".xls":
        if not head.startswith(b"\xd0\xcf\x11\xe0"):
            raise IngestionError(
                "MALFORMED_EXCEL",
                "File claims to be legacy .xls but lacks the OLE2 signature.",
                http_status=422,
            )
    elif ext == ".parquet":
        if path.stat().st_size < 8:
            raise IngestionError(
                "MALFORMED_PARQUET", "Parquet file is too small to be valid."
            )
    elif ext in _TEXT_EXTENSIONS:
        if b"\x00" in head:
            raise IngestionError(
                "BINARY_NOT_TEXT",
                f"File has a {ext} extension but contains binary data "
                "(possibly a mislabeled archive).",
                http_status=415,
            )


def _new_dataset_doc(
    *,
    dataset_id: str,
    source_file_id: str,
    original_filename: str,
    source_format: str,
    storage_path: str,
    table: TableInfo,
    upload_id: str,
    warnings: List[str],
    archive_member: Optional[str] = None,
    parent_archive: Optional[str] = None,
) -> Dict[str, Any]:
    return {
        "dataset_id": dataset_id,
        "source_file_id": source_file_id,
        "original_filename": original_filename,
        "source_format": source_format,
        "storage_path": storage_path,
        "normalized_path": table.normalized_path,
        "table_name": table.table_name,
        "view_name": registry.view_name(dataset_id),
        "schema": table.schema,
        "row_count": table.row_count,
        "column_count": table.column_count,
        "ingestion_status": "completed",
        "warnings": list(warnings) + list(table.warnings),
        "errors": [],
        "created_at": None,  # stamped by caller (async layer) with utcnow()
        "upload_id": upload_id,
        "archive_member": archive_member,
        "parent_archive": parent_archive,
        "profile": None,
    }


def _finalize_normalized_path(table: TableInfo, upload_id: str, dataset_id: str) -> str:
    """Move staged Parquet into data/<upload_id>/<dataset_id>.parquet."""
    src = Path(table.normalized_path)
    staging_root = (settings.DATA_DIR / "staging").resolve()
    try:
        if src.resolve().parent == staging_root:
            dest_dir = settings.DATA_DIR / upload_id
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest = dest_dir / f"{dataset_id}.parquet"
            shutil.move(str(src), str(dest))
            table.normalized_path = str(dest)
    except OSError as exc:
        logger.warning("Could not relocate normalized file: %s", type(exc).__name__)
    return table.normalized_path


# ---------------------------------------------------------------------------
# ZIP handling
# ---------------------------------------------------------------------------

def _discover_from_zip(
    zip_path: Path,
    upload_id: str,
    depth: int,
    manifest: List[Dict[str, Any]],
    unsupported: List[Dict[str, Any]],
    rejected: List[Dict[str, Any]],
    sheet_name: Optional[str],
) -> List[Tuple[Path, str, str, Optional[str], Optional[str]]]:
    """Return candidates: (file_path, original_name, archive_rel, member, parent_archive).

    Recurses into nested ZIPs only while depth < MAX_ZIP_DEPTH.
    """
    candidates: List[Tuple[Path, str, str, Optional[str], Optional[str]]] = []
    extract_dir = settings.TEMP_DIR / upload_id / f"depth_{depth}_{uuid.uuid4().hex[:8]}"

    try:
        extracted, rejected_entries = security.extract_zip_safely(zip_path, extract_dir)
    except SecurityError as exc:
        raise IngestionError(exc.code, exc.message, http_status=400)

    archive_rel = zip_path.name if depth == 0 else zip_path.name
    parent = str(zip_path)

    for rej in rejected_entries:
        rej["archive"] = archive_rel
        rejected.append(rej)
        manifest.append(
            {
                "path": f"{archive_rel}!{rej['entry']}",
                "kind": "rejected",
                "code": rej["code"],
                "reason": rej["reason"],
            }
        )

    for rel in extracted:
        fp = extract_dir / rel
        if fp.is_dir():
            continue
        kind = classify_extension(rel)
        member_id = f"{archive_rel}!{rel}"
        if kind == "archive":
            if depth + 1 <= settings.MAX_ZIP_DEPTH:
                if not zipfile.is_zipfile(fp):
                    reason = "Corrupt or invalid nested archive"
                    unsupported.append({"path": member_id, "reason": reason})
                    manifest.append(
                        {"path": member_id, "kind": "unsupported", "reason": reason}
                    )
                    continue
                manifest.append(
                    {"path": member_id, "kind": "archive", "reason": "nested archive"}
                )
                candidates.extend(
                    _discover_from_zip(
                        fp, upload_id, depth + 1, manifest, unsupported, rejected, None
                    )
                )
            else:
                reason = (
                    f"Nested archive exceeds MAX_ZIP_DEPTH="
                    f"{settings.MAX_ZIP_DEPTH}"
                )
                unsupported.append({"path": member_id, "reason": reason})
                manifest.append(
                    {"path": member_id, "kind": "unsupported", "reason": reason}
                )
        elif kind == "supported":
            candidates.append((fp, Path(rel).name, rel, member_id, parent))
            manifest.append(
                {"path": member_id, "kind": "supported", "reason": ""}
            )
        else:
            reason = f"Unsupported file type {Path(rel).suffix.lower()!r} in archive"
            unsupported.append({"path": member_id, "reason": reason})
            manifest.append(
                {"path": member_id, "kind": "unsupported", "reason": reason}
            )

    return candidates


# ---------------------------------------------------------------------------
# Main pipeline (sync; runs in a worker thread)
# ---------------------------------------------------------------------------

def process_upload(
    *,
    stored_path: Path,
    original_name: str,
    upload_id: str,
    sheet_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Run the full ingestion pipeline for one uploaded file.

    Returns a result dict:
      datasets: list of dataset documents (created_at still None)
      manifest / unsupported / rejected: archive bookkeeping
      upload_id, original_filename, source_format
    Raises IngestionError / SecurityError on fatal validation failures.
    """
    safe_name = sanitize_filename(original_name)
    ext = Path(safe_name).suffix.lower()
    kind = classify_extension(safe_name)
    if kind == "unsupported":
        raise IngestionError(
            "UNSUPPORTED_EXTENSION",
            f"Unsupported file type {ext!r}. Supported: csv, xlsx, xls, json, "
            "parquet, sql, zip.",
            http_status=415,
        )

    _detect_content_type(stored_path, ext)

    manifest: List[Dict[str, Any]] = []
    unsupported: List[Dict[str, Any]] = []
    rejected: List[Dict[str, Any]] = []

    # 1. Secure storage already done (stored_path under datasets/<upload_id>/).
    # 2. ZIP extraction + discovery.
    if ext == ".zip":
        if not zipfile.is_zipfile(stored_path):
            raise IngestionError(
                "INVALID_ZIP",
                "Uploaded file is not a valid ZIP archive (corrupt or truncated).",
                http_status=400,
            )
        manifest.append({"path": safe_name, "kind": "archive", "reason": "top-level"})
        candidates = _discover_from_zip(
            stored_path, upload_id, 0, manifest, unsupported, rejected, sheet_name
        )
        if not candidates and not unsupported and not rejected:
            raise IngestionError(
                "EMPTY_ZIP",
                "ZIP archive contains no files.",
                http_status=422,
            )
        # Sheet selection only applies to a single explicit workbook upload.
        effective_sheet = None
    else:
        candidates = [(stored_path, safe_name, safe_name, None, None)]
        effective_sheet = sheet_name

    # 3. Parse each supported file independently.
    datasets: List[Dict[str, Any]] = []
    parse_failures: List[Dict[str, Any]] = []

    for file_path, orig, rel, member, parent_archive in candidates:
        source_format = SOURCE_FORMATS.get(Path(orig).suffix.lower(), "unknown")
        source_file_id = uuid.uuid4().hex
        try:
            _detect_content_type(file_path, Path(orig).suffix.lower())
            tables = parse_file(file_path, Path(orig).stem, effective_sheet)
        except IngestionError as exc:
            failure = {
                "path": member or orig,
                "code": exc.code,
                "message": exc.message,
            }
            parse_failures.append(failure)
            manifest.append(
                {
                    "path": member or orig,
                    "kind": "failed",
                    "code": exc.code,
                    "reason": exc.message,
                }
            )
            continue

        for table in tables:
            dataset_id = uuid.uuid4().hex
            storage_path = str(file_path)
            # Persist ZIP members into datasets/<upload_id>/ (temp is cleaned).
            if member:
                dest_dir = settings.DATASETS_DIR / upload_id / "extracted"
                dest_dir.mkdir(parents=True, exist_ok=True)
                safe_rel = sanitize_filename(rel.replace("/", "_"), "member")
                dest = dest_dir / f"{uuid.uuid4().hex[:8]}_{safe_rel}"
                try:
                    shutil.copy2(file_path, dest)
                    storage_path = str(dest)
                except OSError:
                    pass  # keep temp path as storage_path (still on E:)
            _finalize_normalized_path(table, upload_id, dataset_id)
            doc = _new_dataset_doc(
                dataset_id=dataset_id,
                source_file_id=source_file_id,
                original_filename=orig,
                source_format=source_format,
                storage_path=storage_path,
                table=table,
                upload_id=upload_id,
                warnings=[],
                archive_member=member,
                parent_archive=parent_archive,
            )
            # DuckDB registration (lazy view over normalized Parquet).
            try:
                registry.register(dataset_id, table.normalized_path)
            except Exception as exc:
                doc["ingestion_status"] = "failed"
                doc["errors"] = [
                    {"code": "DUCKDB_REGISTRATION_FAILED", "message": str(exc)}
                ]
            datasets.append(doc)

    # 4. Clean extraction directory (originals already copied for members).
    if ext == ".zip":
        shutil.rmtree(settings.TEMP_DIR / upload_id, ignore_errors=True)

    if not datasets:
        # Nothing ingested -> structured fatal error (never a fake success).
        if parse_failures:
            first = parse_failures[0]
            extra = (
                f" ({len(unsupported)} unsupported file(s) also present)"
                if unsupported
                else ""
            )
            raise IngestionError(first["code"], f"{first['message']}{extra}")
        if unsupported or rejected:
            sample = "; ".join(
                [f"{u['path']}: {u.get('reason', '')}" for u in unsupported[:5]]
                + [f"{r['entry']}: {r['reason']}" for r in rejected[:5]]
            )
            raise IngestionError(
                "NO_SUPPORTED_FILES",
                "No dataset could be ingested from the archive. "
                f"Unprocessed files: {sample}",
            )
        raise IngestionError("NO_SUPPORTED_FILES", "No files found to ingest.")

    return {
        "upload_id": upload_id,
        "original_filename": safe_name,
        "source_format": "zip" if ext == ".zip" else source_format,
        "datasets": datasets,
        "manifest": manifest,
        "unsupported": unsupported,
        "rejected": rejected,
        "parse_failures": parse_failures,
    }
