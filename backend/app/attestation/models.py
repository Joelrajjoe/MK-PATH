"""Strongly-typed, versioned Pydantic schemas for Attested Result Envelopes with Healing Lineage (ARE-HL)."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class AttestationStatus(str, Enum):
    PROPOSED = "PROPOSED"
    SIGNED = "SIGNED"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"
    REVOKED = "REVOKED"
    BLOCKED = "BLOCKED"
    STALE = "STALE"


class SignatureAlgorithm(str, Enum):
    ED25519 = "Ed25519"
    RSA_PSS_SHA256 = "RSA-PSS-SHA256"


class CanonicalizationAlgorithm(str, Enum):
    RFC_8785_JCS = "RFC-8785-JCS"


class HashAlgorithm(str, Enum):
    SHA256 = "SHA-256"


class GateStatusEnum(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    WARNING = "WARNING"
    HUMAN_REVIEW = "HUMAN_REVIEW"


class IntegrityStatus(str, Enum):
    VALID = "VALID"
    INVALID_SIGNATURE = "INVALID_SIGNATURE"
    HASH_MISMATCH = "HASH_MISMATCH"
    UNKNOWN_KEY = "UNKNOWN_KEY"
    REVOKED_KEY = "REVOKED_KEY"
    UNTRUSTED_KEY = "UNTRUSTED_KEY"
    MISSING_CONTENT = "MISSING_CONTENT"
    INVALID_SCHEMA = "INVALID_SCHEMA"
    LINEAGE_BROKEN = "LINEAGE_BROKEN"
    POLICY_MISMATCH = "POLICY_MISMATCH"
    HUMAN_REVIEW_REQUIRED = "HUMAN_REVIEW_REQUIRED"
    ERROR = "ERROR"


class LineageEventType(str, Enum):
    DATASET_INGESTION = "DATASET_INGESTION"
    DATASET_VERSION_CREATION = "DATASET_VERSION_CREATION"
    PROFILING = "PROFILING"
    SEMANTIC_MAPPING = "SEMANTIC_MAPPING"
    HEALING_PROPOSAL = "HEALING_PROPOSAL"
    HEALING_APPROVAL = "HEALING_APPROVAL"
    HEALING_EXECUTION = "HEALING_EXECUTION"
    ANALYSIS_EXECUTION = "ANALYSIS_EXECUTION"
    PMSG_EVALUATION = "PMSG_EVALUATION"
    VERIFICATION_GATE_EVALUATION = "VERIFICATION_GATE_EVALUATION"
    HUMAN_REVIEW = "HUMAN_REVIEW"
    ARTIFACT_GENERATION = "ARTIFACT_GENERATION"
    ATTESTATION_CREATION = "ATTESTATION_CREATION"
    ATTESTATION_VERIFICATION = "ATTESTATION_VERIFICATION"
    DEPLOYMENT_AUTHORIZATION = "DEPLOYMENT_AUTHORIZATION"
    DEPLOYMENT_REJECTION = "DEPLOYMENT_REJECTION"


# ---------------------------------------------------------------------------
# Component models
# ---------------------------------------------------------------------------

class SourceIdentity(BaseModel):
    source_dataset_id: str
    source_dataset_version: str = "v1.0.0"
    source_content_hash: str
    source_schema_hash: str
    source_size_bytes: Optional[int] = None
    source_record_count: Optional[int] = None
    source_storage_reference: str


class HealingOperationRecord(BaseModel):
    operation_id: str
    operation_type: str
    parent_dataset_id: str
    parent_content_hash: str
    derived_dataset_id: str
    derived_content_hash: str
    parameters_digest: str
    columns_affected: List[str] = Field(default_factory=list)
    records_before: int
    records_after: int
    schema_changes: Dict[str, Any] = Field(default_factory=dict)
    quality_score_before: float
    quality_score_after: float
    improvements: List[str] = Field(default_factory=list)
    executed_by: str = "mkpath.healing.engine"
    approval_reference: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class TransformationLineage(BaseModel):
    lineage_root_id: str
    parent_envelope_id: Optional[str] = None
    parent_dataset_id: str
    derived_dataset_id: Optional[str] = None
    derived_content_hash: Optional[str] = None
    transformation_sequence: List[str] = Field(default_factory=list)
    healing_operation_records: List[HealingOperationRecord] = Field(default_factory=list)
    before_after_quality_evidence: Dict[str, Any] = Field(default_factory=dict)
    human_approval_references: List[str] = Field(default_factory=list)


class AnalyticalResultProvenance(BaseModel):
    analysis_plan_id: str
    analysis_plan_version: str = "v1.0"
    analysis_input_hashes: List[str] = Field(default_factory=list)
    metric_definitions: Dict[str, str] = Field(default_factory=dict)
    result_payload_hash: str
    result_schema_hash: str
    execution_metadata: Dict[str, Any] = Field(default_factory=dict)
    deterministic_execution_details: Dict[str, Any] = Field(default_factory=dict)


class VerificationGateEvidence(BaseModel):
    gate_id: str
    status: GateStatusEnum
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW
    evidence: List[str] = Field(default_factory=list)
    metrics: Dict[str, Any] = Field(default_factory=dict)
    threshold: Optional[float] = None
    reason: str
    recommendation: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class VerificationProvenance(BaseModel):
    verification_policy_version: str = "v1.0"
    verification_gate_results: List[VerificationGateEvidence] = Field(default_factory=list)
    pmsg_run_id: Optional[str] = None
    pmsg_result_hash: Optional[str] = None
    pmsg_gate_status: Optional[GateStatusEnum] = None
    mandatory_gate_status: GateStatusEnum  # PASS if all mandatory passed, FAIL if any failed
    deployment_readiness_status: str  # READY or BLOCKED
    evidence_references: List[str] = Field(default_factory=list)
    unresolved_warnings: List[str] = Field(default_factory=list)
    human_review_status: str = "RESOLVED"  # RESOLVED or PENDING


class ArtifactProvenance(BaseModel):
    artifact_ids: List[str] = Field(default_factory=list)
    artifact_content_hashes: Dict[str, str] = Field(default_factory=dict)  # artifact_file_name -> sha256
    model_version: Optional[str] = None
    model_card_hash: Optional[str] = None
    artifact_verification_status: str = "PASS"  # PASS or FAILED


class SignatureMetadata(BaseModel):
    canonicalization_algorithm: CanonicalizationAlgorithm = CanonicalizationAlgorithm.RFC_8785_JCS
    hash_algorithm: HashAlgorithm = HashAlgorithm.SHA256
    signature_algorithm: SignatureAlgorithm = SignatureAlgorithm.ED25519
    payload_hash: str
    signature: str
    key_id: str
    key_version: str
    signing_timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    attestation_policy_version: str = "ARE-HL-v1.0"


# ---------------------------------------------------------------------------
# Attested Result Envelope (ARE-HL)
# ---------------------------------------------------------------------------

class AttestedResultEnvelope(BaseModel):
    # Identity
    envelope_id: str
    schema_version: str = "are-hl-v1.0"
    project_id: str
    run_id: str
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    application_version: str = "1.0.0"
    git_commit: Optional[str] = None
    attestation_status: AttestationStatus = AttestationStatus.SIGNED

    # Provenance Sections
    source_identity: SourceIdentity
    transformation_lineage: TransformationLineage
    analytical_result: AnalyticalResultProvenance
    verification: VerificationProvenance
    artifact_provenance: ArtifactProvenance

    # Digital Attestation
    attestation: Optional[SignatureMetadata] = None


# ---------------------------------------------------------------------------
# Tamper-Evident Lineage Graph Event & Checkpoint
# ---------------------------------------------------------------------------

class LineageEvent(BaseModel):
    event_id: str
    project_id: str
    run_id: str
    sequence_number: int
    event_type: LineageEventType
    parent_event_id: Optional[str] = None
    previous_event_hash: str  # "0" * 64 for genesis
    input_artifacts: List[Dict[str, str]] = Field(default_factory=list)  # [{"id": ..., "hash": ...}]
    output_artifacts: List[Dict[str, str]] = Field(default_factory=list)
    actor: str = "system"
    policy_version: str = "v1.0"
    details: Dict[str, Any] = Field(default_factory=dict)
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    event_hash: str = ""  # SHA256(canonical(event without event_hash) || previous_event_hash)


class ChainCheckpoint(BaseModel):
    checkpoint_id: str
    project_id: str
    chain_id: str
    sequence_number: int
    final_event_hash: str
    previous_checkpoint_hash: Optional[str] = None
    checkpoint_timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    key_id: str
    key_version: str
    signature: str


# ---------------------------------------------------------------------------
# Verification Report
# ---------------------------------------------------------------------------

class EnvelopeVerificationReport(BaseModel):
    envelope_id: str
    overall_status: IntegrityStatus
    signature_valid: bool
    payload_hash_valid: bool
    content_hashes_valid: bool
    lineage_complete: bool
    mandatory_gates_acceptable: bool
    key_trusted: bool
    key_id: str
    key_revoked: bool = False
    verified_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    verification_errors: List[str] = Field(default_factory=list)
    unresolved_warnings: List[str] = Field(default_factory=list)
    recalculated_hashes: Dict[str, str] = Field(default_factory=dict)
