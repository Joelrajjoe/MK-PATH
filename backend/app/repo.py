"""MongoDB metadata repository for dataset documents (Phase 4/5)."""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .database import db_manager


class MetadataUnavailable(Exception):
    """Raised when the metadata store cannot accept writes (503 to client)."""


def _require_coll(name: str):
    coll = db_manager.get_collection(name)
    if coll is None:
        raise MetadataUnavailable(
            "Metadata store unavailable; dataset operations require MongoDB."
        )
    return coll


async def insert_dataset(doc: Dict[str, Any]) -> None:
    await _require_coll("datasets").insert_one(dict(doc))


async def insert_datasets(docs: List[Dict[str, Any]]) -> None:
    if docs:
        await _require_coll("datasets").insert_many([dict(d) for d in docs])


async def get_dataset(dataset_id: str) -> Optional[Dict[str, Any]]:
    coll = db_manager.get_collection("datasets")
    if coll is None:
        raise MetadataUnavailable("Metadata store unavailable.")
    return await coll.find_one({"dataset_id": dataset_id}, {"_id": 0})


async def list_datasets(limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
    coll = db_manager.get_collection("datasets")
    if coll is None:
        raise MetadataUnavailable("Metadata store unavailable.")
    cursor = (
        coll.find({}, {"_id": 0})
        .sort("created_at", -1)
        .skip(offset)
        .limit(limit)
    )
    return [doc async for doc in cursor]


async def count_datasets() -> int:
    coll = db_manager.get_collection("datasets")
    if coll is None:
        raise MetadataUnavailable("Metadata store unavailable.")
    return await coll.count_documents({})


async def update_dataset(dataset_id: str, update: Dict[str, Any]) -> None:
    await _require_coll("datasets").update_one(
        {"dataset_id": dataset_id}, {"$set": update}
    )


def utcnow() -> datetime:
    return datetime.now(timezone.utc)

async def insert_human_decision(doc: Dict[str, Any]) -> None:
    doc["timestamp"] = doc.get("timestamp", utcnow())
    await _require_coll("human_decisions").insert_one(dict(doc))

async def get_human_decision(question_id: str) -> Optional[Dict[str, Any]]:
    coll = db_manager.get_collection("human_decisions")
    if coll is None:
        raise MetadataUnavailable("Metadata store unavailable.")
    return await coll.find_one({"question_id": question_id}, {"_id": 0})


async def insert_project(doc: Dict[str, Any]) -> None:
    await _require_coll("projects").insert_one(dict(doc))


async def get_project(project_id: str) -> Optional[Dict[str, Any]]:
    coll = db_manager.get_collection("projects")
    if coll is None:
        raise MetadataUnavailable("Metadata store unavailable.")
    return await coll.find_one({"project_id": project_id}, {"_id": 0})


async def list_projects(limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
    coll = db_manager.get_collection("projects")
    if coll is None:
        raise MetadataUnavailable("Metadata store unavailable.")
    cursor = (
        coll.find({}, {"_id": 0})
        .sort("created_at", -1)
        .skip(offset)
        .limit(limit)
    )
    return [doc async for doc in cursor]


async def count_projects() -> int:
    coll = db_manager.get_collection("projects")
    if coll is None:
        raise MetadataUnavailable("Metadata store unavailable.")
    return await coll.count_documents({})

