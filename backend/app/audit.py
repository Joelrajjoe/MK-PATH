"""Audit trail helpers (spec: all important operations generate an audit event)."""
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from .database import db_manager

logger = logging.getLogger("mkpath.audit")


async def record_audit(
    event_type: str,
    *,
    status: str = "ok",
    upload_id: Optional[str] = None,
    dataset_id: Optional[str] = None,
    project_id: Optional[str] = None,
    run_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    **kwargs: Any,
) -> bool:
    """Insert one audit event. Never raises; never records credentials.

    Returns True when the event was persisted, False when the metadata
    store is unavailable (audit loss is logged, not fatal to the request).
    """
    coll = db_manager.get_collection("audit_events")
    doc: Dict[str, Any] = {
        "event_type": event_type,
        "status": status,
        "created_at": datetime.now(timezone.utc),
    }
    if upload_id:
        doc["upload_id"] = upload_id
    if dataset_id:
        doc["dataset_id"] = dataset_id
    if project_id:
        doc["project_id"] = project_id
    if run_id:
        doc["run_id"] = run_id
    if details:
        doc["details"] = details
    for k, v in kwargs.items():
        if v is not None:
            doc[k] = v
    if coll is None:
        logger.warning("Audit store unavailable; event '%s' NOT persisted.", event_type)
        return False
    try:
        await coll.insert_one(doc)
        return True
    except Exception as exc:
        logger.warning(
            "Audit insert failed (%s): %s", event_type, type(exc).__name__
        )
        return False
