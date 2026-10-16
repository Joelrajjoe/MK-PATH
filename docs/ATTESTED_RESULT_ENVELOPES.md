# MK-PATH Option C — Attested Result Envelopes (ARE-HL) Specification

## 1. Overview and Core Philosophy

In traditional analytical systems, consumers of analytical outputs, models, and predictions have no verifiable guarantee regarding where data came from, which specific version of a dataset produced a metric, which transformations or cleaning steps were applied, or whether verification gates were satisfied.

**Attested Result Envelopes with Healing Lineage (ARE-HL)** provide end-to-end cryptographic provenance and non-repudiation for every analytical artifact produced by MK-Path. An Attested Result Envelope is a strongly typed, canonicalized, and digitally signed data structure that binds together:
1. **Source Identity**: Cryptographic fingerprints (streaming SHA-256 and schema hashes) of raw inputs.
2. **Transformation Lineage**: Complete healing operations, rule parameters, before/after data quality metrics, and derived dataset hashes.
3. **Analytical Result Provenance**: Analysis plan ID, input hashes, metric definitions, and deterministic execution details.
4. **Verification Provenance**: Explicit outcomes of all verification gates (data quality, leakage, multiverse stability) and deployment readiness status.
5. **Artifact Provenance**: Cryptographic manifest of all generated model binaries, schemas, and documentation.
6. **Digital Attestation**: Asymmetric cryptographic signature (Ed25519 / RSA-PSS) generated over canonical RFC 8785 JSON bytes.

---

## 2. Envelope Schema & Structure

Envelopes conform to the `are-hl-v1.0` schema standard defined in `backend/app/attestation/models.py`.

```json
{
  "envelope_id": "are_0884d6b5e1cb4659",
  "schema_version": "are-hl-v1.0",
  "project_id": "proj-cardio-01",
  "run_id": "run-cardio-001",
  "created_at": "2026-10-16T15:45:00.000000Z",
  "application_version": "1.0.0",
  "git_commit": "e8a719c",
  "attestation_status": "SIGNED",
  "source_identity": {
    "source_dataset_id": "ds-patients-001",
    "source_dataset_version": "v1.0.0",
    "source_content_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "source_schema_hash": "8f434346648f6b96df89dda901c5176b10a6d83961dd3c1ac88b59b2dc327aa4",
    "source_size_bytes": 1048576,
    "source_record_count": 50000,
    "source_storage_reference": "E:/MKPATH/data/patients.csv"
  },
  "transformation_lineage": {
    "lineage_root_id": "ds-patients-001",
    "parent_dataset_id": "ds-patients-001",
    "derived_dataset_id": "ds_patients_healed_v1",
    "derived_content_hash": "5d41402abc4b2a76b9719d911017c592a8d3da13e8b15d2a832c3bb4869c450a",
    "transformation_sequence": ["profiling", "healing", "analysis"],
    "healing_operation_records": [
      {
        "operation_id": "heal_op_1",
        "action": "IMPUTE_MEDIAN",
        "target_column": "age",
        "parameters": {"strategy": "median"},
        "affected_rows": 42
      }
    ],
    "before_after_quality_evidence": {
      "missing_before": 42,
      "missing_after": 0
    }
  },
  "analytical_result": {
    "analysis_plan_id": "plan-cardio-rf-v1",
    "analysis_plan_version": "v1.0",
    "analysis_input_hashes": [
      "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
      "5d41402abc4b2a76b9719d911017c592a8d3da13e8b15d2a832c3bb4869c450a"
    ],
    "metric_definitions": {
      "accuracy": "Balanced accuracy score across validation folds",
      "f1": "Harmonic mean of precision and recall"
    },
    "result_payload_hash": "b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9",
    "result_schema_hash": "2c26b46b68ffc68ff99b453c1d30413413422d706483bfa0f98a5e886266e7ae",
    "execution_metadata": {
      "engine": "duckdb",
      "model": "RandomForestClassifier",
      "n_estimators": 100
    }
  },
  "verification": {
    "verification_policy_version": "v1.0",
    "verification_gate_results": [
      {
        "gate_id": "data_quality_gate",
        "status": "PASS",
        "severity": "CRITICAL",
        "reason": "100% of required fields pass schema constraints."
      },
      {
        "gate_id": "plan_multiverse_stability",
        "status": "PASS",
        "severity": "HIGH",
        "metrics": {"stability_score": 0.94},
        "reason": "PMSG stability score exceeds threshold."
      }
    ],
    "mandatory_gate_status": "PASS",
    "deployment_readiness_status": "READY"
  },
  "artifact_provenance": {
    "artifact_ids": ["art_run_cardio_001"],
    "artifact_content_hashes": {
      "model.pkl": "a665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3",
      "README.md": "d04b98f48e8f8bcc15c6ae5ac050801cd6dcfd428fb5f9e65c4e16e7807340fa"
    },
    "model_version": "1.0.0",
    "artifact_verification_status": "PASS"
  },
  "attestation": {
    "canonicalization_algorithm": "RFC-8785-JCS",
    "hash_algorithm": "SHA-256",
    "signature_algorithm": "Ed25519",
    "payload_hash": "3f79bb7b435b05321651daefd374cdc681dc06faa65e374e383b787d864f7135",
    "signature": "V293IFJlYWwgRWQyNTUxOSBTaWduYXR1cmUgYnl0ZXMgYmFzZTY0...",
    "key_id": "mkpath-root-v1",
    "key_version": "1.0.0",
    "signing_timestamp": "2026-10-16T15:45:01.000000Z",
    "attestation_policy_version": "ARE-HL-v1.0"
  }
}
```

---

## 3. RFC 8785 JSON Canonicalization Scheme (JCS)

Digital signatures are sensitive to arbitrary serialization differences such as key ordering, whitespace, and floating-point representations. To ensure byte-exact determinism:
- Dictionary keys are lexicographically sorted using UTF-16 code unit order (`sorted(keys)`).
- Separators are stripped of all superfluous whitespace (`separators=(",", ":")`).
- Unicode is preserved in UTF-8 without escaping ASCII characters (`ensure_ascii=False`).
- Floating-point representations normalize standard zero values to prevent `-0.0` vs `0.0` divergence.
- Non-finite numbers (`NaN`, `Infinity`, `-Infinity`) are strictly prohibited and raise `CanonicalizationError`.

Before signing or verifying, the `attestation` property of the envelope dictionary is set to `null` (`None` in Python), producing the exact payload canonical bytes $B$.

---

## 4. Verification Lifecycle

Consumers independently verify an envelope using `POST /api/attestations/{id}/verify` or offline using public keys from `GET /api/attestations/keys/public`:
1. **Key Trust Validation**: Verify `key_id` exists in the public key registry, is marked `trusted=true`, and is not `REVOKED`.
2. **Payload Canonicalization**: Re-canonicalize the envelope dictionary without the `attestation` block.
3. **Payload Hash Check**: Verify $SHA256(B) == payload\_hash$.
4. **Signature Verification**: Execute asymmetric cryptographic signature verification (`pub_key.verify(raw_signature, B)`).
5. **Physical Storage Verification**: If files exist on disk, stream compute their SHA-256 hashes and verify against `source_content_hash`, `derived_content_hash`, and each artifact file in `artifact_content_hashes`.
6. **Gate Policy Enforcement**: Ensure `mandatory_gate_status == PASS` and `deployment_readiness_status != BLOCKED`.
