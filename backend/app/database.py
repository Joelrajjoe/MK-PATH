"""Reusable MongoDB Atlas database module for MK-Path.

Design rules (spec section 5):
- Connection comes from MONGODB_URI / MONGODB_DATABASE only; never hardcoded.
- Startup must NEVER fail catastrophically when MongoDB is unavailable:
  every entry point degrades gracefully and reports status instead of raising.
- MongoDB stores metadata/agent/audit state only - never raw datasets or
  model binaries (enforced at the application layer in later phases).
"""
import logging
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


class DatabaseManager:
    """Async MongoDB access with graceful degradation on failure."""

    def __init__(self) -> None:
        self._client: Optional[AsyncMongoClient] = None
        self._db: Optional[Database] = None
        self._connected: bool = False
        self._last_error: Optional[str] = None

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def last_error(self) -> Optional[str]:
        """Exception class name only - never includes credentials."""
        return self._last_error

    async def connect(self) -> bool:
        """Attempt to (re)establish connectivity. Never raises.

        Returns True when a ping succeeds, False otherwise.
        """
        if not settings.mongo_configured:
            self._connected = False
            self._last_error = "MONGODB_URI_NOT_CONFIGURED"
            return False

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
                    serverSelectionTimeoutMS=3000,
                    connectTimeoutMS=3000,
                )
            await self._client.admin.command("ping")
            self._db = self._client[settings.MONGODB_DATABASE]
            if not self._connected:
                logger.info(
                    "Connected to MongoDB Atlas database '%s'", settings.MONGODB_DATABASE
                )
            self._connected = True
            self._last_error = None
            return True
        except RuntimeError as exc:
            self._client = None
            self._connected = False
            self._last_error = "RuntimeError"
            return False
        except PyMongoError as exc:
            # Log/record the exception type only; never the URI or credentials.
            self._connected = False
            self._last_error = type(exc).__name__
            logger.warning("MongoDB unavailable: %s", type(exc).__name__)
            return False
        except Exception as exc:  # defensive: startup must never crash
            self._connected = False
            self._last_error = type(exc).__name__
            logger.warning("MongoDB unexpected error: %s", type(exc).__name__)
            return False

    async def close(self) -> None:
        if self._client is not None:
            try:
                # AsyncMongoClient.close() is a coroutine (PyMongo >= 4.18).
                await self._client.close()
            except Exception:
                pass
            self._client = None
            self._db = None
        self._connected = False

    def get_database(self) -> Optional[Database]:
        """Database accessor; None when not connected."""
        return self._db if self._connected else None

    def get_collection(self, name: str):
        """Collection accessor; None when not connected or unknown name."""
        if not self._connected or self._db is None:
            return None
        if name not in CORE_COLLECTIONS:
            logger.warning("Access to non-declared collection '%s' blocked", name)
            return None
        return self._db[name]

    async def ensure_collections(self) -> Dict[str, Any]:
        """Create the logical collections if missing; idempotent; never raises.

        Collections in MongoDB are created implicitly on first write, but we
        materialize them explicitly so the schema baseline is visible and
        verifiable. Only the two justified indexes are ensured.
        """
        result: Dict[str, Any] = {
            "database": settings.MONGODB_DATABASE,
            "created": [],
            "already_existed": [],
            "indexes_created": [],
            "errors": [],
        }
        if not await self.connect() or self._db is None:
            result["errors"].append(self._last_error or "NOT_CONNECTED")
            return result

        for name in CORE_COLLECTIONS:
            try:
                await self._db.create_collection(name)
                result["created"].append(name)
            except CollectionInvalid:
                result["already_existed"].append(name)
            except PyMongoError as exc:
                result["errors"].append(f"{name}: {type(exc).__name__}")

        for name, keys in JUSTIFIED_INDEXES.items():
            try:
                await self._db[name].create_index(keys)
                result["indexes_created"].append(f"{name}{keys}")
            except PyMongoError as exc:
                result["errors"].append(f"index {name}: {type(exc).__name__}")

        return result

    async def health(self) -> Dict[str, Any]:
        """Health probe used by GET /api/health/database. Never raises."""
        ok = await self.connect()
        payload: Dict[str, Any] = {
            "status": "healthy" if ok else "unhealthy",
            "database": settings.MONGODB_DATABASE,
        }
        if not ok:
            # Diagnostic without secrets: config state + exception class only.
            payload["reason"] = self._last_error or "UNKNOWN"
        return payload


# Application-wide singleton
db_manager = DatabaseManager()


def get_db_manager() -> DatabaseManager:
    """FastAPI dependency accessor for the database manager."""
    return db_manager
