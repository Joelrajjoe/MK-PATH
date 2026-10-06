"""MK-Path API - application entry point (Phase 3 foundation).

Startup policy (spec section 5 / Phase 3):
- MongoDB configuration problems must NOT crash startup. Connection and
  collection bootstrap are attempted once, failures are logged, and the
  API serves a degraded-but-alive status.
- No credentials are ever returned in responses.
"""
import logging
from contextlib import asynccontextmanager
from typing import Any, Dict

from fastapi import FastAPI, Response

from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .database import db_manager
from .routers import datasets as datasets_router
from .routers import semantic as semantic_router
from .routers import runs as runs_router
from .routers import projects as projects_router
from .routers import pipeline as pipeline_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mkpath.main")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Non-fatal startup: attempt connection + collection baseline once.
    connected = await db_manager.connect()
    if connected:
        try:
            bootstrap = await db_manager.ensure_collections()
            logger.info(
                "Collection baseline: created=%s existed=%s errors=%s",
                bootstrap.get("created"),
                bootstrap.get("already_existed"),
                bootstrap.get("errors"),
            )
        except Exception as exc:  # startup must never crash
            logger.warning("Collection bootstrap failed: %s", type(exc).__name__)
    else:
        logger.warning(
            "MongoDB not reachable at startup (%s); API will run degraded.",
            db_manager.last_error,
        )
    yield
    await db_manager.close()


app = FastAPI(
    title="MK-Path API",
    description=(
        "Multi-agent Knowledge Platform for Autonomous Transformation & Healing "
        "- Evidence-Gated Autonomous Data Transformation."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(projects_router.router)
app.include_router(datasets_router.router)
app.include_router(semantic_router.router)
app.include_router(runs_router.router)
app.include_router(pipeline_router.router)


@app.get("/")
async def root() -> Dict[str, Any]:
    return {
        "service": "MK-Path API",
        "version": "0.1.0",
        "phase": 3,
        "docs": "/docs",
    }


@app.get("/api/health/database")
async def health_database(response: Response) -> Dict[str, Any]:
    """MongoDB Atlas health probe.

    healthy   -> 200 {"status": "healthy", "database": "mk_path"}
    degraded  -> 503 {"status": "unhealthy", "database": "mk_path", "reason": "<exception class>"}

    Never exposes credentials, URIs, or usernames.
    """
    payload = await db_manager.health()
    if payload["status"] != "healthy":
        response.status_code = 503
    return payload
