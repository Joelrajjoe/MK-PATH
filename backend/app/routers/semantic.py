"""Semantic knowledge layer API routes (Phase 6).

POST /api/datasets/{id}/semantic              build context (may INTERRUPT)
GET  /api/datasets/{id}/semantic              latest context
GET  /api/datasets/{id}/semantic/ambiguities  open ambiguities + questions
GET  /api/clarifications                      list clarification questions
POST /api/clarifications/{qid}/resolve        apply a user decision
"""
import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from ..database import db_manager
from ..repo import MetadataUnavailable
from ..semantic import service
from ..semantic.models import new_id

logger = logging.getLogger("mkpath.semantic.api")

router = APIRouter(tags=["semantic"])


class SemanticBuildRequest(BaseModel):
    business_goal: Optional[str] = None


class ResolveRequest(BaseModel):
    choice: str
    note: Optional[str] = None
    answered_by: Optional[str] = "system_user"


def _require_db() -> None:
    if db_manager.get_database() is None:
        raise HTTPException(
            status_code=503,
            detail={"code": "METADATA_UNAVAILABLE", "message": "Metadata store unavailable."},
        )


def _map_service_errors(exc: Exception) -> HTTPException:
    if isinstance(exc, LookupError):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, RuntimeError):
        return HTTPException(status_code=409, detail=str(exc))
    if isinstance(exc, ValueError):
        return HTTPException(status_code=422, detail=str(exc))
    if isinstance(exc, MetadataUnavailable):
        return HTTPException(status_code=503, detail=str(exc))
    import traceback
    logger.error("Semantic API error: %s\n%s", exc, traceback.format_exc())
    return HTTPException(status_code=500, detail=f"Unexpected error: {type(exc).__name__}: {exc}")


async def _dataset_or_404(dataset_id: str) -> Dict[str, Any]:
    from .. import repo

    doc = await repo.get_dataset(dataset_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Dataset not found.")
    return doc


@router.post("/api/datasets/{dataset_id}/semantic", status_code=201)
async def build_semantic_context(
    dataset_id: str, body: Optional[SemanticBuildRequest] = None
) -> Dict[str, Any]:
    _require_db()
    dataset = await _dataset_or_404(dataset_id)
    business_goal = (body.business_goal or None) if body else None
    try:
        return await service.build_and_store(dataset, business_goal)
    except Exception as exc:
        raise _map_service_errors(exc)


@router.get("/api/datasets/{dataset_id}/semantic")
async def get_semantic_context(dataset_id: str) -> Dict[str, Any]:
    _require_db()
    await _dataset_or_404(dataset_id)
    try:
        ctx = await service.get_latest_context(dataset_id)
    except Exception as exc:
        raise _map_service_errors(exc)
    if ctx is None:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "NO_SEMANTIC_CONTEXT",
                "message": "No semantic context yet. Run POST "
                f"/api/datasets/{dataset_id}/semantic first.",
            },
        )
    return ctx


@router.get("/api/datasets/{dataset_id}/semantic/ambiguities")
async def get_ambiguities(dataset_id: str, status: str = Query("open")) -> Dict[str, Any]:
    _require_db()
    await _dataset_or_404(dataset_id)
    try:
        ctx = await service.get_latest_context(dataset_id)
    except Exception as exc:
        raise _map_service_errors(exc)
    if ctx is None:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "NO_SEMANTIC_CONTEXT",
                "message": "No semantic context yet. Run POST "
                f"/api/datasets/{dataset_id}/semantic first.",
            },
        )
    open_ambs = [a for a in ctx.get("ambiguities", []) if a.get("status") == status]
    return {
        "dataset_id": dataset_id,
        "workflow_status": ctx.get("workflow_status"),
        "confidence": ctx.get("confidence"),
        "threshold": None,
        "ambiguities": open_ambs,
        "questions": [
            {
                "question_id": a.get("question_id"),
                "kind": a.get("kind"),
                "question": a.get("question"),
                "options": a.get("options", []),
                "allows_free_text": a.get("allows_free_text", False),
            }
            for a in open_ambs
            if a.get("question_id")
        ],
    }


@router.get("/api/clarifications")
async def list_clarifications(
    dataset_id: Optional[str] = Query(None),
    status: str = Query("open"),
    limit: int = Query(50, ge=1, le=200),
) -> Dict[str, Any]:
    _require_db()
    query: Dict[str, Any] = {"status": status}
    if dataset_id:
        query["dataset_id"] = dataset_id
    try:
        coll = db_manager.get_collection("clarification_questions")
        if coll is None:
            raise MetadataUnavailable("Metadata store unavailable.")
        cursor = coll.find(query, {"_id": 0}).sort("created_at", -1).limit(limit)
        items = [doc async for doc in cursor]
    except Exception as exc:
        raise _map_service_errors(exc)
    return {"items": items, "total": len(items), "status": status}


@router.post("/api/clarifications/{question_id}/resolve")
async def resolve_clarification(question_id: str, body: ResolveRequest) -> Dict[str, Any]:
    _require_db()
    try:
        return await service.resolve_question(question_id, body.choice, body.note, body.answered_by)
    except Exception as exc:
        raise _map_service_errors(exc)
