# MK-PATH Option C — Attestation REST API Reference

The Attestation REST API exposes endpoints for creating, retrieving, verifying, and auditing Attested Result Envelopes and lineage graphs. All endpoints are prefixed under `/api/attestations`.

---

## 1. Envelope Endpoints

### 1.1 Create Attestation Envelope
`POST /api/attestations`
- **Description**: Constructs, canonicalizes, cryptographically signs, and persists an Attested Result Envelope for an analytical run.
- **Request Body (`CreateEnvelopeRequest`)**:
```json
{
  "project_id": "proj-cardio-01",
  "run_id": "run-001",
  "source_dataset_id": "ds-patients-001",
  "source_storage_reference": "data/patients.csv",
  "verification_report": {
    "summary": {"results": [...]},
    "deployment_status": "READY"
  },
  "analysis_result": {
    "plan_id": "plan-rf",
    "metrics": {"accuracy": 0.94},
    "schema": {"prediction": "int"}
  },
  "healing_event": null,
  "artifact_meta": null,
  "require_atlas": false
}
```
- **Response**: `201 Created` with full `AttestedResultEnvelope` JSON.

### 1.2 List Envelopes for Project
`GET /api/attestations?project_id={project_id}`
- **Description**: Returns all attested envelopes associated with the specified project.
- **Response**: `200 OK` with JSON array of envelopes.

### 1.3 Get Envelope by ID
`GET /api/attestations/{envelope_id}`
- **Description**: Retrieves a specific envelope by its unique identifier (e.g., `are_0884d6b5e1cb4659`).
- **Response**: `200 OK` with `AttestedResultEnvelope` JSON, or `404 Not Found`.

### 1.4 Reverity Attestation Envelope
`POST /api/attestations/{envelope_id}/verify`
- **Description**: Independently re-computes the envelope's canonical payload hash, cryptographically verifies the digital signature using the public key trust registry, and re-hashes physical source/derived/artifact files on disk.
- **Response**: `200 OK` with `EnvelopeVerificationReport`:
```json
{
  "envelope_id": "are_0884d6b5e1cb4659",
  "overall_status": "VALID",
  "signature_valid": true,
  "payload_hash_valid": true,
  "content_hashes_valid": true,
  "lineage_complete": true,
  "mandatory_gates_acceptable": true,
  "key_trusted": true,
  "key_id": "mkpath-root-v1",
  "verification_errors": [],
  "verification_warnings": [],
  "verified_at": "2026-10-16T15:50:00Z"
}
```

---

## 2. Lineage & Checkpoint Endpoints

### 2.1 Get Run Lineage Events
`GET /api/attestations/lineage/runs/{run_id}`
- **Description**: Returns the chronological hash-chained lineage events recorded for an analysis run.
- **Response**: `200 OK` with array of `LineageEvent` objects.

### 2.2 Verify Lineage Chain
`POST /api/attestations/lineage/runs/{run_id}/verify`
- **Description**: Traverses the run's lineage event chain and validates sequence numbers, hash pointers (`prev_event_hash`), and payload integrity.
- **Response**: `200 OK`:
```json
{
  "run_id": "run-001",
  "chain_valid": true,
  "event_count": 5,
  "errors": [],
  "head_event_hash": "9c12e8b...01fe"
}
```

### 2.3 Issue Chain Checkpoint
`POST /api/attestations/lineage/runs/{run_id}/checkpoint?project_id={project_id}`
- **Description**: Issues a signed checkpoint over the current chain-head of the run's lineage event graph.
- **Response**: `200 OK` with `ChainCheckpoint` object.

---

## 3. Artifact Readiness & Public Key Endpoints

### 3.1 Verify Artifact Deployment Readiness
`GET /api/attestations/artifacts/{project_id}/{run_id}/verify`
- **Description**: Performs on-disk byte-by-byte streaming SHA-256 verification of all files in `artifacts/{project_id}/{run_id}` against `metadata.json`.
- **Response**: `200 OK`:
```json
{
  "status": "VERIFIED_READY",
  "deployable": true,
  "downloadable": true,
  "reason": "All artifact files verified against attested cryptographic hashes.",
  "mismatches": [],
  "verified_hashes": {
    "model.pkl": "a665a45920...",
    "README.md": "d04b98f48e..."
  }
}
```
*(If modified, returns `status: "TAMPERED_BLOCKED"`, `deployable: false`, `downloadable: false`).*

### 3.2 List Public Verification Keys
`GET /api/attestations/keys/public`
- **Description**: Returns all public verification keys in the active trust store in standard PEM format.
- **Response**: `200 OK` with array of public key records.

### 3.3 Revoke Signing Key
`POST /api/attestations/keys/revoke`
- **Description**: Marks a compromised or retired key as REVOKED.
- **Request Body**:
```json
{
  "key_id": "compromised-key-id",
  "reason": "Suspected private key compromise"
}
```
- **Response**: `200 OK` with updated `KeyRecord`.
