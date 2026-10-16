"""FastAPI router for Attested Result Envelopes and Healing Lineage (Phase 9).

Endpoints:
- POST /api/attestations: create an envelope
- GET  /api/attestations: list envelopes for a project
- GET  /api/attestations/{envelope_id}: retrieve envelope
- POST /api/attestations/{envelope_id}/verify: independently reverify envelope
- GET  /api/lineage/runs/{run_id}: get lineage events
- POST /api/lineage/runs/{run_id}/verify: verify lineage event chain
- POST /api/lineage/runs/{run_id}/checkpoint: issue signed checkpoint
- GET  /api/artifacts/{project_id}/{run_id}/verify: verify artifact hashes before deploy/download
- GET  /api/attestations/keys/public: get public verification keys
- POST /api/attestations/keys/revoke: revoke key (authorized administrative workflow)
"""

import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from ..attestation.crypto import key_manager
from ..attestation.lineage import lineage_tracker
from ..attestation.models import (
    AttestedResultEnvelope,
    ChainCheckpoint,
    EnvelopeVerificationReport,
    IntegrityStatus,
    LineageEvent,
)
from ..attestation.service import (
    AtlasPersistenceError,
    AttestationGateFailureError,
    attestation_service,
)
from ..database import db_manager
from ..engineering.ml_engineer import verify_artifact_deployment_readiness

logger = logging.getLogger("mkpath.attestation.router")

router = APIRouter(prefix="/api/attestations", tags=["attestations"])


class CreateEnvelopeRequest(BaseModel):
    project_id: str
    run_id: str
    source_dataset_id: str
    source_storage_reference: str
    verification_report: Dict[str, Any]
    analysis_result: Dict[str, Any]
    healing_event: Optional[Dict[str, Any]] = None
    artifact_meta: Optional[Dict[str, Any]] = None
    require_atlas: bool = False


class RevokeKeyRequest(BaseModel):
    key_id: str
    reason: str = "Administrative revocation"


@router.post("", status_code=status.HTTP_201_CREATED, response_model=AttestedResultEnvelope)
async def create_attestation(req: CreateEnvelopeRequest) -> AttestedResultEnvelope:
    """Create, cryptographically seal, and persist an Attested Result Envelope."""
    try:
        envelope = await attestation_service.create_envelope_for_run(
            project_id=req.project_id,
            run_id=req.run_id,
            source_dataset_id=req.source_dataset_id,
            source_storage_reference=req.source_storage_reference,
            verification_report=req.verification_report,
            analysis_result=req.analysis_result,
            healing_event=req.healing_event,
            artifact_meta=req.artifact_meta,
            require_atlas=req.require_atlas,
        )
        return envelope
    except AtlasPersistenceError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "ATLAS_PERSISTENCE_REQUIRED", "message": str(exc)},
        )
    except Exception as exc:
        logger.error("Failed to create attestation envelope: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Envelope creation failed: {type(exc).__name__}: {exc}",
        )


@router.get("", response_model=List[Dict[str, Any]])
async def list_attestations(
    project_id: str = Query(..., description="Project ID to filter envelopes"),
) -> List[Dict[str, Any]]:
    """List all envelopes for an authorized project."""
    return await attestation_service.list_envelopes_for_project(project_id)


@router.get("/{envelope_id}", response_model=AttestedResultEnvelope)
async def get_attestation(envelope_id: str) -> AttestedResultEnvelope:
    """Retrieve an Attested Result Envelope by ID."""
    envelope = await attestation_service.get_envelope(envelope_id)
    if not envelope:
        raise HTTPException(status_code=404, detail=f"Attestation envelope '{envelope_id}' not found.")
    return envelope


@router.post("/{envelope_id}/verify", response_model=EnvelopeVerificationReport)
async def verify_attestation(envelope_id: str) -> EnvelopeVerificationReport:
    """
    Independently reverify an envelope's signature, payload hash, physical file hashes,
    and verification gate outcomes.
    """
    report = await attestation_service.verify_envelope_by_id(envelope_id)
    return report


@router.get("/lineage/runs/{run_id}", response_model=List[LineageEvent])
async def get_run_lineage(run_id: str) -> List[LineageEvent]:
    """Retrieve the hash-chained lineage events for a given analysis run."""
    events = await attestation_service.get_lineage_events_for_run(run_id)
    return events


@router.post("/lineage/runs/{run_id}/verify")
async def verify_run_lineage(run_id: str) -> Dict[str, Any]:
    """Verify cryptographic hash-continuity of the lineage event chain for a run."""
    events = await attestation_service.get_lineage_events_for_run(run_id)
    if not events:
        raise HTTPException(status_code=404, detail=f"No lineage events recorded for run '{run_id}'.")
    
    is_valid, errors = lineage_tracker.verify_chain(events)
    return {
        "run_id": run_id,
        "chain_valid": is_valid,
        "event_count": len(events),
        "errors": errors,
        "head_event_hash": events[-1].event_hash if events else None,
    }


@router.post("/lineage/runs/{run_id}/checkpoint", response_model=ChainCheckpoint)
async def checkpoint_run_lineage(
    run_id: str,
    project_id: str = Query(..., description="Project ID"),
) -> ChainCheckpoint:
    """Issue a signed cryptographic chain-head checkpoint over the run's lineage chain."""
    events = await attestation_service.get_lineage_events_for_run(run_id)
    if not events:
        raise HTTPException(status_code=404, detail=f"No lineage events found to checkpoint for run '{run_id}'.")

    try:
        checkpoint = lineage_tracker.create_chain_checkpoint(
            project_id=project_id,
            chain_id=f"chain_{run_id}",
            events=events,
        )
        coll = db_manager.get_collection("lineage_checkpoints")
        if coll is not None:
            await coll.insert_one(checkpoint.model_dump())
        return checkpoint
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Checkpoint creation failed: {exc}")


@router.get("/artifacts/{project_id}/{run_id}/verify")
async def verify_artifacts_deployment(project_id: str, run_id: str) -> Dict[str, Any]:
    """Verify artifact files on disk against attested content hashes before deployment or download."""
    res = verify_artifact_deployment_readiness(project_id, run_id)
    return res


@router.get("/keys/public")
async def get_public_keys() -> List[Dict[str, Any]]:
    """Retrieve public verification keys in the trusted registry."""
    return key_manager.list_public_keys()


@router.post("/keys/revoke")
async def revoke_signing_key(req: RevokeKeyRequest) -> Dict[str, Any]:
    """Revoke an attestation signing key."""
    key_manager.revoke_key(req.key_id, req.reason)
    return {
        "key_id": req.key_id,
        "status": "REVOKED",
        "reason": req.reason,
    }
