"""Project management API routes.

POST /api/projects
GET  /api/projects
GET  /api/projects/{project_id}
"""
import uuid
import logging
from typing import Any, Dict, Optional, List
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field, ConfigDict

from .. import repo
from ..audit import record_audit
from ..database import db_manager
from ..repo import MetadataUnavailable

logger = logging.getLogger("mkpath.projects")

router = APIRouter(prefix="/api/projects", tags=["projects"])


class CreateProjectRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str = Field(..., min_length=1)
    description: Optional[str] = ""
    business_goal: Optional[str] = Field(default="", alias="businessGoal")


def _require_db() -> None:
    if db_manager.get_database() is None:
        raise HTTPException(
            status_code=503,
            detail={"code": "METADATA_UNAVAILABLE", "message": "Metadata store unavailable."},
        )


@router.post("", status_code=201)
async def create_project(body: CreateProjectRequest) -> Dict[str, Any]:
    _require_db()
    project_id = uuid.uuid4().hex
    now = repo.utcnow()

    doc = {
        "project_id": project_id,
        "id": project_id,
        "name": body.name,
        "description": body.description or "",
        "business_goal": body.business_goal or "",
        "businessGoal": body.business_goal or "",
        "status": "active",
        "dataset_count": 0,
        "datasetCount": 0,
        "model_count": 0,
        "modelCount": 0,
        "created_at": now.isoformat(),
        "last_run": None,
    }

    try:
        await repo.insert_project(doc)
    except MetadataUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    await record_audit(
        "project_created",
        status="ok",
        project_id=project_id,
        details={"name": body.name, "business_goal": body.business_goal},
    )

    return doc


@router.get("")
async def list_projects(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> List[Dict[str, Any]]:
    _require_db()
    try:
        items = await repo.list_projects(limit=limit, offset=offset)
        return items
    except MetadataUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@router.get("/{project_id}")
async def get_project(project_id: str) -> Dict[str, Any]:
    _require_db()
    try:
        doc = await repo.get_project(project_id)
        if not doc:
            raise HTTPException(status_code=404, detail="Project not found.")
        return doc
    except MetadataUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc))
