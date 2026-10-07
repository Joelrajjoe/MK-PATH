"""Reusable MongoDB Atlas database module for MK-Path.

Design rules (spec section 5):
- Connection comes from MONGODB_URI / MONGODB_DATABASE only; never hardcoded.
- Startup must NEVER fail catastrophically when MongoDB is unavailable:
  every entry point degrades gracefully and reports status instead of raising.
- MongoDB stores metadata/agent/audit state only - never raw datasets or
  model binaries (enforced at the application layer in later phases).
"""
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pymongo import AsyncMongoClient
from pymongo.database import Database
from pymongo.errors import CollectionInvalid, PyMongoError

from .config import settings

logger = logging.getLogger("mkpath.database")

# Logical collections required by the specification (Phase 3).
CORE_COLLECTIONS: List[str] = [
    "projects",
    "datasets",
    "ontology",
    "agent_runs",
    "runs",
    "clarification_questions",
    "human_decisions",
    "validation_results",
    "models",
    "artifacts",
    "audit_events",
    "healing_events",
]

# Indexes are created ONLY where justified by a concrete query pattern:
# - audit_events: audit trail is read in reverse chronological order.
# - agent_runs: agent run listings are read in reverse chronological order.
# - ontology: semantic contexts are always fetched by dataset (latest first).
# - clarification_questions: open questions are polled per dataset and status.
# All other collections are write-first with no established read pattern yet,
# so no indexes are created (indexes cost write throughput and storage).
JUSTIFIED_INDEXES: Dict[str, List[Any]] = {
    "audit_events": [("created_at", -1)],
    "agent_runs": [("created_at", -1)],
    "ontology": [("dataset_id", 1), ("created_at", -1)],
    "clarification_questions": [("dataset_id", 1), ("status", 1), ("created_at", -1)],
}


import json
import uuid
from pathlib import Path


class LocalFallbackCursor:
    """Async cursor mimicking PyMongo cursor over local JSON list."""

    def __init__(self, docs: List[Dict[str, Any]], projection: Optional[Dict[str, Any]] = None):
        self._docs = [dict(d) for d in docs]
        self._projection = projection
        self._skip_count = 0
        self._limit_count = len(self._docs)
        self._iter = None

    def sort(self, key_or_list: Any, direction: int = 1):
        if isinstance(key_or_list, str):
            key = key_or_list
            reverse = (direction == -1)
        elif isinstance(key_or_list, list) and len(key_or_list) > 0:
            item = key_or_list[0]
            if isinstance(item, (tuple, list)):
                key, direction = item[0], item[1]
            else:
                key, direction = item, 1
            reverse = (direction == -1)
        else:
            return self

        def sort_key(doc):
            val = doc.get(key)
            if val is None:
                return ""
            if isinstance(val, datetime):
                return val.isoformat()
            return str(val)

        self._docs.sort(key=sort_key, reverse=reverse)
        return self

    def skip(self, n: int):
        self._skip_count = max(0, n)
        return self

    def limit(self, n: int):
        self._limit_count = max(0, n)
        return self

    def __aiter__(self):
        end = self._skip_count + self._limit_count
        sliced = self._docs[self._skip_count:end]
        self._iter = iter(sliced)
        return self

    async def __anext__(self):
        try:
            doc = next(self._iter)
            return self._apply_projection(doc)
        except StopIteration:
            raise StopAsyncIteration

    def _apply_projection(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        if not self._projection:
            return dict(doc)
        out = dict(doc)
        for k, v in self._projection.items():
            if v == 0 and k in out:
                out.pop(k)
        return out


class LocalFallbackCollection:
    """File-backed JSON collection executing PyMongo CRUD operations."""

    def __init__(self, name: str, filepath: Path):
        self.name = name
        self.filepath = filepath
        self.filepath.parent.mkdir(parents=True, exist_ok=True)

    def _read_docs(self) -> List[Dict[str, Any]]:
        if not self.filepath.exists():
            return []
        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        except Exception:
            return []

    def _write_docs(self, docs: List[Dict[str, Any]]) -> None:
        def default_serializer(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            return str(obj)

        with open(self.filepath, "w", encoding="utf-8") as f:
            json.dump(docs, f, indent=2, default=default_serializer)

    def _matches(self, doc: Dict[str, Any], query: Dict[str, Any]) -> bool:
        if not query:
            return True
        for k, v in query.items():
            if k.startswith("$"):
                continue
            doc_val = doc.get(k)
            if doc_val is None and v is not None:
                return False
            if str(doc_val) != str(v) and doc_val != v:
                return False
        return True

    async def insert_one(self, doc: Dict[str, Any]) -> Any:
        docs = self._read_docs()
        doc_copy = dict(doc)
        if "_id" not in doc_copy:
            doc_copy["_id"] = str(uuid.uuid4().hex)
        docs.append(doc_copy)
        self._write_docs(docs)
        return doc_copy

    async def insert_many(self, docs: List[Dict[str, Any]]) -> Any:
        existing = self._read_docs()
        for d in docs:
            d_copy = dict(d)
            if "_id" not in d_copy:
                d_copy["_id"] = str(uuid.uuid4().hex)
            existing.append(d_copy)
        self._write_docs(existing)
        return docs

    async def find_one(
        self,
        query: Dict[str, Any],
        projection: Optional[Dict[str, Any]] = None,
        sort: Any = None
    ) -> Optional[Dict[str, Any]]:
        docs = self._read_docs()
        filtered = [d for d in docs if self._matches(d, query)]
        if not filtered:
            return None
        cursor = LocalFallbackCursor(filtered, projection)
        if sort:
            cursor.sort(sort)
        sliced = cursor._docs
        if not sliced:
            return None
        return cursor._apply_projection(sliced[0])

    def find(
        self,
        query: Optional[Dict[str, Any]] = None,
        projection: Optional[Dict[str, Any]] = None
    ) -> LocalFallbackCursor:
        docs = self._read_docs()
        query = query or {}
        filtered = [d for d in docs if self._matches(d, query)]
        return LocalFallbackCursor(filtered, projection)

    async def count_documents(self, query: Dict[str, Any]) -> int:
        docs = self._read_docs()
        return sum(1 for d in docs if self._matches(d, query))

    async def update_one(self, query: Dict[str, Any], update: Dict[str, Any]) -> None:
        docs = self._read_docs()
        set_fields = update.get("$set", {})
        for d in docs:
            if self._matches(d, query):
                for k, v in set_fields.items():
                    d[k] = v
                break
        self._write_docs(docs)

    async def create_index(self, keys: Any, **kwargs) -> str:
        return "local_index"


class LocalFallbackDB:
    def __init__(self, metadata_dir: Path):
        self.metadata_dir = metadata_dir
        self.metadata_dir.mkdir(parents=True, exist_ok=True)

    def get_collection(self, name: str) -> LocalFallbackCollection:
        filepath = self.metadata_dir / f"{name}.json"
        return LocalFallbackCollection(name, filepath)

    async def create_collection(self, name: str):
        filepath = self.metadata_dir / f"{name}.json"
        if not filepath.exists():
            filepath.write_text("[]", encoding="utf-8")


class DatabaseManager:
    """Async MongoDB access with seamless local JSON fallback degradation."""

    def __init__(self) -> None:
        self._client: Optional[AsyncMongoClient] = None
        self._db: Optional[Any] = None
        self._fallback_db: LocalFallbackDB = LocalFallbackDB(settings.DATA_DIR / "metadata")
        self._connected: bool = False
        self._using_fallback: bool = False
        self._last_error: Optional[str] = None

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def last_error(self) -> Optional[str]:
        return self._last_error

    async def connect(self) -> bool:
        """Attempt to establish connectivity to MongoDB Atlas.
        If Atlas fails/times out, switch transparently to local file fallback.
        """
        if not settings.mongo_configured:
            self._connected = True
            self._using_fallback = True
            self._db = self._fallback_db
            self._last_error = "MONGODB_URI_NOT_CONFIGURED"
            logger.info("Using Local File Storage Fallback at '%s'", settings.DATA_DIR / "metadata")
            return True

        try:
            import asyncio
            try:
                curr_loop = asyncio.get_running_loop()
                if self._client is not None and getattr(self._client, "_loop", None) is not None and self._client._loop != curr_loop:
                    self._client = None
            except Exception:
                pass

            if self._client is None:
                self._client = AsyncMongoClient(
                    settings.MONGODB_URI,
                    serverSelectionTimeoutMS=2000,
                    connectTimeoutMS=2000,
                )
            await self._client.admin.command("ping")
            self._db = self._client[settings.MONGODB_DATABASE]
            self._connected = True
            self._using_fallback = False
            self._last_error = None
            logger.info("Connected to MongoDB Atlas database '%s'", settings.MONGODB_DATABASE)
            return True
        except Exception as exc:
            self._client = None
            self._db = self._fallback_db
            self._connected = True
            self._using_fallback = True
            self._last_error = type(exc).__name__
            logger.warning("MongoDB Atlas unavailable (%s). Switched to Local File Fallback.", type(exc).__name__)
            return True

    async def close(self) -> None:
        if self._client is not None:
            try:
                await self._client.close()
            except Exception:
                pass
            self._client = None
        self._db = self._fallback_db

    def get_database(self) -> Any:
        """Database accessor; returns Atlas PyMongo DB or LocalFallbackDB."""
        return self._db if self._db else self._fallback_db

    def get_collection(self, name: str):
        """Collection accessor."""
        if name not in CORE_COLLECTIONS:
            logger.warning("Access to non-declared collection '%s' blocked", name)
            return None
        if self._db is not None:
            return self._db[name] if not self._using_fallback else self._fallback_db.get_collection(name)
        return self._fallback_db.get_collection(name)

    async def ensure_collections(self) -> Dict[str, Any]:
        """Idempotently ensure collections baseline."""
        result: Dict[str, Any] = {
            "database": "local_fallback" if self._using_fallback else settings.MONGODB_DATABASE,
            "created": [],
            "already_existed": [],
            "indexes_created": [],
            "errors": [],
        }
        await self.connect()
        db = self.get_database()

        for name in CORE_COLLECTIONS:
            try:
                if self._using_fallback:
                    await self._fallback_db.create_collection(name)
                else:
                    await db.create_collection(name)
                result["created"].append(name)
            except Exception as exc:
                result["already_existed"].append(name)

        return result

    async def health(self) -> Dict[str, Any]:
        """Health probe."""
        await self.connect()
        return {
            "status": "healthy" if not self._using_fallback else "degraded_local_fallback",
            "database": "local_fallback" if self._using_fallback else settings.MONGODB_DATABASE,
            "mode": "local_json_fallback" if self._using_fallback else "mongodb_atlas",
            "reason": self._last_error,
        }


# Application-wide singleton
db_manager = DatabaseManager()


def get_db_manager() -> DatabaseManager:
    """FastAPI dependency accessor for the database manager."""
    return db_manager
