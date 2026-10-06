"""Security helpers for the Universal Data Ingestion Engine (Phase 4).

Threat model: uploaded files and archive entries are untrusted input.
- Never trust uploaded filenames as filesystem paths (ZIP slip / traversal).
- Never extract outside the designated temp root (project temp/).
- Enforce size / entry-count / compression-ratio budgets (decompression bombs).
- Never allow symlinks or special files out of archives.
"""
import os
import re
import zipfile
from pathlib import Path
from typing import List, Optional, Tuple

from ..config import settings

# Extension allow-list (spec section 12). ZIP handled separately.
SUPPORTED_EXTENSIONS = {".csv", ".xlsx", ".xls", ".json", ".parquet", ".sql"}
ARCHIVE_EXTENSION = ".zip"

_DRIVE_RE = re.compile(r"^[A-Za-z]:")
_CONTROL_RE = re.compile(r"[\x00-\x1f\x7f]")
_UNSAFE_NAME_RE = re.compile(r"[^A-Za-z0-9._\- ()\[\]]+")


class SecurityError(Exception):
    """Raised when untrusted input violates a security policy."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def sanitize_filename(name: str, fallback: str = "unnamed") -> str:
    """Reduce an untrusted filename to a safe basename. Never a path."""
    # Drop any directory components (both separators) and drive letters.
    name = name.replace("\\", "/").split("/")[-1]
    name = _DRIVE_RE.sub("", name)
    name = _CONTROL_RE.sub("", name)
    # Keep a conservative character set; collapse everything else.
    name = _UNSAFE_NAME_RE.sub("_", name).strip(" .")
    name = name[:150]
    if not name or name in {".", ".."}:
        return fallback
    return name


def safe_join(root: Path, *parts: str) -> Path:
    """Join untrusted relative parts under root; refuse escape.

    Raises SecurityError if the resolved target leaves root.
    """
    target = root
    for p in parts:
        target = target / p
    root_resolved = os.path.realpath(root)
    target_resolved = os.path.realpath(target)
    if target_resolved != root_resolved and not target_resolved.startswith(
        root_resolved + os.sep
    ):
        raise SecurityError(
            "PATH_TRAVERSAL", f"Path escapes the designated extraction root: {parts!r}"
        )
    return target


def classify_extension(filename: str) -> str:
    """Return 'supported' | 'archive' | 'unsupported' from the extension."""
    ext = Path(filename).suffix.lower()
    if ext in SUPPORTED_EXTENSIONS:
        return "supported"
    if ext == ARCHIVE_EXTENSION:
        return "archive"
    return "unsupported"


def validate_zip_entry(info: zipfile.ZipInfo) -> None:
    """Validate a single archive entry before any bytes are written."""
    name = info.filename

    if not name or "\x00" in name:
        raise SecurityError("BAD_ENTRY_NAME", "Archive entry has an empty or NUL name.")

    # Encrypted entries cannot be extracted safely by stdlib zipfile.
    if info.flag_bits & 0x1:
        raise SecurityError("ENCRYPTED_ENTRY", f"Encrypted entry not allowed: {name!r}")

    # Symlink / special-file detection via external attributes (Unix mode).
    mode = (info.external_attr >> 16) & 0o170000
    if mode == 0o120000:
        raise SecurityError("SYMLINK_ENTRY", f"Symlink entries are not allowed: {name!r}")
    if mode not in (0, 0o100000, 0o040000):
        raise SecurityError(
            "SPECIAL_FILE_ENTRY", f"Special file entries are not allowed: {name!r}"
        )

    norm = name.replace("\\", "/")
    if norm.startswith("/") or _DRIVE_RE.match(norm):
        raise SecurityError(
            "ABSOLUTE_PATH_ENTRY", f"Absolute paths in archives are not allowed: {name!r}"
        )
    for part in norm.split("/"):
        if part == "..":
            raise SecurityError(
                "PATH_TRAVERSAL", f"Path traversal ('..') in archive entry: {name!r}"
            )


def check_zip_limits(infos: List[zipfile.ZipInfo]) -> None:
    """Archive-level budgets, evaluated BEFORE extraction (bomb protection)."""
    if len(infos) > settings.MAX_ZIP_ENTRIES:
        raise SecurityError(
            "TOO_MANY_ENTRIES",
            f"Archive has {len(infos)} entries; limit is {settings.MAX_ZIP_ENTRIES}.",
        )

    total_uncompressed = sum(i.file_size for i in infos)
    total_compressed = sum(i.compress_size for i in infos)
    max_bytes = settings.MAX_ZIP_UNCOMPRESSED_MB * 1024 * 1024

    if total_uncompressed > max_bytes:
        raise SecurityError(
            "ESTIMATED_SIZE_EXCEEDED",
            f"Estimated extracted size {total_uncompressed} bytes exceeds limit "
            f"{max_bytes} bytes.",
        )
    # Ratio guard only applies when the archive is large enough to matter.
    if total_uncompressed > 10 * 1024 * 1024 and total_compressed > 0:
        ratio = total_uncompressed / total_compressed
        if ratio > settings.MAX_ZIP_RATIO:
            raise SecurityError(
                "COMPRESSION_RATIO_EXCEEDED",
                f"Compression ratio {ratio:.0f}:1 exceeds limit "
                f"{settings.MAX_ZIP_RATIO}:1 (possible decompression bomb).",
            )


def extract_zip_safely(zip_path: Path, dest_root: Path) -> Tuple[List[str], List[dict]]:
    """Extract zip_path into dest_root with per-entry validation.

    Returns (extracted_relative_paths, rejected_entries).
    Never uses extractall(); every target path is re-checked after join.
    """
    dest_root.mkdir(parents=True, exist_ok=True)
    extracted: List[str] = []
    rejected: List[dict] = []
    seen_names = set()
    written_bytes = 0
    max_bytes = settings.MAX_ZIP_UNCOMPRESSED_MB * 1024 * 1024

    with zipfile.ZipFile(zip_path, "r") as zf:
        infos = zf.infolist()
        check_zip_limits(infos)

        for info in infos:
            try:
                validate_zip_entry(info)
            except SecurityError as exc:
                rejected.append({"entry": info.filename, "code": exc.code, "reason": exc.message})
                continue

            norm = info.filename.replace("\\", "/").lstrip("./")
            # Duplicate names (case-insensitive: Windows FS) -> disambiguate.
            key = norm.lower().rstrip("/")
            if key in seen_names and not info.is_dir():
                stem, dot, ext = norm.rpartition("/")
                stem = stem + "/" if dot else ""
                base = Path(norm).stem
                suffix = Path(norm).suffix
                n = 1
                candidate = f"{stem}{base}({n}){suffix}"
                while candidate.lower() in seen_names:
                    n += 1
                    candidate = f"{stem}{base}({n}){suffix}"
                rejected.append(
                    {
                        "entry": info.filename,
                        "code": "DUPLICATE_NAME",
                        "reason": f"Duplicate entry renamed to {candidate}",
                    }
                )
                norm = candidate
                key = norm.lower()
            seen_names.add(key)

            target = safe_join(dest_root, *norm.split("/"))

            if info.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue

            target.parent.mkdir(parents=True, exist_ok=True)
            # Stream with a running byte budget (guards against lying headers).
            try:
                with zf.open(info, "r") as src, open(target, "wb") as dst:
                    while True:
                        chunk = src.read(1024 * 1024)
                        if not chunk:
                            break
                        written_bytes += len(chunk)
                        if written_bytes > max_bytes:
                            target.unlink(missing_ok=True)
                            raise SecurityError(
                                "EXTRACTED_SIZE_EXCEEDED",
                                f"Extraction exceeded {max_bytes} bytes; archive rejected.",
                            )
                        dst.write(chunk)
            except SecurityError:
                raise
            except Exception as exc:  # corrupt/deflated entry: report, never crash
                target.unlink(missing_ok=True)
                rejected.append(
                    {
                        "entry": info.filename,
                        "code": "CORRUPT_ENTRY",
                        "reason": f"Could not extract entry: {type(exc).__name__}",
                    }
                )
                continue
            extracted.append(norm)

    return extracted, rejected
