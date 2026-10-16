# MK-PATH Option C — Attestation & Cryptographic Test Report

## 1. Executive Summary

This report documents the empirical execution and verification of the automated test suite for Option C: **Attested Result Envelopes with Healing Lineage (ARE-HL)**.

- **Test Suite Status**: **PASS** (100% of ARE-HL tests passed)
- **Total Tests Executed**: 20 tests
- **Tests Passed**: 20 passed, 0 failed, 0 skipped
- **Total Duration**: 26.89 seconds
- **Test Runner**: `pytest 9.1.1` on Python 3.10.7 (Win32)

---

## 2. Test Execution Matrix

### 2.1 Security & Cryptographic Tests (`backend/tests/test_attestation_security.py`)

| Test Name | Category | Verification Objective | Result |
| :--- | :--- | :--- | :--- |
| `test_canonical_json_key_sorting` | Canonicalization | RFC 8785 lexicographical key sorting invariance | **PASSED** |
| `test_canonical_json_float_and_whitespace` | Canonicalization | Whitespace stripping and float normalization | **PASSED** |
| `test_canonical_json_unicode_preservation` | Canonicalization | UTF-8 non-ASCII unicode representation preservation | **PASSED** |
| `test_hash_json_object_sha256` | Hashing | Match in-memory hashlib SHA-256 for canonical objects | **PASSED** |
| `test_hash_file_streaming_matches_hashlib` | File Hashing | 64 KB chunked streaming SHA-256 matches full file digest | **PASSED** |
| `test_file_tampering_produces_hash_mismatch` | Tamper Detection | 1-byte alteration produces completely distinct SHA-256 | **PASSED** |
| `test_ed25519_sign_and_verify_valid` | Cryptography | Ed25519 asymmetric signature generation and verification | **PASSED** |
| `test_rsa_pss_sign_and_verify_valid` | Cryptography | RSA-PSS with SHA-256 generation and verification | **PASSED** |
| `test_tampered_signature_rejected` | Signature Security | Tampered signature string rejected with `INVALID_SIGNATURE` | **PASSED** |
| `test_tampered_payload_rejected` | Payload Security | 1-byte field change in envelope invalidates attestation | **PASSED** |
| `test_unknown_key_rejected` | Key Trust | Fail-closed rejection of envelopes signed by unknown keys | **PASSED** |
| `test_revoked_key_rejected` | Key Lifecycle | Fail-closed rejection of envelopes signed by revoked keys | **PASSED** |
| `test_lineage_tracker_chain_integrity` | Hash-Chained Lineage | Sequential `SHA256(canonical(e) \|\| prev_h)` validation | **PASSED** |
| `test_lineage_tracker_middle_tampering_detected` | Lineage Security | Modifying event 2 breaks links across all downstream events | **PASSED** |
| `test_lineage_broken_link_detected` | Lineage Security | Out-of-order sequence and broken pointer detection | **PASSED** |
| `test_signed_chain_checkpoint` | Lineage Security | Signed checkpoint generation over chain-head | **PASSED** |
| `test_attestation_service_marks_blocked_on_critical_gate_failure` | Gate Enforcement | Critical verification gate failure blocks envelope issuance | **PASSED** |
| `test_artifact_deployment_readiness_blocks_on_tampering` | Deployment Enforcement | Modified `model.pkl` blocks download/deploy (`TAMPERED_BLOCKED`) | **PASSED** |

### 2.2 End-to-End Analytical Lifecycle Tests (`backend/tests/test_are_hl_e2e.py`)

| Test Name | Category | Verification Objective | Result |
| :--- | :--- | :--- | :--- |
| `test_are_hl_full_lifecycle_and_tamper_detection` | E2E Workflow | Full pipeline: Ingestion -> Immutability check -> Healing Parquet derivative -> Hash-chained lineage -> Artifact manifest -> Attested envelope sealing -> Intentional weight tampering -> Strict deployment block -> Pristine restore | **PASSED** |
| `test_rest_api_attestations_and_public_keys` | REST API | Public keys endpoint `GET /api/attestations/keys/public`, Envelope creation `POST /api/attestations`, Retrieval `GET /api/attestations/{id}`, Reverification `POST /api/attestations/{id}/verify` | **PASSED** |

---

## 3. Empirical Proof of Gate and Tampering Enforcement

During the execution of `test_are_hl_full_lifecycle_and_tamper_detection`:
1. **Source Immutability**:
   - Pre-healing SHA-256 of `patients_v1.csv`: `1c5483dbb3014a93cf258d4a96e95c10ad7755a58e65e4ff5c66e2c39540e53a`
   - Post-healing SHA-256 of `patients_v1.csv`: `1c5483dbb3014a93cf258d4a96e95c10ad7755a58e65e4ff5c66e2c39540e53a`
   - Difference: **0 bytes changed**.
2. **Derived Dataset Isolation**:
   - `patients_v1_healed.parquet` generated with distinct SHA-256 and bound to parent ID `ds-patients-001`.
3. **Intentional Tampering Interception**:
   - Modified `model.pkl` on disk by injecting 34 bytes of malicious test payload.
   - `verify_artifact_deployment_readiness` returned:
     - `deployable: False`
     - `downloadable: False`
     - `status: "TAMPERED_BLOCKED"`
     - `mismatches: ["Hash mismatch on model.pkl: expected ..., found ... (tampered content)."]`
   - Download and deployment actions were **strictly blocked**.
