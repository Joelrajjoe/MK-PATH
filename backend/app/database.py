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

# Logical collections required by the specification (Phase 3 & Option B).
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
    "pmsg_runs",
    "fib_vg_runs",
    "fib_vg_scenario_results",
    "fib_vg_audit_events",
    "attestation_envelopes",
    "lineage_events",
    "lineage_checkpoints",
]

# Indexes are created ONLY where justified by a concrete query pattern:
# - audit_events: audit trail is read in reverse chronological order.
# - agent_runs: agent run listings are read in reverse chronological order.
# - ontology: semantic contexts are always fetched by dataset (latest first).
# - clarification_questions: open questions are polled per dataset and status.
# - pmsg_runs: robustness analysis runs indexed by project, dataset, and creation time.
# - fib_vg_runs: benchmark runs indexed by project and creation time.
# - fib_vg_scenario_results: scenario outcomes indexed by run_id and scenario_id.
# - fib_vg_audit_events: benchmark audit trails indexed by run_id and timestamp.
# - attestation_envelopes: envelopes indexed by envelope_id, project_id, and created_at.
# - lineage_events: event chain indexed by run_id and sequence_number.
# - lineage_checkpoints: chain checkpoints indexed by chain_id and checkpoint_id.
# All other collections are write-first with no established read pattern yet,
# so no indexes are created (indexes cost write throughput and storage).
JUSTIFIED_INDEXES: Dict[str, List[Any]] = {
    "audit_events": [("created_at", -1)],
    "agent_runs": [("created_at", -1)],
    "ontology": [("dataset_id", 1), ("created_at", -1)],
    "clarification_questions": [("dataset_id", 1), ("status", 1), ("created_at", -1)],
    "pmsg_runs": [("project_id", 1), ("dataset_id", 1), ("created_at", -1)],
    "fib_vg_runs": [("project_id", 1), ("created_at", -1)],
    "fib_vg_scenario_results": [("run_id", 1), ("scenario_id", 1)],
    "fib_vg_audit_events": [("run_id", 1), ("created_at", -1)],
    "attestation_envelopes": [("envelope_id", 1), ("project_id", 1), ("created_at", -1)],
    "lineage_events": [("run_id", 1), ("sequence_number", 1)],
    "lineage_checkpoints": [("chain_id", 1), ("checkpoint_id", 1)],
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

    async def to_list(self, length: Optional[int] = None) -> List[Dict[str, Any]]:
        end = self._skip_count + (min(self._limit_count, length) if length is not None else self._limit_count)
        sliced = self._docs[self._skip_count:end]
        return [self._apply_projection(d) for d in sliced]

    def _apply_projection(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        if not self._projection:
            return dict(doc)
        out = dict(doc)
        for k, v in self._projection.items():
            if v == 0 and k in out:
                out.pop(k)
        return out


class LocalDeleteResult:
    """Mimics PyMongo/Motor DeleteResult."""

    def __init__(self, deleted_count: int = 0, acknowledged: bool = True):
        self.deleted_count = deleted_count
        self.acknowledged = acknowledged

    @property
    def raw_result(self) -> Dict[str, Any]:
        return {"n": self.deleted_count, "ok": 1.0}


class LocalUpdateResult:
    """Mimics PyMongo/Motor UpdateResult."""

    def __init__(
        self,
        matched_count: int = 0,
        modified_count: int = 0,
        upserted_id: Any = None,
        acknowledged: bool = True,
        doc: Optional[Dict[str, Any]] = None,
    ):
        self.matched_count = matched_count
        self.modified_count = modified_count
        self.upserted_id = upserted_id
        self.acknowledged = acknowledged
        self._doc = doc or {}

    @property
    def raw_result(self) -> Dict[str, Any]:
        return {
            "n": self.matched_count,
            "nModified": self.modified_count,
            "upserted": self.upserted_id,
            "ok": 1.0,
        }

    def __getitem__(self, key: str) -> Any:
        return self._doc[key]

    def get(self, key: str, default: Any = None) -> Any:
        return self._doc.get(key, default)


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
            if k == "$or" and isinstance(v, list):
                if not any(self._matches(doc, cond) for cond in v):
                    return False
                continue
            if k == "$and" and isinstance(v, list):
                if not all(self._matches(doc, cond) for cond in v):
                    return False
                continue
            if k.startswith("$"):
                continue

            doc_val = doc.get(k)
            if isinstance(v, dict):
                matched_ops = True
                for op, val in v.items():
                    if op == "$in":
                        if doc_val not in val:
                            matched_ops = False
                            break
                    elif op == "$nin":
                        if doc_val in val:
                            matched_ops = False
                            break
                    elif op == "$ne":
                        if doc_val == val:
                            matched_ops = False
                            break
                    elif op == "$gt":
                        if doc_val is None or not (doc_val > val):
                            matched_ops = False
                            break
                    elif op == "$gte":
                        if doc_val is None or not (doc_val >= val):
                            matched_ops = False
                            break
                    elif op == "$lt":
                        if doc_val is None or not (doc_val < val):
                            matched_ops = False
                            break
                    elif op == "$lte":
                        if doc_val is None or not (doc_val <= val):
                            matched_ops = False
                            break
                    elif op == "$exists":
                        if (k in doc) != bool(val):
                            matched_ops = False
                            break
                if not matched_ops:
                    return False
                continue

            if doc_val is None and v is not None:
                return False
            if type(doc_val) is bool or type(v) is bool:
                if doc_val is not v:
                    return False
            elif str(doc_val) != str(v) and doc_val != v:
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

    async def delete_one(self, query: Dict[str, Any]) -> LocalDeleteResult:
        docs = self._read_docs()
        found_idx = -1
        for i, d in enumerate(docs):
            if self._matches(d, query):
                found_idx = i
                break
        if found_idx >= 0:
            docs.pop(found_idx)
            self._write_docs(docs)
            return LocalDeleteResult(deleted_count=1, acknowledged=True)
        return LocalDeleteResult(deleted_count=0, acknowledged=True)

    async def delete_many(self, query: Dict[str, Any]) -> LocalDeleteResult:
        docs = self._read_docs()
        kept = []
        deleted_count = 0
        for d in docs:
            if self._matches(d, query):
                deleted_count += 1
            else:
                kept.append(d)
        if deleted_count > 0:
            self._write_docs(kept)
        return LocalDeleteResult(deleted_count=deleted_count, acknowledged=True)

    async def find_one_and_delete(
        self,
        query: Dict[str, Any],
        projection: Optional[Dict[str, Any]] = None,
        sort: Any = None
    ) -> Optional[Dict[str, Any]]:
        docs = self._read_docs()
        filtered_indices = [i for i, d in enumerate(docs) if self._matches(d, query)]
        if not filtered_indices:
            return None
        if sort:
            cursor = LocalFallbackCursor([docs[i] for i in filtered_indices])
            cursor.sort(sort)
            chosen_doc = cursor._docs[0] if cursor._docs else None
            if chosen_doc:
                for idx in filtered_indices:
                    if docs[idx] == chosen_doc or docs[idx].get("_id") == chosen_doc.get("_id"):
                        target_idx = idx
                        break
                else:
                    target_idx = filtered_indices[0]
            else:
                target_idx = filtered_indices[0]
        else:
            target_idx = filtered_indices[0]

        deleted_doc = docs.pop(target_idx)
        self._write_docs(docs)
        if projection:
            cursor = LocalFallbackCursor([deleted_doc], projection)
            return cursor._apply_projection(deleted_doc)
        return deleted_doc

    async def update_one(self, query: Dict[str, Any], update: Dict[str, Any], upsert: bool = False) -> LocalUpdateResult:
        docs = self._read_docs()
        set_fields = update.get("$set", {})
        inc_fields = update.get("$inc", {})
        unset_fields = update.get("$unset", {})
        matched = 0
        modified = 0
        for d in docs:
            if self._matches(d, query):
                matched = 1
                for k, v in set_fields.items():
                    d[k] = v
                    modified = 1
                for k, v in inc_fields.items():
                    d[k] = d.get(k, 0) + v
                    modified = 1
                for k in unset_fields.keys():
                    if k in d:
                        del d[k]
                        modified = 1
                break
        if matched == 0 and upsert:
            new_doc = dict(query)
            if "_id" not in new_doc:
                new_doc["_id"] = str(uuid.uuid4().hex)
            for k, v in set_fields.items():
                new_doc[k] = v
            for k, v in inc_fields.items():
                new_doc[k] = v
            docs.append(new_doc)
            self._write_docs(docs)
            return LocalUpdateResult(matched_count=0, modified_count=0, upserted_id=new_doc["_id"], acknowledged=True)
        if modified > 0:
            self._write_docs(docs)
        return LocalUpdateResult(matched_count=matched, modified_count=modified, acknowledged=True)

    async def update_many(self, query: Dict[str, Any], update: Dict[str, Any], upsert: bool = False) -> LocalUpdateResult:
        docs = self._read_docs()
        set_fields = update.get("$set", {})
        inc_fields = update.get("$inc", {})
        unset_fields = update.get("$unset", {})
        matched_count = 0
        modified_count = 0
        for d in docs:
            if self._matches(d, query):
                matched_count += 1
                for k, v in set_fields.items():
                    d[k] = v
                    modified_count += 1
                for k, v in inc_fields.items():
                    d[k] = d.get(k, 0) + v
                    modified_count += 1
                for k in unset_fields.keys():
                    if k in d:
                        del d[k]
                        modified_count += 1
        if matched_count == 0 and upsert:
            new_doc = dict(query)
            if "_id" not in new_doc:
                new_doc["_id"] = str(uuid.uuid4().hex)
            for k, v in set_fields.items():
                new_doc[k] = v
            for k, v in inc_fields.items():
                new_doc[k] = v
            docs.append(new_doc)
            self._write_docs(docs)
            return LocalUpdateResult(matched_count=0, modified_count=0, upserted_id=new_doc["_id"], acknowledged=True)
        if modified_count > 0:
            self._write_docs(docs)
        return LocalUpdateResult(matched_count=matched_count, modified_count=modified_count, acknowledged=True)

    async def replace_one(self, query: Dict[str, Any], replacement: Dict[str, Any], upsert: bool = False) -> Any:
        docs = self._read_docs()
        found = False
        for i, d in enumerate(docs):
            if self._matches(d, query):
                rep_copy = dict(replacement)
                if "_id" not in rep_copy and "_id" in d:
                    rep_copy["_id"] = d["_id"]
                docs[i] = rep_copy
                found = True
                break
        if not found and upsert:
            rep_copy = dict(replacement)
            if "_id" not in rep_copy:
                rep_copy["_id"] = str(uuid.uuid4().hex)
            docs.append(rep_copy)
        self._write_docs(docs)
        return replacement

    async def distinct(self, key: str, query: Optional[Dict[str, Any]] = None) -> List[Any]:
        docs = self._read_docs()
        if query:
            docs = [d for d in docs if self._matches(d, query)]
        vals = set()
        for d in docs:
            if key in d and d[key] is not None:
                vals.add(d[key])
        return list(vals)

    async def drop(self) -> None:
        if self.filepath.exists():
            try:
                self.filepath.unlink()
            except Exception:
                pass

    async def create_index(self, keys: Any, **kwargs) -> str:
        return "local_index"


class LocalFallbackDB:
    def __init__(self, metadata_dir: Path):
        self.metadata_dir = metadata_dir
        self.metadata_dir.mkdir(parents=True, exist_ok=True)

    def get_collection(self, name: str) -> LocalFallbackCollection:
        filepath = self.metadata_dir / f"{name}.json"
        return LocalFallbackCollection(name, filepath)

    def __getitem__(self, name: str) -> LocalFallbackCollection:
        return self.get_collection(name)

    async def create_collection(self, name: str):
        filepath = self.metadata_dir / f"{name}.json"
        if not filepath.exists():
            filepath.write_text("[]", encoding="utf-8")

    async def drop_collection(self, name: str) -> None:
        filepath = self.metadata_dir / f"{name}.json"
        if filepath.exists():
            try:
                filepath.unlink()
            except Exception:
                pass

    async def list_collection_names(self) -> List[str]:
        return [p.stem for p in self.metadata_dir.glob("*.json")]


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

    def is_ready(self) -> bool:
        return self._connected and not self._using_fallback

    @property
    def last_error(self) -> Optional[str]:
        return self._last_error

    async def connect(self, force: bool = False) -> bool:
        """Attempt to establish connectivity to MongoDB Atlas.
        If Atlas fails/times out, switch transparently to local file fallback.
        """
        if self._connected and not force:
            return True

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
        self._connected = False
        self._db = self._fallback_db
        self._using_fallback = True

    def get_database(self) -> Any:
        """Database accessor; returns Atlas PyMongo DB or LocalFallbackDB."""
        return self._db if self._db is not None else self._fallback_db

    def get_collection(self, name: str):
        """Collection accessor."""
        if name not in CORE_COLLECTIONS:
            logger.warning("Access to non-declared collection '%s' blocked", name)
            return None
        if self._db is not None and not self._using_fallback and not isinstance(self._db, LocalFallbackDB):
            return self._db[name]
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
