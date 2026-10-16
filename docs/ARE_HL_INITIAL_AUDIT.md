# MK-Path ARE-HL Initial System Audit Report
**Document ID:** `ARE-HL-AUDIT-001`  
**Date:** 2026-10-16  
**Auditor Roles:** Principal Data Provenance Architect, Cryptographic Systems Engineer, Software Supply-Chain Security Engineer, Data Reliability Engineer  
**Workspace:** `E:\MKPATH`  
**Git Branch / Commit:** `main` @ `3c8745d`  

---

## 1. Executive Summary

This audit establishes the baseline empirical findings across existing MK-Path subsystems prior to implementing **Attested Result Envelopes with Healing Lineage (ARE-HL)**.

The audit verified actual behaviors across:
- `backend/app/healing/engine.py` (autonomous healing, before/after scoring, derived dataset creation)
- `backend/app/verification/engine.py` (central verification gates, deployment readiness)
- `backend/app/engineering/ml_engineer.py` (FastAPI deployment artifact generation, artifact inference validation, model card creation)
- `backend/app/routers/runs.py` (run orchestration, MongoDB persistence)
- `backend/app/ingestion/` (format parsing, DuckDB registration, Parquet storage, file security)
- `backend/app/stability/` (Plan-Multiverse Stability Gate - PMSG, variant execution, rank correlation)
- `backend/app/benchmark/` (Fault-Injection Benchmark - FIB-VG, 42 scenarios, containment testing)
- `backend/app/database.py` & `backend/app/audit.py` (MongoDB Atlas connectivity, audit event logging, fallback behaviors)
- `frontend/src/pages/projects/` (Verification, Healing, Artifacts, Audit, and Overview UI)

### Key Audit Findings
1. **Source Immutability in Memory vs. Cryptographic Provenance:**
   - In `backend/app/healing/engine.py`, healing creates a copy (`derived_df = dataset.copy()`) and outputs a new parquet file (`settings.DATA_DIR / "derived" / f"{derived_id}.parquet"`), preserving the source in memory.
   - **Defect:** No cryptographic content hash (SHA-256) is computed for the parent dataset or derived dataset before or after healing. No immutability check is performed by recalculating parent bytes. No hash-chained lineage envelope exists.
2. **Central Verification & Gate Enforcement:**
   - In `backend/app/verification/engine.py`, `run_verification_gates` executes deterministic gates (Data Quality, Temporal Leakage, PMSG) and returns `DeploymentReadinessReport` with `deployment_status = READY | BLOCKED`.
   - In `backend/app/engineering/ml_engineer.py`, artifact generation checks `verification_report.get("deployment_status") != "READY"` and aborts if blocked, generating `DIAGNOSTIC_REPORT.md`.
   - **Defect:** The verification report is not cryptographically signed. No content hash of the generated model artifacts (`model.pkl`, `api/main.py`, `MODEL_CARD.md`) is bound to the verification outcome. A client or attacker could modify artifact bytes on disk without detection.
3. **PMSG Denominator / Estimand Classification & Test Baseline:**
   - Out of 105 total backend tests, 102 passed, 3 failed.
   - PMSG successfully isolates estimand divergences (`var_denom_within_group_rate` vs `var_denom_population_share`), but when metadata lookups fail or datasets are not present in Atlas, tests encounter 404s.
   - If PMSG encounters an unresolved issue or gate failure, the attestation system must strictly preserve that status as `FAIL` or `HUMAN_REVIEW` and **must never sign it as verified analytical robustness**.
4. **Cryptographic Primitives & Key Management:**
   - `cryptography` was missing from `requirements.txt` (now installed: `cryptography 50.0.2`).
   - No public/private key pairs, digital signatures (Ed25519/RSA-PSS), canonical payload hashing, or key rotation existed.
5. **MongoDB Atlas Persistence & Storage Fallback Constraint:**
   - `backend/app/database.py` has a local JSON fallback (`LocalFallbackDB`).
   - Under the ARE-HL specification constraints: **"Do not silently introduce local JSON, SQLite, or another storage fallback. If Atlas is unavailable, fail closed for operations requiring durable attestation. Return a clear error and do not claim that the attestation was saved."**
   - The attestation service must require genuine Atlas persistence and fail-closed with structured errors (`ATLAS_PERSISTENCE_REQUIRED` / `ATLAS_UNAVAILABLE`) if Atlas is unreachable.

---

## 2. Component Audit Matrix

| Component | Source File & Function | Existing Behavior | Test Performed | Actual Outcome | Identified Defect | Decision | Reason |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Healing Engine** | `backend/app/healing/engine.py` -> `apply_healing()` | Transforms DataFrame, writes derived Parquet, generates `HealingEvent` with scores. | Checked execution in `test_remediation.py`. | Derived dataset created; parent memory unmutated. | Lacks parent/child SHA-256 byte hashing, immutability verification, and envelope generation. | **Extend** | Real healing logic is solid and non-destructive; needs cryptographic hash calculation, immutability check, and lineage binding. |
| **Central Verification Engine** | `backend/app/verification/engine.py` -> `run_verification_gates()` | Evaluates Data Quality, Temporal Leakage, and PMSG gates. Produces `DeploymentReadinessReport`. | Tested in `test_fib_vg.py` & `test_pmsg.py`. | Correctly marks `BLOCKED` when critical gates fail. | Unsigned report; gate results not bound to cryptographic attestation payload; no envelope ID. | **Extend** | Core gating logic enforces hard stops; needs binding into strongly-typed ARE-HL schema. |
| **ML Engineer Artifacts** | `backend/app/engineering/ml_engineer.py` -> `generate_deployment_artifacts()` | Generates `model.pkl`, `api/main.py`, `MODEL_CARD.md`, validates real inference. Blocks if not `READY`. | Tested in `test_remediation.py` and `test_fib_vg.py`. | Produces artifacts and `DIAGNOSTIC_REPORT.md` on block. | No artifact content hashing, no signed manifest, no verification check before download/deploy. | **Extend** | Generation and validation are real; must bind artifact content hashes, verify envelope signature before download/deploy. |
| **Ingestion Pipeline** | `backend/app/ingestion/service.py` -> `ingest_file()` | Parses files into normalized Parquet on `E:\MKPATH\data`, registers DuckDB views. | Tested in `test_ingestion.py` (36 tests). | 36 passed. Normalizes files to Parquet. | Stores file size and schema, but does not calculate SHA-256 content hash of ingested file or Parquet. | **Extend** | Robust ingestion; needs streaming chunked SHA-256 hash computation stored on dataset record. |
| **PMSG Stability Gate** | `backend/app/stability/gate.py` -> `evaluate_gate_decision()` | Evaluates multiverse stability across specifications, prevents silent pass. | Tested in `test_pmsg.py` (15 tests). | 13 passed, 2 failed on missing dataset doc. | Does not generate signed proof of robustness; does not bind run to envelope. | **Extend** | Math and gate rules are verified; attestation must reference PMSG run ID, dataset hash, policy version, and result hash. |
| **Audit Logging** | `backend/app/audit.py` -> `record_audit()` | Writes audit documents to `audit_events` collection in MongoDB. | Code inspection & `test_remediation.py`. | Audit records created asynchronously. | Audit records are loose documents, not cryptographically hash-chained (`event_hash = SHA256(canonical || prev_hash)`). | **Extend** | Keep central audit collection, add hash-chained lineage events and signed chain-head checkpoints. |
| **Database Manager** | `backend/app/database.py` -> `DatabaseManager` | Manages AsyncMongoClient with fallback to local JSON. | Unit tests in `test_local_database.py`. | Fallback active when Atlas unreachable. | Silent fallback violates Option C requirement for durable attestation persistence. | **Repair / Enforce** | For ARE-HL records, check `db_manager.is_ready()` (connected to Atlas). Fail-closed if Atlas unavailable. |
| **Run Orchestrator** | `backend/app/routers/runs.py` -> `execute_run()` | LangGraph state graph execution, stores run document in `runs` collection. | Code inspection & router routes. | Stores run state in MongoDB. | Result outputs are not sealed in an Attested Result Envelope with cryptographic signature. | **Extend** | Seal completed run states into signed envelopes with parent lineage and verification gates. |
| **Cryptographic Provenance** | None (`backend/app/attestation/` missing) | Non-existent. No digital signatures, key management, or canonical serializers. | Checked imports & repo search. | Missing. | System cannot prove non-repudiation, tamper-evidence, or external verifiability. | **Implement (New)** | Build `backend/app/attestation/` subsystem: `models.py`, `hashing.py`, `crypto.py`, `lineage.py`, `service.py`. |
| **Attestation APIs** | None (`/api/attestations`, `/api/lineage` missing) | Non-existent. | Endpoint discovery. | Missing. | Consumers cannot fetch, inspect, or verify envelopes or lineage graphs via REST. | **Implement (New)** | Create `backend/app/routers/attestations.py` and register in `main.py`. |
| **Frontend Provenance UI** | `frontend/src/pages/projects/` (Verification, Healing, Artifacts, Audit) | Displays verification gates and healing metrics, but has no attestation badge, lineage graph, or evidence panel. | UI inspection & production build. | Built in 628ms with 0 errors. | Lacks cryptographic attestation status, hash verification buttons, and interactive lineage explorer. | **Extend** | Integrate Attestation Badge, Evidence Panel, and Tamper-Evident Lineage Explorer into existing tabs. |

---

## 3. Cryptographic & Security Baseline

1. **Digital Signature Primitive Selection:**
   - **Ed25519** (pure Edwards-curve Digital Signature Algorithm, RFC 8032) is selected as the primary signature scheme for ARE-HL due to high performance, deterministic signatures, collision resilience, and zero risk of bad RNG side-channel vulnerabilities during signing.
   - **RSA-PSS** (PKCS#1 v2.1 with SHA-256 and PSS padding) is also supported for enterprise PKI compatibility.
   - Algorithm identifiers: `Ed25519` and `RSA-PSS-SHA256`.
2. **Canonicalization Specification:**
   - Canonical JSON serialization following RFC 8785 (JSON Canonicalization Scheme - JCS):
     - UTF-8 byte encoding
     - Lexicographically sorted dictionary keys
     - No whitespace between tokens (` separators=(',', ':') `)
     - Datetime values strictly ISO-8601 UTC (`YYYY-MM-DDTHH:MM:SS.ffffffZ`)
     - Rejection of non-finite numbers (`NaN`, `Infinity`)
     - Explicit handling of None/null values
3. **Content Hashing:**
   - Chunked streaming SHA-256 (64 KB chunks) for physical files (Parquet, PKL, CSV, ZIP, scripts).
   - Never hash file path or timestamps.
   - Record `hash_algorithm: "SHA-256"` and `hash_version: "v1.0"`.
4. **Lineage Hash Chaining:**
   - `event_hash = SHA256(canonical_event_bytes || previous_event_hash_bytes)`
   - Genesis event has `previous_event_hash = "0" * 64`.
   - Signed chain-head checkpoint: contains `chain_id`, `sequence_number`, `final_event_hash`, `timestamp`, `key_id`, signed by the attestation key.
5. **Key Management & Storage:**
   - Private signing keys must be loaded from configured environment variables or secure key files outside source control (`MKPATH_SIGNING_PRIVATE_KEY` / `MKPATH_SIGNING_KEY_PATH`).
   - For local development, if non-production mode is explicitly enabled (`MKPATH_DEV_SIGNING=true`), an isolated ephemeral test key may be initialized and clearly flagged as `MKPATH_DEV_KEY_v1` (with `trusted=False` in production policy).
   - In production (`MKPATH_ENV=production`), missing or untrusted private keys **fail closed**.
   - Private keys are NEVER exposed via API responses or sent to LLMs/browsers.

---

## 4. Remediation and Implementation Plan

Following Phase Zero audit, execution proceeds through the remaining phases:
- **Phase 1:** Strongly-typed Pydantic schema for `AttestedResultEnvelope`, `LineageEvent`, `VerificationGateResult`, `ChainCheckpoint`, `EnvelopeVerificationReport`.
- **Phase 2:** Canonicalization (RFC 8785 JCS) and chunked SHA-256 hashing.
- **Phase 3:** Ed25519 / RSA-PSS digital signing, key manager with rotation and revocation support, and independent verifier.
- **Phase 4:** Healing integration: capture parent/child SHA-256, enforce source immutability, record before/after quality metrics.
- **Phase 5:** Tamper-evident lineage graph: hash-chained event series and signed chain-head checkpoints.
- **Phase 6:** Verification engine & PMSG integration: bind gate results and PMSG run hashes, fail-closed on critical gate failures.
- **Phase 7:** Artifact attestation & deployment protection: bind model artifacts to hashes, block downloads/deployments if hash mismatches or mandatory gates failed.
- **Phase 8:** MongoDB Atlas persistence: store envelopes, lineage events, and checkpoints with justified indexes. Fail closed if Atlas is unavailable.
- **Phase 9:** REST API contracts: `/api/attestations`, `/api/attestations/{id}/verify`, `/api/lineage/{dataset_id}`, `/api/lineage/runs/{run_id}`.
- **Phase 10:** Frontend integration: Attestation badge, Evidence panel, and Lineage timeline across Verification, Healing, Artifacts, and Audit tabs.
- **Phase 11-16:** Security test suite, E2E acceptance test, operational documentation, no-mock audit, and GitHub push.
