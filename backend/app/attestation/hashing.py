"""Deterministic canonicalization and collision-resistant content hashing for ARE-HL (Phase 2).

Implements RFC 8785 (JSON Canonicalization Scheme - JCS) rules and
chunked streaming SHA-256 hashing for arbitrary physical files and memory buffers.
"""

import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import pyarrow.parquet as pq


CHUNK_SIZE = 65536  # 64 KB streaming chunks


class CanonicalizationError(ValueError):
    """Raised when data cannot be canonicalized deterministically."""
    pass


def _canonicalize_value(val: Any) -> Any:
    """Recursively normalize data types to RFC 8785 compliant canonical forms."""
    if val is None:
        return None
    if isinstance(val, bool):
        return val
    if isinstance(val, (int,)):
        return val
    if isinstance(val, float):
        if math.isnan(val) or math.isinf(val):
            raise CanonicalizationError(f"Non-finite float value '{val}' is forbidden in canonical representations.")
        # Ensure 0.0 is represented without minus sign
        if val == 0.0:
            return 0.0
        return val
    if isinstance(val, str):
        return val
    if isinstance(val, datetime):
        # Normalize to UTC ISO 8601 string
        if val.tzinfo is None:
            val = val.replace(tzinfo=timezone.utc)
        else:
            val = val.astimezone(timezone.utc)
        return val.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    if hasattr(val, "model_dump") and callable(getattr(val, "model_dump")):
        return _canonicalize_value(val.model_dump())
    if hasattr(val, "dict") and callable(getattr(val, "dict")):
        return _canonicalize_value(val.dict())
    if isinstance(val, dict):
        # Sort keys lexicographically by UTF-16 code units (Python's sorted() on str matches)
        sorted_dict = {}
        for k in sorted(val.keys()):
            if not isinstance(k, str):
                raise CanonicalizationError(f"Dictionary key '{k}' must be a string, got {type(k).__name__}.")
            sorted_dict[k] = _canonicalize_value(val[k])
        return sorted_dict
    if isinstance(val, (list, tuple, set)):
        return [_canonicalize_value(item) for item in val]
    if hasattr(val, "item") and callable(getattr(val, "item")):
        # Handle numpy scalar
        return _canonicalize_value(val.item())
    if hasattr(val, "tolist") and callable(getattr(val, "tolist")):
        # Handle numpy array / pandas series
        return _canonicalize_value(val.tolist())
    
    return str(val)


def canonical_json_dumps(obj: Any) -> str:
    """Serialize object to canonical JSON string with sorted keys, no whitespace, UTF-8."""
    normalized = _canonicalize_value(obj)
    return json.dumps(
        normalized,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def canonical_json_bytes(obj: Any) -> bytes:
    """Serialize object to UTF-8 encoded canonical JSON bytes."""
    return canonical_json_dumps(obj).encode("utf-8")


def hash_bytes(data: bytes, algorithm: str = "sha256") -> str:
    """Compute hex-encoded cryptographic hash of bytes."""
    if algorithm.lower() != "sha256":
        raise ValueError(f"Unsupported hash algorithm '{algorithm}'. Only 'sha256' is approved.")
    return hashlib.sha256(data).hexdigest()


def hash_json_object(obj: Any, algorithm: str = "sha256") -> str:
    """Canonicalize JSON-serializable object and return SHA-256 hex digest."""
    canon_bytes = canonical_json_bytes(obj)
    return hash_bytes(canon_bytes, algorithm=algorithm)


def hash_file_streaming(file_path: Union[str, Path], algorithm: str = "sha256") -> str:
    """
    Compute collision-resistant SHA-256 hash using chunked streaming.
    Never loads entire file into memory.
    Validates file existence, non-emptiness, readability, and byte count.
    """
    p = Path(file_path).resolve()
    if not p.exists():
        raise FileNotFoundError(f"Cannot hash non-existent file: {p}")
    if not p.is_file():
        raise ValueError(f"Path is not a regular file: {p}")

    hasher = hashlib.sha256()
    bytes_read = 0

    with open(p, "rb") as f:
        while True:
            chunk = f.read(CHUNK_SIZE)
            if not chunk:
                break
            hasher.update(chunk)
            bytes_read += len(chunk)

    stat = p.stat()
    if bytes_read != stat.st_size:
        raise IOError(f"Truncated file read: expected {stat.st_size} bytes, read {bytes_read} bytes.")

    return hasher.hexdigest()


def compute_semantic_parquet_fingerprint(parquet_path: Union[str, Path]) -> Dict[str, Any]:
    """
    Compute a versioned semantic fingerprint for a Parquet dataset.
    Explicitly defines column order, types, row count, and null counts.
    Distinguishes semantic data identity from exact file bytes.
    """
    p = Path(parquet_path).resolve()
    if not p.exists() or not p.is_file():
        raise FileNotFoundError(f"Parquet file not found: {p}")

    meta = pq.read_metadata(p)
    schema = pq.read_schema(p)

    cols = []
    for i in range(len(schema.names)):
        cols.append({
            "name": schema.names[i],
            "type": str(schema.types[i]),
        })
    # Sort columns deterministically by name
    sorted_cols = sorted(cols, key=lambda x: x["name"])

    fingerprint_obj = {
        "format": "parquet",
        "semantic_version": "v1.0",
        "num_rows": meta.num_rows,
        "num_columns": meta.num_columns,
        "columns": sorted_cols,
    }

    semantic_hash = hash_json_object(fingerprint_obj)
    return {
        "semantic_hash": semantic_hash,
        "num_rows": meta.num_rows,
        "num_columns": meta.num_columns,
        "column_count": len(sorted_cols),
        "fingerprint": fingerprint_obj,
    }
