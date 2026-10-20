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
from .routers import stability as stability_router
from .routers import dashboard as dashboard_router
from .routers import benchmark as benchmark_router
from .routers import attestations as attestations_router


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
app.include_router(stability_router.router)
app.include_router(dashboard_router.router)
app.include_router(benchmark_router.router)
app.include_router(attestations_router.router)



@app.get("/api/health/database")
async def health_database(response: Response) -> Dict[str, Any]:
    """MongoDB Atlas / Local Fallback health probe.

    healthy                  -> 200 {"status": "healthy", "database": "mk_path"}
    degraded_local_fallback  -> 200 {"status": "degraded_local_fallback", "database": "local_fallback", "mode": "local_json_fallback"}
    unhealthy                -> 503 {"status": "unhealthy", "reason": "<exception class>"}

    Never exposes credentials, URIs, or usernames.
    """
    payload = await db_manager.health()
    if payload["status"] not in ("healthy", "degraded_local_fallback"):
        response.status_code = 503
    return payload


# --- Frontend Production Distribution Mounting (Single-port Railway / PaaS deployment) ---
import os
from pathlib import Path
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# Check for frontend build directory relative to backend or repo root
possible_dist_paths = [
    Path(__file__).resolve().parent.parent.parent / "frontend" / "dist",
    Path("frontend/dist"),
    Path("/app/frontend/dist"),
]

dist_path = None
for p in possible_dist_paths:
    if p.exists() and (p / "index.html").exists():
        dist_path = p
        break

if dist_path:
    logger.info("Mounting frontend SPA from: %s", dist_path)
    # Mount assets subfolder
    assets_dir = dist_path / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    # Serve manifest, service worker, icons, and SPA fallback
    @app.get("/manifest.json")
    async def get_manifest():
        return FileResponse(dist_path / "manifest.json", media_type="application/manifest+json")

    @app.get("/sw.js")
    async def get_sw():
        return FileResponse(dist_path / "sw.js", media_type="application/javascript")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        # Allow API routes and docs to pass through
        if full_path.startswith("api/") or full_path in ("docs", "openapi.json", "redoc"):
            return Response(status_code=404)
        target = dist_path / full_path
        if target.exists() and target.is_file():
            return FileResponse(target)
        return FileResponse(dist_path / "index.html")
else:
    @app.get("/")
    async def root() -> Dict[str, Any]:
        return {
            "service": "MK-Path API",
            "version": "0.1.0",
            "phase": 3,
            "docs": "/docs",
        }

