"""MK-PATH Option C — Attested Result Envelopes with Healing Lineage (ARE-HL)
Automated Security, Cryptographic & Gate Compliance Test Suite.

Tests:
1. RFC 8785 Canonicalization Determinism & Invariance
2. File Streaming SHA-256 and Byte Tampering Detection
3. Digital Signatures (Ed25519 & RSA-PSS):
   - Key generation, registration, and export
   - Valid signature verification
   - Signature bit-flip / truncation tampering (INVALID_SIGNATURE)
   - Payload byte tampering (HASH_MISMATCH / INVALID_SIGNATURE)
   - Unknown key rejection (UNKNOWN_KEY)
   - Revoked key rejection (REVOKED_KEY)
4. Hash-Chained Lineage Events & Tamper-Evident Graph:
   - Genesis event and previous_event_hash binding
   - Middle-of-chain modification breaks all downstream links (tampering detected)
   - Broken sequence continuity detection
   - Signed ChainCheckpoint integrity verification
5. Verification Gate Compliance & Deployment Enforcement:
   - Critical gate failure blocks deployment status and marks envelope BLOCKED
   - Artifact tampering blocks deployment readiness verification
"""

import asyncio
import copy
import hashlib
import json
import os
import tempfile
import pytest
from datetime import datetime, timezone
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric import ed25519, rsa
from cryptography.hazmat.primitives import serialization

from app.attestation.models import (
    AttestedResultEnvelope,
    AttestationStatus,
    SourceIdentity,
    TransformationLineage,
    AnalyticalResultProvenance,
    VerificationProvenance,
    VerificationGateEvidence,
    ArtifactProvenance,
    SignatureMetadata,
    LineageEvent,
    LineageEventType,
    ChainCheckpoint,
    EnvelopeVerificationReport,
    IntegrityStatus,
    GateStatusEnum,
    SignatureAlgorithm,
)
from app.attestation.hashing import (
    canonical_json_bytes,
    hash_json_object,
    hash_file_streaming,
    hash_bytes,
)
from app.attestation.crypto import (
    KeyManager,
    Signer,
    Verifier,
    KeyState,
)
from app.attestation.lineage import (
    compute_event_hash,
    LineageTracker,
    GENESIS_PREVIOUS_HASH,
    LineageChainError,
)
from app.attestation.service import (
    AttestationService,
)
from app.engineering.ml_engineer import (
    verify_artifact_deployment_readiness,
)


def _make_test_source():
    return SourceIdentity(
        source_dataset_id="ds_01",
        source_dataset_version="v1.0.0",
        source_content_hash="a" * 64,
        source_schema_hash="b" * 64,
        source_size_bytes=100,
        source_storage_reference="data/ds_01.csv",
    )


def _make_test_lineage():
    return TransformationLineage(
        lineage_root_id="ds_01",
        parent_dataset_id="ds_01",
    )


# =====================================================================
# 1. RFC 8785 Canonicalization & Hashing Determinism
# =====================================================================

def test_canonical_json_key_sorting():
    """Verify that key ordering in dictionary does not affect canonical bytes."""
    obj1 = {"z": 1, "a": 2, "m": {"b": 3, "a": 4}}
    obj2 = {"a": 2, "m": {"a": 4, "b": 3}, "z": 1}
    
    b1 = canonical_json_bytes(obj1)
    b2 = canonical_json_bytes(obj2)
    
    assert b1 == b2
    assert b1 == b'{"a":2,"m":{"a":4,"b":3},"z":1}'


def test_canonical_json_float_and_whitespace():
    """Verify float formatting and whitespace stripping in canonical bytes."""
    obj = {"number": 10.0, "spaces": "  content  ", "nested": [1, 2, 3]}
    b = canonical_json_bytes(obj)
    
    assert b == b'{"nested":[1,2,3],"number":10.0,"spaces":"  content  "}'


def test_canonical_json_unicode_preservation():
    """Verify UTF-8 encoding without ASCII escaping."""
    obj = {"label": "café München 测试 🚀"}
    b = canonical_json_bytes(obj)
    
    expected = '{"label":"café München 测试 🚀"}'.encode("utf-8")
    assert b == expected


def test_hash_json_object_sha256():
    """Verify SHA-256 of canonical JSON matches hashlib."""
    obj = {"test": 123}
    expected_hash = hashlib.sha256(b'{"test":123}').hexdigest()
    assert hash_json_object(obj) == expected_hash


# =====================================================================
# 2. File Streaming SHA-256 & Tampering Detection
# =====================================================================

def test_hash_file_streaming_matches_hashlib():
    """Verify chunked streaming SHA-256 matches in-memory hashlib."""
    content = b"MKPATH-Option-C-Attested-Data" * 1000
    with tempfile.NamedTemporaryFile(delete=False) as tf:
        tf.write(content)
        tf_path = tf.name
        
    try:
        calculated_hash = hash_file_streaming(tf_path)
        expected_hash = hashlib.sha256(content).hexdigest()
        assert calculated_hash == expected_hash
    finally:
        if os.path.exists(tf_path):
            os.remove(tf_path)


def test_file_tampering_produces_hash_mismatch():
    """Verify single byte alteration produces completely distinct SHA-256."""
    content = b"Original pristine dataset content"
    with tempfile.NamedTemporaryFile(delete=False) as tf:
        tf.write(content)
        tf_path = tf.name
        
    try:
        h1 = hash_file_streaming(tf_path)
        
        # Tamper single byte
        with open(tf_path, "wb") as f:
            f.write(b"Original pristine dataset ContenT")
            
        h2 = hash_file_streaming(tf_path)
        assert h1 != h2
    finally:
        if os.path.exists(tf_path):
            os.remove(tf_path)


# =====================================================================
# 3. Cryptographic Signatures (Ed25519 & RSA-PSS) & Security
# =====================================================================

def test_ed25519_sign_and_verify_valid():
    """Test standard Ed25519 keypair signing and envelope verification."""
    km = KeyManager()
    priv = ed25519.Ed25519PrivateKey.generate()
    km.register_private_key("key-ed-01", "1.0.0", priv, is_active=True, trusted=True)
    
    signer = Signer(km)
    verifier = Verifier(km)
    
    envelope = AttestedResultEnvelope(
        envelope_id="are_test_01",
        project_id="proj_01",
        run_id="run_01",
        source_identity=_make_test_source(),
        transformation_lineage=_make_test_lineage(),
        analytical_result=AnalyticalResultProvenance(
            analysis_plan_id="plan_01",
            result_payload_hash="c" * 64,
            result_schema_hash="d" * 64,
        ),
        verification=VerificationProvenance(
            mandatory_gate_status=GateStatusEnum.PASS,
            deployment_readiness_status="READY",
        ),
        artifact_provenance=ArtifactProvenance(),
    )
    
    signed_env = signer.sign_envelope(envelope)
    assert signed_env.attestation is not None
    assert signed_env.attestation.key_id == "key-ed-01"
    assert signed_env.attestation.signature_algorithm == SignatureAlgorithm.ED25519
    
    report = verifier.verify_envelope(signed_env, verify_content_files=False)
    assert report.signature_valid is True
    assert report.payload_hash_valid is True
    assert report.overall_status == IntegrityStatus.VALID


def test_rsa_pss_sign_and_verify_valid():
    """Test RSA-PSS keypair signing and envelope verification."""
    km = KeyManager()
    priv = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    km.register_private_key("key-rsa-01", "1.0.0", priv, is_active=True, trusted=True)
    
    signer = Signer(km)
    verifier = Verifier(km)
    
    envelope = AttestedResultEnvelope(
        envelope_id="are_test_rsa",
        project_id="proj_01",
        run_id="run_01",
        source_identity=_make_test_source(),
        transformation_lineage=_make_test_lineage(),
        analytical_result=AnalyticalResultProvenance(
            analysis_plan_id="plan_01",
            result_payload_hash="c" * 64,
            result_schema_hash="d" * 64,
        ),
        verification=VerificationProvenance(
            mandatory_gate_status=GateStatusEnum.PASS,
            deployment_readiness_status="READY",
        ),
        artifact_provenance=ArtifactProvenance(),
    )
    
    signed_env = signer.sign_envelope(envelope)
    assert signed_env.attestation.signature_algorithm == SignatureAlgorithm.RSA_PSS_SHA256
    
    report = verifier.verify_envelope(signed_env, verify_content_files=False)
    assert report.signature_valid is True
    assert report.overall_status == IntegrityStatus.VALID


def test_tampered_signature_rejected():
    """Test that a tampered signature fails verification (INVALID_SIGNATURE)."""
    km = KeyManager()
    priv = ed25519.Ed25519PrivateKey.generate()
    km.register_private_key("key-tamper-sig", "1.0.0", priv, is_active=True, trusted=True)
    signer = Signer(km)
    verifier = Verifier(km)
    
    envelope = AttestedResultEnvelope(
        envelope_id="are_test_tamper_sig",
        project_id="proj_01",
        run_id="run_01",
        source_identity=_make_test_source(),
        transformation_lineage=_make_test_lineage(),
        analytical_result=AnalyticalResultProvenance(
            analysis_plan_id="plan_01",
            result_payload_hash="c" * 64,
            result_schema_hash="d" * 64,
        ),
        verification=VerificationProvenance(
            mandatory_gate_status=GateStatusEnum.PASS,
            deployment_readiness_status="READY",
        ),
        artifact_provenance=ArtifactProvenance(),
    )
    
    signed_env = signer.sign_envelope(envelope)
    
    # Tamper signature string
    tampered_sig = "A" + signed_env.attestation.signature[1:]
    signed_env.attestation.signature = tampered_sig
    
    report = verifier.verify_envelope(signed_env, verify_content_files=False)
    assert report.signature_valid is False
    assert report.overall_status == IntegrityStatus.INVALID_SIGNATURE


def test_tampered_payload_rejected():
    """Test that altering any payload field invalidates the attestation."""
    km = KeyManager()
    priv = ed25519.Ed25519PrivateKey.generate()
    km.register_private_key("key-tamper-payload", "1.0.0", priv, is_active=True, trusted=True)
    signer = Signer(km)
    verifier = Verifier(km)
    
    envelope = AttestedResultEnvelope(
        envelope_id="are_test_tamper_pl",
        project_id="proj_01",
        run_id="run_01",
        source_identity=_make_test_source(),
        transformation_lineage=_make_test_lineage(),
        analytical_result=AnalyticalResultProvenance(
            analysis_plan_id="plan_01",
            result_payload_hash="c" * 64,
            result_schema_hash="d" * 64,
        ),
        verification=VerificationProvenance(
            mandatory_gate_status=GateStatusEnum.PASS,
            deployment_readiness_status="READY",
        ),
        artifact_provenance=ArtifactProvenance(),
    )
    
    signed_env = signer.sign_envelope(envelope)
    
    # Tamper with an envelope field
    signed_env.source_identity.source_size_bytes = 999999
    
    report = verifier.verify_envelope(signed_env, verify_content_files=False)
    assert report.payload_hash_valid is False
    assert report.overall_status in (IntegrityStatus.INVALID_SIGNATURE, IntegrityStatus.HASH_MISMATCH)


def test_unknown_key_rejected():
    """Verification must fail closed when key_id is not in trust registry."""
    km1 = KeyManager()
    priv1 = ed25519.Ed25519PrivateKey.generate()
    km1.register_private_key("unknown-foreign-key", "1.0.0", priv1, is_active=True, trusted=True)
    signer1 = Signer(km1)
    
    envelope = AttestedResultEnvelope(
        envelope_id="are_test_unknown",
        project_id="proj_01",
        run_id="run_01",
        source_identity=_make_test_source(),
        transformation_lineage=_make_test_lineage(),
        analytical_result=AnalyticalResultProvenance(
            analysis_plan_id="plan_01",
            result_payload_hash="c" * 64,
            result_schema_hash="d" * 64,
        ),
        verification=VerificationProvenance(
            mandatory_gate_status=GateStatusEnum.PASS,
            deployment_readiness_status="READY",
        ),
        artifact_provenance=ArtifactProvenance(),
    )
    signed_env = signer1.sign_envelope(envelope)
    
    # Clean verifier with fresh keystore
    km2 = KeyManager()
    if "unknown-foreign-key" in km2._public_registry:
        del km2._public_registry["unknown-foreign-key"]
    verifier2 = Verifier(km2)
    
    report = verifier2.verify_envelope(signed_env, verify_content_files=False)
    assert report.key_trusted is False
    assert report.overall_status == IntegrityStatus.UNKNOWN_KEY


def test_revoked_key_rejected():
    """Verification must fail closed when the signing key has been revoked."""
    km = KeyManager()
    priv = ed25519.Ed25519PrivateKey.generate()
    km.register_private_key("key-revoked-01", "1.0.0", priv, is_active=True, trusted=True)
    signer = Signer(km)
    verifier = Verifier(km)
    
    envelope = AttestedResultEnvelope(
        envelope_id="are_test_revoked",
        project_id="proj_01",
        run_id="run_01",
        source_identity=_make_test_source(),
        transformation_lineage=_make_test_lineage(),
        analytical_result=AnalyticalResultProvenance(
            analysis_plan_id="plan_01",
            result_payload_hash="c" * 64,
            result_schema_hash="d" * 64,
        ),
        verification=VerificationProvenance(
            mandatory_gate_status=GateStatusEnum.PASS,
            deployment_readiness_status="READY",
        ),
        artifact_provenance=ArtifactProvenance(),
    )
    signed_env = signer.sign_envelope(envelope)
    
    # Revoke key
    km.revoke_key("key-revoked-01", reason="Test key compromise")
    
    report = verifier.verify_envelope(signed_env, verify_content_files=False)
    assert report.key_revoked is True
    assert report.overall_status == IntegrityStatus.REVOKED_KEY


# =====================================================================
# 4. Hash-Chained Lineage Graph & Integrity
# =====================================================================

def test_lineage_tracker_chain_integrity():
    """Verify correct sequential hash chaining and verification."""
    tracker = LineageTracker()
    
    e1 = tracker.create_event(
        project_id="proj_sec_01",
        run_id="run_sec_01",
        event_type=LineageEventType.DATASET_INGESTION,
        sequence_number=1,
        actor="worker",
        details={"file": "data.csv"},
    )
    assert e1.sequence_number == 1
    assert e1.previous_event_hash == GENESIS_PREVIOUS_HASH
    assert e1.event_hash == compute_event_hash(e1, GENESIS_PREVIOUS_HASH)
    
    e2 = tracker.create_event(
        project_id="proj_sec_01",
        run_id="run_sec_01",
        event_type=LineageEventType.PROFILING,
        sequence_number=2,
        previous_event_hash=e1.event_hash,
        actor="profiler",
        details={"rows": 50},
    )
    assert e2.sequence_number == 2
    assert e2.previous_event_hash == e1.event_hash
    assert e2.event_hash == compute_event_hash(e2, e1.event_hash)
    
    is_valid, errors = tracker.verify_chain([e1, e2])
    assert is_valid is True
    assert len(errors) == 0


def test_lineage_tracker_middle_tampering_detected():
    """Modifying an event in the middle of the chain breaks verification."""
    tracker = LineageTracker()
    
    e1 = tracker.create_event(
        project_id="proj_sec_02",
        run_id="run_sec_02",
        event_type=LineageEventType.DATASET_INGESTION,
        sequence_number=1,
    )
    e2 = tracker.create_event(
        project_id="proj_sec_02",
        run_id="run_sec_02",
        event_type=LineageEventType.HEALING_EXECUTION,
        sequence_number=2,
        previous_event_hash=e1.event_hash,
        details={"rule": "drop_nulls"},
    )
    e3 = tracker.create_event(
        project_id="proj_sec_02",
        run_id="run_sec_02",
        event_type=LineageEventType.VERIFICATION_GATE_EVALUATION,
        sequence_number=3,
        previous_event_hash=e2.event_hash,
    )
    
    # Tamper with event 2 details
    e2.details["rule"] = "malicious_tampered_rule"
    
    is_valid, errors = tracker.verify_chain([e1, e2, e3])
    assert is_valid is False
    assert any("Tampered event content" in err for err in errors)


def test_lineage_broken_link_detected():
    """Breaking sequence continuity or link pointer is caught immediately."""
    tracker = LineageTracker()
    
    e1 = tracker.create_event(
        project_id="proj_sec_03",
        run_id="run_sec_03",
        event_type=LineageEventType.DATASET_INGESTION,
        sequence_number=1,
    )
    e2 = tracker.create_event(
        project_id="proj_sec_03",
        run_id="run_sec_03",
        event_type=LineageEventType.HEALING_EXECUTION,
        sequence_number=3,  # Skipped 2
        previous_event_hash="f" * 64,  # Invalid pointer
    )
    
    is_valid, errors = tracker.verify_chain([e1, e2])
    assert is_valid is False
    assert any("Sequence discontinuity" in err for err in errors)
    assert any("Broken hash chain" in err for err in errors)


def test_signed_chain_checkpoint():
    """Verify signed chain-head checkpoint generation."""
    km = KeyManager()
    priv = ed25519.Ed25519PrivateKey.generate()
    km.register_private_key("chk-key-01", "1.0.0", priv, is_active=True, trusted=True)
    
    signer = Signer(km)
    tracker = LineageTracker(signer=signer)
    
    e1 = tracker.create_event(
        project_id="proj_sec_04",
        run_id="run_sec_04",
        event_type=LineageEventType.DATASET_INGESTION,
        sequence_number=1,
    )
    e2 = tracker.create_event(
        project_id="proj_sec_04",
        run_id="run_sec_04",
        event_type=LineageEventType.ANALYSIS_EXECUTION,
        sequence_number=2,
        previous_event_hash=e1.event_hash,
    )
    
    checkpoint = tracker.create_chain_checkpoint(
        project_id="proj_sec_04",
        chain_id="run_sec_04",
        events=[e1, e2],
    )
    
    assert checkpoint.sequence_number == 2
    assert checkpoint.final_event_hash == e2.event_hash
    assert checkpoint.signature is not None
    assert checkpoint.key_id == "chk-key-01"


# =====================================================================
# 5. Gate Compliance & Deployment Enforcement
# =====================================================================

def test_attestation_service_marks_blocked_on_critical_gate_failure():
    """AttestationService must mark envelope as BLOCKED if critical gates fail."""
    service = AttestationService()
    
    verification_report = {
        "summary": {
            "results": [
                {
                    "gate_id": "data_leakage_gate",
                    "severity": "CRITICAL",
                    "status": "FAIL",
                    "evidence": ["Target variable leaked into features"],
                    "reason": "Critical leakage violation",
                }
            ]
        },
        "deployment_status": "BLOCKED",
    }
    
    analysis_result = {
        "plan_id": "plan_leak_01",
        "metrics": {"accuracy": 0.99},
        "schema": {"target": "int"},
        "row_count": 100,
    }
    
    envelope = asyncio.run(service.create_envelope_for_run(
        project_id="proj_gate_01",
        run_id="run_gate_01",
        source_dataset_id="ds_leak_01",
        source_storage_reference="nonexistent/virtual/path.csv",
        verification_report=verification_report,
        analysis_result=analysis_result,
        require_atlas=False,
    ))
    
    assert envelope.attestation_status == AttestationStatus.BLOCKED
    assert envelope.verification.mandatory_gate_status == GateStatusEnum.FAIL
    assert envelope.verification.deployment_readiness_status == "BLOCKED"


def test_artifact_deployment_readiness_blocks_on_tampering(tmp_path):
    """Artifact verification must fail and block deployment if an artifact file was modified."""
    model_dir = tmp_path / "model_artifacts"
    model_dir.mkdir()
    
    model_file = model_dir / "model.pkl"
    model_file.write_bytes(b"PKL_MODEL_CONTENT_ORIGINAL")
    
    readme_file = model_dir / "README.md"
    readme_file.write_text("# Model Documentation\nPristine.")
    
    manifest = {
        "model.pkl": hashlib.sha256(b"PKL_MODEL_CONTENT_ORIGINAL").hexdigest(),
        "README.md": hashlib.sha256(readme_file.read_bytes()).hexdigest(),
    }
    metadata = {
        "project_id": "proj-art",
        "run_id": "run-art",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "artifact_content_hashes": manifest,
        "gates_passed": True,
    }
    
    meta_file = model_dir / "metadata.json"
    meta_file.write_text(json.dumps(metadata))
    
    # 1. Verify pristine state is approved
    res1 = verify_artifact_deployment_readiness(
        project_id="proj-art",
        run_id="run-art",
        artifact_dir_override=model_dir,
    )
    assert res1["deployable"] is True
    assert res1["status"] == "VERIFIED_READY"
    assert "verified" in res1["reason"].lower()
    
    # 2. Tamper with model.pkl bytes
    model_file.write_bytes(b"PKL_MODEL_CONTENT_BACKDOOR")
    
    # 3. Verify tampered state is BLOCKED
    res2 = verify_artifact_deployment_readiness(
        project_id="proj-art",
        run_id="run-art",
        artifact_dir_override=model_dir,
    )
    assert res2["deployable"] is False
    assert res2["status"] == "TAMPERED_BLOCKED"
    assert any("model.pkl" in m for m in res2["mismatches"])
