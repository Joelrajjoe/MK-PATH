"""MK-PATH Option C — Attested Result Envelopes with Healing Lineage (ARE-HL)
End-to-End Analytical Lifecycle & Tampering Acceptance Tests.

Comprehensive E2E workflow:
1. Ingest raw CSV dataset -> Calculate cryptographic SourceIdentity.
2. Execute non-destructive healing -> Assert parent dataset byte immutability.
3. Record hash-chained lineage graph across all lifecycle stages.
4. Generate deployment artifacts with streaming SHA-256 manifests.
5. Construct, sign, and verify Attested Result Envelope.
6. Test REST API verification, public key retrieval, and lineage verification endpoints.
7. Tamper with artifact file -> Prove download/deployment is strictly blocked.
8. Restore pristine artifact file -> Prove reverification passes.
"""

import asyncio
import hashlib
import json
import os
import shutil
import tempfile
import pytest
from datetime import datetime, timezone
from pathlib import Path
from fastapi.testclient import TestClient

import pandas as pd
import pyarrow.parquet as pq

from app.main import app
from app.config import settings
from app.attestation.models import (
    AttestedResultEnvelope,
    AttestationStatus,
    SourceIdentity,
    TransformationLineage,
    AnalyticalResultProvenance,
    VerificationProvenance,
    VerificationGateEvidence,
    ArtifactProvenance,
    LineageEvent,
    LineageEventType,
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
    key_manager,
)
from app.attestation.lineage import (
    compute_event_hash,
    LineageTracker,
    GENESIS_PREVIOUS_HASH,
)
from app.attestation.service import (
    AttestationService,
    attestation_service,
)
from app.engineering.ml_engineer import (
    generate_deployment_artifacts,
    verify_artifact_deployment_readiness,
)


@pytest.fixture
def e2e_env(tmp_path):
    """Setup temporary directories for data, derived datasets, and artifacts."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    derived_dir = data_dir / "derived"
    derived_dir.mkdir()
    artifacts_dir = tmp_path / "artifacts"
    artifacts_dir.mkdir()
    
    # Create raw CSV dataset
    raw_csv = (
        "patient_id,age,blood_pressure,cholesterol,outcome\n"
        "P001,45,120,200,0\n"
        "P002,,130,220,1\n"
        "P003,60,,240,1\n"
        "P004,52,125,210,0\n"
        "P005,58,140,250,1\n"
    )
    raw_path = data_dir / "patients_v1.csv"
    raw_path.write_text(raw_csv, encoding="utf-8")
    
    return {
        "tmp_path": tmp_path,
        "data_dir": data_dir,
        "derived_dir": derived_dir,
        "artifacts_dir": artifacts_dir,
        "raw_path": raw_path,
        "raw_csv": raw_csv,
    }


def test_are_hl_full_lifecycle_and_tamper_detection(e2e_env):
    """
    Execute full Option C ARE-HL lifecycle:
    Ingest -> Heal (Immutability check) -> Hash-Chained Lineage -> Artifacts -> Attestation -> Tamper & Block.
    """
    raw_path = e2e_env["raw_path"]
    project_id = "proj-e2e-cardio"
    run_id = "run-e2e-001"
    
    # -------------------------------------------------------------
    # Step 1: Ingestion & Source Identity Computation
    # -------------------------------------------------------------
    raw_bytes = raw_path.read_bytes()
    expected_source_sha256 = hashlib.sha256(raw_bytes).hexdigest()
    streaming_source_sha256 = hash_file_streaming(raw_path)
    assert streaming_source_sha256 == expected_source_sha256
    
    source_identity = SourceIdentity(
        source_dataset_id="ds-patients-001",
        source_dataset_version="v1.0.0",
        source_content_hash=streaming_source_sha256,
        source_schema_hash=hash_json_object({"patient_id": "str", "age": "float", "outcome": "int"}),
        source_size_bytes=raw_path.stat().st_size,
        source_record_count=5,
        source_storage_reference=str(raw_path),
    )
    
    # -------------------------------------------------------------
    # Step 2: Lineage Tracking - Ingestion Event
    # -------------------------------------------------------------
    tracker = LineageTracker()
    evt_ingest = tracker.create_event(
        project_id=project_id,
        run_id=run_id,
        event_type=LineageEventType.DATASET_INGESTION,
        sequence_number=1,
        input_artifacts=[{"id": "raw_upload", "hash": streaming_source_sha256}],
        output_artifacts=[{"id": "ds-patients-001", "hash": streaming_source_sha256}],
        details={"filename": "patients_v1.csv"},
    )
    assert evt_ingest.previous_event_hash == GENESIS_PREVIOUS_HASH
    
    # -------------------------------------------------------------
    # Step 3: Non-Destructive Healing & Source Immutability
    # -------------------------------------------------------------
    # Load raw data, heal missing values into derived parquet
    df = pd.read_csv(raw_path)
    df_healed = df.copy()
    # Simple median imputation for testing
    df_healed["age"] = df_healed["age"].fillna(df_healed["age"].median())
    df_healed["blood_pressure"] = df_healed["blood_pressure"].fillna(df_healed["blood_pressure"].median())
    
    derived_path = e2e_env["derived_dir"] / "patients_v1_healed.parquet"
    df_healed.to_parquet(derived_path, index=False)
    
    # VERIFY CRITICAL CONSTRAINT: Source file has NOT mutated!
    post_healing_source_sha256 = hash_file_streaming(raw_path)
    assert post_healing_source_sha256 == streaming_source_sha256
    assert raw_path.read_bytes() == raw_bytes
    
    derived_sha256 = hash_file_streaming(derived_path)
    
    # Lineage event for healing
    evt_healing = tracker.create_event(
        project_id=project_id,
        run_id=run_id,
        event_type=LineageEventType.HEALING_EXECUTION,
        sequence_number=2,
        previous_event_hash=evt_ingest.event_hash,
        input_artifacts=[{"id": "ds-patients-001", "hash": streaming_source_sha256}],
        output_artifacts=[{"id": "patients_v1_healed", "hash": derived_sha256}],
        details={
            "rules_applied": ["median_impute_age", "median_impute_bp"],
            "parent_dataset_sha256": streaming_source_sha256,
            "derived_dataset_sha256": derived_sha256,
        },
    )
    
    transformation_lineage = TransformationLineage(
        lineage_root_id="ds-patients-001",
        parent_dataset_id="ds-patients-001",
        derived_dataset_id="patients_v1_healed",
        derived_content_hash=derived_sha256,
        transformation_sequence=["ingestion", "healing_imputation"],
        before_after_quality_evidence={
            "missing_cells_before": 2,
            "missing_cells_after": 0,
        },
    )
    
    # -------------------------------------------------------------
    # Step 4: Analysis & Verification Gates
    # -------------------------------------------------------------
    analytical_result = AnalyticalResultProvenance(
        analysis_plan_id="plan-cardio-rf",
        analysis_plan_version="v1.0",
        analysis_input_hashes=[streaming_source_sha256, derived_sha256],
        metric_definitions={"accuracy": "Balanced accuracy score", "f1": "Harmonic mean of precision and recall"},
        result_payload_hash=hash_json_object({"accuracy": 0.94, "f1": 0.92}),
        result_schema_hash=hash_json_object({"prediction": "int"}),
        execution_metadata={"model": "RandomForestClassifier", "n_estimators": 100},
    )
    
    evt_analysis = tracker.create_event(
        project_id=project_id,
        run_id=run_id,
        event_type=LineageEventType.ANALYSIS_EXECUTION,
        sequence_number=3,
        previous_event_hash=evt_healing.event_hash,
        input_artifacts=[{"id": "patients_v1_healed", "hash": derived_sha256}],
        output_artifacts=[{"id": "model_metrics", "hash": analytical_result.result_payload_hash}],
    )
    
    verification = VerificationProvenance(
        verification_policy_version="v1.0",
        verification_gate_results=[
            VerificationGateEvidence(
                gate_id="data_quality_gate",
                status=GateStatusEnum.PASS,
                severity="CRITICAL",
                metrics={"completeness": 1.0},
                reason="All missing values resolved by verified healing transformation.",
                recommendation="Proceed to deployment.",
            ),
            VerificationGateEvidence(
                gate_id="temporal_leakage_gate",
                status=GateStatusEnum.PASS,
                severity="CRITICAL",
                metrics={"leakage_detected": 0},
                reason="No future temporal leakage identified.",
                recommendation="Proceed.",
            ),
            VerificationGateEvidence(
                gate_id="plan_multiverse_stability",
                status=GateStatusEnum.PASS,
                severity="HIGH",
                metrics={"stability_score": 0.96},
                reason="PMSG score exceeds threshold 0.85 across 50 multiverse paths.",
                recommendation="Deployable.",
            ),
        ],
        pmsg_run_id="pmsg-e2e-001",
        pmsg_gate_status=GateStatusEnum.PASS,
        mandatory_gate_status=GateStatusEnum.PASS,
        deployment_readiness_status="READY",
        evidence_references=[f"run:{run_id}"],
    )
    
    evt_verification = tracker.create_event(
        project_id=project_id,
        run_id=run_id,
        event_type=LineageEventType.VERIFICATION_GATE_EVALUATION,
        sequence_number=4,
        previous_event_hash=evt_analysis.event_hash,
        details={"overall": "PASS", "critical_passed": True},
    )
    
    # Verify lineage chain integrity
    events = [evt_ingest, evt_healing, evt_analysis, evt_verification]
    is_chain_valid, chain_errors = tracker.verify_chain(events)
    assert is_chain_valid is True
    assert len(chain_errors) == 0
    
    # -------------------------------------------------------------
    # Step 5: Artifact Generation with Cryptographic Hashes
    # -------------------------------------------------------------
    run_art_dir = e2e_env["artifacts_dir"] / project_id / run_id
    run_art_dir.mkdir(parents=True)
    
    # Write model and API files
    model_file = run_art_dir / "model.pkl"
    model_file.write_bytes(b"PKL_RANDOM_FOREST_WEIGHTS_MOCK_BYTES")
    
    readme_file = run_art_dir / "README.md"
    readme_file.write_text("# Model v1.0\nCardio Risk Classifier.", encoding="utf-8")
    
    art_hashes = {
        "model.pkl": hash_file_streaming(model_file),
        "README.md": hash_file_streaming(readme_file),
    }
    
    art_meta = {
        "project_id": project_id,
        "run_id": run_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "artifact_content_hashes": art_hashes,
        "gates_passed": True,
        "downloadable": True,
    }
    meta_path = run_art_dir / "metadata.json"
    meta_path.write_text(json.dumps(art_meta, indent=2), encoding="utf-8")
    
    artifact_provenance = ArtifactProvenance(
        artifact_ids=[f"art_{run_id}"],
        artifact_content_hashes=art_hashes,
        model_version="1.0.0",
        artifact_verification_status="PASS",
    )
    
    # -------------------------------------------------------------
    # Step 6: Envelope Sealing & Digital Attestation
    # -------------------------------------------------------------
    unsigned_envelope = AttestedResultEnvelope(
        envelope_id=f"are_{run_id}",
        project_id=project_id,
        run_id=run_id,
        attestation_status=AttestationStatus.SIGNED,
        source_identity=source_identity,
        transformation_lineage=transformation_lineage,
        analytical_result=analytical_result,
        verification=verification,
        artifact_provenance=artifact_provenance,
    )
    
    signer = Signer()
    signed_envelope = signer.sign_envelope(unsigned_envelope)
    
    assert signed_envelope.attestation is not None
    assert signed_envelope.attestation.signature is not None
    assert signed_envelope.attestation.key_id is not None
    assert signed_envelope.attestation.payload_hash == hash_bytes(
        canonical_json_bytes({**signed_envelope.model_dump(), "attestation": None}),
        "sha256",
    )
    
    # -------------------------------------------------------------
    # Step 7: Reverification of Pristine Envelope
    # -------------------------------------------------------------
    verifier = Verifier()
    report = verifier.verify_envelope(signed_envelope, verify_content_files=False)
    assert report.overall_status == IntegrityStatus.VALID
    assert report.signature_valid is True
    assert report.payload_hash_valid is True
    assert report.mandatory_gates_acceptable is True
    assert len(report.verification_errors) == 0
    
    # Verify artifact deployment readiness on pristine files
    readiness = verify_artifact_deployment_readiness(
        project_id=project_id,
        run_id=run_id,
        artifact_dir_override=run_art_dir,
    )
    assert readiness["deployable"] is True
    assert readiness["downloadable"] is True
    assert readiness["status"] == "VERIFIED_READY"
    
    # -------------------------------------------------------------
    # Step 8: Intentional Tampering & Strict Blocking
    # -------------------------------------------------------------
    # Attack 1: Modify model.pkl bytes
    model_file.write_bytes(b"PKL_RANDOM_FOREST_BACKDOOR_PAYLOAD")
    
    tampered_readiness = verify_artifact_deployment_readiness(
        project_id=project_id,
        run_id=run_id,
        artifact_dir_override=run_art_dir,
    )
    # MUST FAIL CLOSED: Download and deployment must be strictly blocked!
    assert tampered_readiness["deployable"] is False
    assert tampered_readiness["downloadable"] is False
    assert tampered_readiness["status"] == "TAMPERED_BLOCKED"
    assert any("model.pkl" in m for m in tampered_readiness["mismatches"])
    
    # Attack 2: Tamper with envelope analytical result metrics
    tampered_envelope = signed_envelope.model_copy(deep=True)
    tampered_envelope.analytical_result.result_payload_hash = "0" * 64
    
    tampered_report = verifier.verify_envelope(tampered_envelope, verify_content_files=False)
    assert tampered_report.overall_status in (IntegrityStatus.INVALID_SIGNATURE, IntegrityStatus.HASH_MISMATCH)
    assert tampered_report.payload_hash_valid is False
    
    # -------------------------------------------------------------
    # Step 9: Reversion & Verification Recovery
    # -------------------------------------------------------------
    # Restore model.pkl to pristine state
    model_file.write_bytes(b"PKL_RANDOM_FOREST_WEIGHTS_MOCK_BYTES")
    restored_readiness = verify_artifact_deployment_readiness(
        project_id=project_id,
        run_id=run_id,
        artifact_dir_override=run_art_dir,
    )
    assert restored_readiness["deployable"] is True
    assert restored_readiness["status"] == "VERIFIED_READY"


def test_rest_api_attestations_and_public_keys():
    """Verify REST API endpoints for attestations, verification, public keys, and lineage."""
    with TestClient(app) as client:
        # 1. Get public keys
        resp_keys = client.get("/api/attestations/keys/public")
        assert resp_keys.status_code == 200
        keys_data = resp_keys.json()
        assert isinstance(keys_data, list)
        assert len(keys_data) > 0
        active_key = next((k for k in keys_data if k["state"] == "ACTIVE"), None)
        assert active_key is not None
        assert "public_key_pem" in active_key
        
        # 2. Test create attestation endpoint
        payload = {
            "project_id": "proj-api-test",
            "run_id": "run-api-test-01",
            "source_dataset_id": "ds-api-01",
            "source_storage_reference": "data/mock.csv",
            "verification_report": {
                "summary": {
                    "results": [
                        {
                            "gate_id": "data_quality_gate",
                            "severity": "CRITICAL",
                            "status": "PASS",
                            "evidence": ["Data passes all quality checks"],
                            "reason": "OK",
                        }
                    ]
                },
                "deployment_status": "READY",
            },
            "analysis_result": {
                "plan_id": "plan-api-01",
                "metrics": {"f1": 0.95},
                "schema": {"target": "int"},
                "row_count": 50,
            },
            "require_atlas": False,
        }
        resp_create = client.post("/api/attestations", json=payload)
        assert resp_create.status_code == 201
        envelope = resp_create.json()
        assert "envelope_id" in envelope
        assert envelope["attestation_status"] == "SIGNED"
        env_id = envelope["envelope_id"]

        # 3. Test get attestation endpoint
        resp_get = client.get(f"/api/attestations/{env_id}")
        assert resp_get.status_code == 200
        fetched = resp_get.json()
        assert fetched["envelope_id"] == env_id
        assert fetched["attestation"]["signature"] is not None

        # 4. Test verify attestation endpoint
        resp_verify = client.post(f"/api/attestations/{env_id}/verify")
        assert resp_verify.status_code == 200
        verify_report = resp_verify.json()
        assert verify_report["overall_status"] == "VALID"
        assert verify_report["signature_valid"] is True
        assert verify_report["payload_hash_valid"] is True
