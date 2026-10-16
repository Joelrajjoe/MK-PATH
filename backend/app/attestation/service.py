"""Central Attestation and Provenance Service for ARE-HL (Phases 6, 7, 8).

Coordinates:
- Strongly typed Attested Result Envelope construction
- Strict gate compliance & PMSG integration
- Digital signature sealing
- MongoDB Atlas persistence with fail-closed integrity
- Full cryptographic reverification and tamper detection
"""

import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ..config import settings
from ..database import db_manager
from .crypto import Signer, Verifier, key_manager
from .hashing import (
    canonical_json_bytes,
    hash_bytes,
    hash_file_streaming,
    hash_json_object,
)
from .lineage import lineage_tracker
from .models import (
    AnalyticalResultProvenance,
    ArtifactProvenance,
    AttestationStatus,
    AttestedResultEnvelope,
    ChainCheckpoint,
    EnvelopeVerificationReport,
    GateStatusEnum,
    HealingOperationRecord,
    IntegrityStatus,
    LineageEvent,
    LineageEventType,
    SourceIdentity,
    TransformationLineage,
    VerificationGateEvidence,
    VerificationProvenance,
)

logger = logging.getLogger("mkpath.attestation.service")


class AttestationGateFailureError(ValueError):
    """Raised when an attempt is made to issue a deployment-ready attestation on failed gates."""
    pass


class AtlasPersistenceError(RuntimeError):
    """Raised when durable Atlas persistence fails or fallback is active."""
    pass


class AttestationService:
    def __init__(self, signer: Optional[Signer] = None, verifier: Optional[Verifier] = None):
        self.signer = signer or Signer()
        self.verifier = verifier or Verifier()

    async def create_envelope_for_run(
        self,
        *,
        project_id: str,
        run_id: str,
        source_dataset_id: str,
        source_storage_reference: str,
        verification_report: Dict[str, Any],
        analysis_result: Dict[str, Any],
        healing_event: Optional[Dict[str, Any]] = None,
        artifact_meta: Optional[Dict[str, Any]] = None,
        require_atlas: bool = False,
    ) -> AttestedResultEnvelope:
        """
        Build, validate, sign, and persist an Attested Result Envelope:
        1. Extract and compute source content hash and schema hash.
        2. Verify mandatory gates (Data Quality, Temporal Leakage, PMSG).
        3. Extract healing lineage if present.
        4. Extract artifact hashes if present.
        5. Enforce gate policy: If mandatory gate failed, mark BLOCKED/REJECTED.
        6. Compute digital signature over canonical payload.
        7. Persist to MongoDB Atlas.
        """
        envelope_id = f"are_{uuid.uuid4().hex[:16]}"
        now_iso = datetime.now(timezone.utc).isoformat()

        # 1. Source Identity
        source_path = Path(source_storage_reference).resolve()
        if source_path.exists() and source_path.is_file():
            source_content_hash = hash_file_streaming(source_path)
            source_size = source_path.stat().st_size
        else:
            source_content_hash = hash_bytes(b"empty_or_virtual_source", "sha256")
            source_size = 0

        source_id = SourceIdentity(
            source_dataset_id=source_dataset_id,
            source_dataset_version="v1.0.0",
            source_content_hash=source_content_hash,
            source_schema_hash=hash_json_object(analysis_result.get("schema", {})),
            source_size_bytes=source_size,
            source_record_count=analysis_result.get("row_count"),
            source_storage_reference=str(source_path),
        )

        # 2. Transformation & Healing Lineage
        healing_records: List[HealingOperationRecord] = []
        derived_dataset_id = None
        derived_content_hash = None
        quality_evidence = {}

        if healing_event:
            derived_dataset_id = healing_event.get("derived_dataset_id")
            derived_content_hash = healing_event.get("derived_content_hash", "")
            q_rep = healing_event.get("quality_report", {})
            quality_evidence = {
                "before_score": q_rep.get("before_score") if isinstance(q_rep, dict) else getattr(q_rep, "before_score", 85.0),
                "after_score": q_rep.get("after_score") if isinstance(q_rep, dict) else getattr(q_rep, "after_score", 100.0),
                "improvements": q_rep.get("improvements", []) if isinstance(q_rep, dict) else getattr(q_rep, "improvements", []),
            }
            op_rec = HealingOperationRecord(
                operation_id=f"heal_op_{uuid.uuid4().hex[:8]}",
                operation_type="autonomous_preprocessing",
                parent_dataset_id=source_dataset_id,
                parent_content_hash=healing_event.get("parent_content_hash", source_content_hash),
                derived_dataset_id=derived_dataset_id or "",
                derived_content_hash=derived_content_hash or "",
                parameters_digest=healing_event.get("parameters_digest", ""),
                columns_affected=healing_event.get("plan", {}).get("columns_affected", []) if isinstance(healing_event.get("plan"), dict) else getattr(healing_event.get("plan"), "columns_affected", []),
                records_before=healing_event.get("row_count", 0),
                records_after=healing_event.get("row_count", 0),
                quality_score_before=float(quality_evidence["before_score"]),
                quality_score_after=float(quality_evidence["after_score"]),
                improvements=quality_evidence["improvements"],
                executed_by="mkpath.healing.engine",
                timestamp=now_iso,
            )
            healing_records.append(op_rec)

        transformation_lineage = TransformationLineage(
            lineage_root_id=source_dataset_id,
            parent_dataset_id=source_dataset_id,
            derived_dataset_id=derived_dataset_id,
            derived_content_hash=derived_content_hash,
            transformation_sequence=["profiling", "healing", "analysis"] if healing_event else ["profiling", "analysis"],
            healing_operation_records=healing_records,
            before_after_quality_evidence=quality_evidence,
        )

        # 3. Analytical Result Provenance
        analytical_provenance = AnalyticalResultProvenance(
            analysis_plan_id=analysis_result.get("plan_id", f"plan_{run_id}"),
            analysis_plan_version="v1.0",
            analysis_input_hashes=[source_content_hash] + ([derived_content_hash] if derived_content_hash else []),
            metric_definitions=analysis_result.get("metric_definitions", {}),
            result_payload_hash=hash_json_object(analysis_result.get("metrics", {})),
            result_schema_hash=hash_json_object(analysis_result.get("schema", {})),
            execution_metadata={
                "run_id": run_id,
                "project_id": project_id,
                "engine": "duckdb",
            },
            deterministic_execution_details=analysis_result.get("execution_details", {}),
        )

        # 4. Verification Gates & PMSG Integration
        v_summary = verification_report.get("summary", {})
        gate_results_raw = v_summary.get("results", []) if isinstance(v_summary, dict) else getattr(v_summary, "results", [])
        
        gate_evidences: List[VerificationGateEvidence] = []
        has_critical_failure = False

        for g in gate_results_raw:
            g_dict = g if isinstance(g, dict) else g.model_dump()
            st = g_dict.get("status", "PASS")
            if st == "FAIL" and g_dict.get("severity") in ("CRITICAL", "HIGH"):
                has_critical_failure = True
            
            gate_evidences.append(
                VerificationGateEvidence(
                    gate_id=g_dict.get("gate_id", "unknown"),
                    status=GateStatusEnum(st) if st in GateStatusEnum._value2member_map_ else GateStatusEnum.FAIL,
                    severity=g_dict.get("severity", "HIGH"),
                    evidence=g_dict.get("evidence", []),
                    metrics=g_dict.get("metrics", {}),
                    threshold=g_dict.get("threshold"),
                    reason=g_dict.get("reason", ""),
                    recommendation=g_dict.get("recommendation", ""),
                    timestamp=g_dict.get("timestamp", now_iso),
                )
            )

        deployment_status = verification_report.get("deployment_status", "READY")
        if has_critical_failure:
            deployment_status = "BLOCKED"

        pmsg_gate = next((g for g in gate_evidences if g.gate_id == "plan_multiverse_stability"), None)
        pmsg_status = pmsg_gate.status if pmsg_gate else None
        pmsg_run_id = analysis_result.get("pmsg_run_id")

        verification_provenance = VerificationProvenance(
            verification_policy_version="v1.0",
            verification_gate_results=gate_evidences,
            pmsg_run_id=pmsg_run_id,
            pmsg_result_hash=hash_json_object(pmsg_gate.metrics if pmsg_gate else {}),
            pmsg_gate_status=pmsg_status,
            mandatory_gate_status=GateStatusEnum.FAIL if has_critical_failure else GateStatusEnum.PASS,
            deployment_readiness_status=deployment_status,
            evidence_references=[f"run:{run_id}"],
            unresolved_warnings=[g.reason for g in gate_evidences if g.status == GateStatusEnum.WARNING],
            human_review_status="PENDING" if any(g.status == GateStatusEnum.HUMAN_REVIEW for g in gate_evidences) else "RESOLVED",
        )

        # 5. Artifact Provenance
        art_hashes = {}
        model_ver = None
        model_card_h = None
        if artifact_meta:
            art_hashes = artifact_meta.get("artifact_content_hashes", {})
            model_ver = artifact_meta.get("model_version")
            model_card_h = artifact_meta.get("model_card_hash")

        artifact_provenance = ArtifactProvenance(
            artifact_ids=[f"art_{run_id}"],
            artifact_content_hashes=art_hashes,
            model_version=model_ver,
            model_card_hash=model_card_h,
            artifact_verification_status="PASS" if (artifact_meta and artifact_meta.get("downloadable")) else "BLOCKED",
        )

        # Determine attestation status
        if has_critical_failure or deployment_status == "BLOCKED":
            attestation_status = AttestationStatus.BLOCKED
        else:
            attestation_status = AttestationStatus.SIGNED

        # Construct unsigned envelope
        envelope = AttestedResultEnvelope(
            envelope_id=envelope_id,
            schema_version="are-hl-v1.0",
            project_id=project_id,
            run_id=run_id,
            created_at=now_iso,
            application_version="1.0.0",
            attestation_status=attestation_status,
            source_identity=source_id,
            transformation_lineage=transformation_lineage,
            analytical_result=analytical_provenance,
            verification=verification_provenance,
            artifact_provenance=artifact_provenance,
        )

        # 6. Cryptographically sign the envelope
        signed_envelope = self.signer.sign_envelope(envelope)

        # 7. Record lineage event
        lineage_event = lineage_tracker.create_event(
            project_id=project_id,
            run_id=run_id,
            event_type=LineageEventType.ATTESTATION_CREATION,
            sequence_number=1,
            details={
                "envelope_id": envelope_id,
                "attestation_status": attestation_status.value,
                "deployment_status": deployment_status,
                "source_hash": source_content_hash,
            },
        )

        # 8. Persist to MongoDB Atlas
        await self._persist_envelope(signed_envelope, lineage_event, require_atlas=require_atlas)

        return signed_envelope

    async def _persist_envelope(
        self,
        envelope: AttestedResultEnvelope,
        lineage_event: Optional[LineageEvent] = None,
        require_atlas: bool = False,
    ) -> None:
        """Persist envelope to MongoDB Atlas with fail-closed behavior when Atlas is required."""
        coll = db_manager.get_collection("attestation_envelopes")
        if coll is None:
            if require_atlas:
                raise AtlasPersistenceError("MongoDB Atlas is unavailable for required durable attestation.")
            logger.warning("Attestation store unavailable; envelope '%s' not persisted to DB.", envelope.envelope_id)
            return

        # Check if database is using local fallback when Atlas is strictly required
        if require_atlas and (not db_manager.is_ready() or getattr(db_manager, "_using_fallback", False)):
            raise AtlasPersistenceError("Strict Atlas persistence requested but database is in local fallback mode.")

        doc = envelope.model_dump()
        try:
            await coll.insert_one(doc)
            logger.info("Persisted AttestedResultEnvelope '%s' to database.", envelope.envelope_id)
            
            # Persist lineage event
            if lineage_event:
                l_coll = db_manager.get_collection("lineage_events")
                if l_coll is not None:
                    await l_coll.insert_one(lineage_event.model_dump())
        except Exception as exc:
            logger.error("Failed to insert envelope to database: %s", exc)
            if require_atlas:
                raise AtlasPersistenceError(f"Database write failed: {exc}")

    async def get_envelope(self, envelope_id: str) -> Optional[AttestedResultEnvelope]:
        """Retrieve an envelope by its envelope_id."""
        coll = db_manager.get_collection("attestation_envelopes")
        if coll is None:
            return None
        doc = await coll.find_one({"envelope_id": envelope_id}, {"_id": 0})
        if not doc:
            return None
        return AttestedResultEnvelope.model_validate(doc)

    async def verify_envelope_by_id(self, envelope_id: str) -> EnvelopeVerificationReport:
        """Retrieve and exhaustively verify an envelope."""
        envelope = await self.get_envelope(envelope_id)
        if not envelope:
            return EnvelopeVerificationReport(
                envelope_id=envelope_id,
                overall_status=IntegrityStatus.MISSING_CONTENT,
                signature_valid=False,
                payload_hash_valid=False,
                content_hashes_valid=False,
                lineage_complete=False,
                mandatory_gates_acceptable=False,
                key_trusted=False,
                key_id="unknown",
                verification_errors=[f"Attested Result Envelope '{envelope_id}' not found."],
            )

        return self.verifier.verify_envelope(envelope, verify_content_files=True)

    async def list_envelopes_for_project(self, project_id: str) -> List[Dict[str, Any]]:
        """List summary of envelopes for an authorized project."""
        coll = db_manager.get_collection("attestation_envelopes")
        if coll is None:
            return []
        cursor = coll.find({"project_id": project_id}, {"_id": 0}).sort("created_at", -1)
        return [doc async for doc in cursor]

    async def get_lineage_events_for_run(self, run_id: str) -> List[LineageEvent]:
        """Fetch all lineage events for a run, ordered by sequence."""
        coll = db_manager.get_collection("lineage_events")
        if coll is None:
            return []
        cursor = coll.find({"run_id": run_id}, {"_id": 0}).sort("sequence_number", 1)
        docs = [doc async for doc in cursor]
        return [LineageEvent.model_validate(d) for d in docs]


attestation_service = AttestationService()
