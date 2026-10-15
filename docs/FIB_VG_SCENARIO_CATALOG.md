# FIB-VG Scenario Catalog Specification
## Fault-Injection Benchmark for Verification Gates — Catalog Version 1.0.0

This catalog defines the versioned, independent test oracle specifications for all 42 scenarios (34 controlled fault injection scenarios and 8 clean control scenarios) implemented in MK-Path Option B.

All expected outcomes are defined **a priori and independently** of the verification components under test. No verifier is permitted to determine its own ground truth.

---

## Catalog Summary by Category

| Category | Total | Fault Scenarios | Clean Controls | Critical Severity | High Severity | Medium Severity | Low Severity |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Data Integrity (`DAT`)** | 6 | 5 | 1 | 1 | 3 | 1 | 1 |
| **Analytical Correctness (`ANA`)** | 5 | 4 | 1 | 1 | 3 | 0 | 1 |
| **Semantic & Governance (`SEM`)** | 5 | 4 | 1 | 2 | 2 | 1 | 0 |
| **Agent Orchestration (`AGT`)** | 5 | 4 | 1 | 2 | 2 | 1 | 0 |
| **Verification Gate Bypass (`BYP`)** | 6 | 5 | 1 | 3 | 2 | 0 | 1 |
| **Storage & Persistence (`STO`)** | 5 | 4 | 1 | 1 | 3 | 1 | 0 |
| **Frontend & API Integrity (`API`)** | 5 | 4 | 1 | 0 | 3 | 1 | 1 |
| **Audit & Evidence (`AUD`)** | 5 | 4 | 1 | 0 | 4 | 1 | 0 |
| **Total** | **42** | **34** | **8** | **12** | **15** | **11** | **4** |

---

## Detailed Scenario Specifications

### Category A: Data Integrity Faults

#### `FIB-DAT-001`: Mandatory Column Missing
- **Severity**: `HIGH`
- **Target Component**: Schema Validator / Data Ingestion (`run_verification_gates`)
- **Preconditions**: Valid synthetic baseline DataFrame with columns `['record_id', 'group_id', 'numerator_val', 'denominator_val', 'metric_value']`.
- **Injection Method**: `df.drop(columns=['denominator_val'])`
- **Expected Detection**: `True`
- **Expected Diagnosis**: `SCHEMA_VALIDATION_ERROR`
- **Expected Gate Outcome**: `FAIL`
- **Expected Deployment Blocked**: `False`
- **Expected Audit Evidence**: Evidence must record `missing_columns: ['denominator_val']`.
- **Cleanup & Isolation**: Disposable in-memory copy; no disk persistence.

#### `FIB-DAT-002`: Invalid Numeric Datatype
- **Severity**: `HIGH`
- **Target Component**: Schema Validator / Column Classification
- **Preconditions**: Valid numeric DataFrame.
- **Injection Method**: Cast numeric column to object and inject string `"CORRUPT_NOT_A_NUMBER"`.
- **Expected Detection**: `True`
- **Expected Diagnosis**: `DATATYPE_MISMATCH`
- **Expected Gate Outcome**: `FAIL`
- **Expected Deployment Blocked**: `False`
- **Cleanup & Isolation**: Pure in-memory transformation.

#### `FIB-DAT-003`: Null Values in Mandatory Business Key
- **Severity**: `HIGH`
- **Target Component**: Data Ingestion Completeness Verifier
- **Preconditions**: Dataset with valid primary key `record_id`.
- **Injection Method**: Set 25% of `record_id` values to `None` / `np.nan`.
- **Expected Detection**: `True`
- **Expected Diagnosis**: `NULL_KEY_VIOLATION`
- **Expected Gate Outcome**: `FAIL`
- **Expected Deployment Blocked**: `False`
- **Cleanup & Isolation**: Pure in-memory transformation.

#### `FIB-DAT-004`: Dropped Rows During Processing (Critical)
- **Severity**: `CRITICAL`
- **Target Component**: Transformation Ingestion Verifier & Deployment Pipeline
- **Preconditions**: Expected row count = 100.
- **Injection Method**: Silently slice `df = df.iloc[:70]` (30% row drop without tombstone flags).
- **Expected Detection**: `True`
- **Expected Diagnosis**: `ROW_COUNT_DISCREPANCY`
- **Expected Gate Outcome**: `FAIL`
- **Expected Deployment Blocked**: `True`
- **Cleanup & Isolation**: Isolated pipeline run.

#### `FIB-DAT-005`: Schema Mismatch Between Source and Output
- **Severity**: `MEDIUM`
- **Target Component**: Schema Drift Verifier
- **Preconditions**: Baseline schema version `1.0`.
- **Injection Method**: Add unexpected column `_unauthorized_extra_feature`.
- **Expected Detection**: `True`
- **Expected Diagnosis**: `SCHEMA_DRIFT_DETECTED`
- **Expected Gate Outcome**: `FAIL`
- **Expected Deployment Blocked**: `False`

#### `FIB-DAT-006`: Clean Baseline Dataset (Clean Control)
- **Severity**: `LOW`
- **Target Component**: Schema Validator & Data Quality Engine
- **Preconditions**: Standard valid synthetic dataset meeting all schema contracts.
- **Injection Method**: None (Pass clean data unchanged).
- **Expected Detection**: `False` (Must not trigger false positive)
- **Expected Diagnosis**: `NONE`
- **Expected Gate Outcome**: `PASS`
- **Expected Deployment Blocked**: `False`

---

### Category B: Analytical Correctness Faults

#### `FIB-ANA-001`: Altered Denominator Causing Ratio Distortion (Critical)
- **Severity**: `CRITICAL`
- **Target Component**: KPI Calculation Engine & Plan-Multiverse Stability Gate (PMSG)
- **Preconditions**: KPI ratio = `numerator / denominator`.
- **Injection Method**: Shift denominator by factor of 3.0, falsifying analytical metrics.
- **Expected Detection**: `True`
- **Expected Diagnosis**: `RATIO_CALCULATION_DISTORTION`
- **Expected Gate Outcome**: `FAIL`
- **Expected Deployment Blocked**: `True`

#### `FIB-ANA-002`: Metric Exceeds Baseline Tolerance
- **Severity**: `HIGH`
- **Target Component**: Statistical Tolerance Verifier
- **Preconditions**: Historical mean metric = 10.0, std = 1.0.
- **Injection Method**: Multiply metric values by 4.5.
- **Expected Detection**: `True`
- **Expected Diagnosis**: `STATISTICAL_OUTLIER_TOLERANCE_EXCEEDED`
- **Expected Gate Outcome**: `FAIL`
- **Expected Deployment Blocked**: `False`

#### `FIB-ANA-003`: Plan-Multiverse Stability Gate Instability
- **Severity**: `HIGH`
- **Target Component**: Plan-Multiverse Stability Gate (PMSG)
- **Preconditions**: Multi-plan variation evaluation across 10 simulation paths.
- **Injection Method**: High variance perturbation across multiverse plans ($CV = 0.35$, threshold $= 0.15$).
- **Expected Detection**: `True`
- **Expected Diagnosis**: `MULTIVERSE_STABILITY_VIOLATION`
- **Expected Gate Outcome**: `FAIL`
- **Expected Deployment Blocked**: `False`

#### `FIB-ANA-004`: Inverted Ranking Discrepancy
- **Severity**: `HIGH`
- **Target Component**: Ranking & Sorting Verifier
- **Preconditions**: Top-K rankings determined by analytical score.
- **Injection Method**: Reverse sorting order while asserting descending order.
- **Expected Detection**: `True`
- **Expected Diagnosis**: `RANKING_INVERSION_ERROR`
- **Expected Gate Outcome**: `FAIL`
- **Expected Deployment Blocked**: `False`

#### `FIB-ANA-005`: Deterministic Recalculation Match (Clean Control)
- **Severity**: `LOW`
- **Target Component**: Analytical Verifier & Recalculation Check
- **Preconditions**: Exact mathematical calculations.
- **Injection Method**: None (Clean analytical execution).
- **Expected Detection**: `False`
- **Expected Diagnosis**: `NONE`
- **Expected Gate Outcome**: `PASS`
- **Expected Deployment Blocked**: `False`

---

### Category C: Semantic and Information Governance Faults

#### `FIB-SEM-001`: Restricted Column Leaked into Analytical Output (Critical)
- **Severity**: `CRITICAL`
- **Target Component**: Information Governance & Policy Enforcer
- **Preconditions**: Project policy restricts columns matching `SSN`, `CREDIT_CARD`, `PASSWORD`.
- **Injection Method**: Inject column `restricted_tax_identifier_ssn` into analytical payload.
- **Expected Detection**: `True`
- **Expected Diagnosis**: `PII_LEAKAGE_DETECTED`
- **Expected Gate Outcome**: `FAIL`
- **Expected Deployment Blocked**: `True`

#### `FIB-SEM-002`: Raw Secret Token Leaked into Logs or Evidence
- **Severity**: `HIGH`
- **Target Component**: Evidence Envelope Sanitizer
- **Preconditions**: Evidence logging enabled.
- **Injection Method**: Inject bearer token `sk_live_secret_auth_token_9999` into evidence fields.
- **Expected Detection**: `True`
- **Expected Diagnosis**: `SECRET_EXPOSURE_IN_AUDIT`
- **Expected Gate Outcome**: `FAIL`
- **Expected Deployment Blocked**: `False`

#### `FIB-SEM-003`: Cross-Tenant Dataset Access Attempt (Critical)
- **Severity**: `CRITICAL`
- **Target Component**: Workspace Boundary & Tenant Isolation Gate
- **Preconditions**: Active project `proj_alpha`.
- **Injection Method**: Request references dataset belonging to `proj_beta_foreign_tenant`.
- **Expected Detection**: `True`
- **Expected Diagnosis**: `CROSS_TENANT_ACCESS_DENIED`
- **Expected Gate Outcome**: `FAIL`
- **Expected Deployment Blocked**: `True`

#### `FIB-SEM-004`: Document Classification Confused for Authorization
- **Severity**: `HIGH`
- **Target Component**: Semantic Access Controller
- **Preconditions**: Document classified as `PUBLIC_MARKETING`.
- **Injection Method**: Attempt export to restricted system without cryptographic authorization token.
- **Expected Detection**: `True`
- **Expected Diagnosis**: `AUTHORIZATION_TOKEN_MISSING`
- **Expected Gate Outcome**: `FAIL`
- **Expected Deployment Blocked**: `False`

#### `FIB-SEM-005`: Legitimate Authorized Project Access (Clean Control)
- **Severity**: `MEDIUM`
- **Target Component**: Tenant Access & Governance Gate
- **Preconditions**: Valid project token, matching workspace.
- **Injection Method**: None.
- **Expected Detection**: `False`
- **Expected Diagnosis**: `NONE`
- **Expected Gate Outcome**: `PASS`
- **Expected Deployment Blocked**: `False`

---

### Category D: Agent State and Orchestration Faults

#### `FIB-AGT-001`: Agent Returns Malformed Output
- **Severity**: `HIGH`
- **Target Component**: Agent Envelope Validator
- **Preconditions**: Expected agent payload: JSON dictionary with `status`, `results`, `envelope`.
- **Injection Method**: Return non-JSON string or malformed schema missing `envelope`.
- **Expected Detection**: `True`
- **Expected Diagnosis**: `AGENT_OUTPUT_SCHEMA_INVALID`
- **Expected Gate Outcome**: `FAIL`
- **Expected Deployment Blocked**: `False`

#### `FIB-AGT-002`: Agent Omits Mandatory Evidence
- **Severity**: `HIGH`
- **Target Component**: Agent Evidence Contract Gate
- **Preconditions**: Agent must attach `provenance_hash` and `execution_step_id`.
- **Injection Method**: `del payload['evidence']['provenance_hash']`
- **Expected Detection**: `True`
- **Expected Diagnosis**: `MISSING_AGENT_PROVENANCE`
- **Expected Gate Outcome**: `FAIL`
- **Expected Deployment Blocked**: `False`

#### `FIB-AGT-003`: Prerequisite Stage Failed but Agent Reports Success (Critical)
- **Severity**: `CRITICAL`
- **Target Component**: Orchestration Pipeline State Machine
- **Preconditions**: Stage 2 depends on Stage 1. Stage 1 failed with error.
- **Injection Method**: Force Stage 2 to execute and report `COMPLETED` despite Stage 1 failure.
- **Expected Detection**: `True`
- **Expected Diagnosis**: `ORCHESTRATION_PREREQUISITE_VIOLATION`
- **Expected Gate Outcome**: `FAIL`
- **Expected Deployment Blocked**: `True`

#### `FIB-AGT-004`: Mandatory Verification Stage Skipped (Critical)
- **Severity**: `CRITICAL`
- **Target Component**: Pipeline Stage Completion Enforcer
- **Preconditions**: Pipeline requires `[Ingestion, Validation, Verification, ArtifactGeneration]`.
- **Injection Method**: Omit `Verification` stage from pipeline execution list.
- **Expected Detection**: `True`
- **Expected Diagnosis**: `MANDATORY_STAGE_OMITTED`
- **Expected Gate Outcome**: `FAIL`
- **Expected Deployment Blocked**: `True`

#### `FIB-AGT-005`: Complete Pipeline Execution in Order (Clean Control)
- **Severity**: `MEDIUM`
- **Target Component**: Pipeline Orchestration Engine
- **Preconditions**: Normal sequential pipeline execution.
- **Injection Method**: None.
- **Expected Detection**: `False`
- **Expected Diagnosis**: `NONE`
- **Expected Gate Outcome**: `PASS`
- **Expected Deployment Blocked**: `False`

---

### Category E: Verification Gate Bypass Faults

#### `FIB-BYP-001`: Failed Verifier Incorrectly Reported as Passed (Critical)
- **Severity**: `CRITICAL`
- **Target Component**: Gate Aggregation Logic
- **Preconditions**: Verification gate returned `status='FAIL'`.
- **Injection Method**: Aggregator attempt to overwrite gate status to `'PASS'`.
- **Expected Detection**: `True`
- **Expected Diagnosis**: `VERIFIER_TAMPERING_DETECTED`
- **Expected Gate Outcome**: `FAIL`
- **Expected Deployment Blocked**: `True`

#### `FIB-BYP-002`: Critical Failed Gate Ignored by Downstream Consumer (Critical)
- **Severity**: `CRITICAL`
- **Target Component**: ML Model Deployment Artifact Generator
- **Preconditions**: Verification gates evaluated with critical failure.
- **Injection Method**: Call `generate_deployment_artifacts` without verifying gate state.
- **Expected Detection**: `True`
- **Expected Diagnosis**: `DEPLOYMENT_GATE_BYPASS_ATTEMPT`
- **Expected Gate Outcome**: `FAIL`
- **Expected Deployment Blocked**: `True`

#### `FIB-BYP-003`: Failed Verification Stage Omitted from Aggregate Result
- **Severity**: `HIGH`
- **Target Component**: Gate Result Envelope Builder
- **Preconditions**: 3 gates evaluated: Gate 1 (PASS), Gate 2 (FAIL), Gate 3 (PASS).
- **Injection Method**: Filter out Gate 2 from the summary list so only PASS results appear.
- **Expected Detection**: `True`
- **Expected Diagnosis**: `OMITTED_GATE_RESULT_IN_AGGREGATE`
- **Expected Gate Outcome**: `FAIL`
- **Expected Deployment Blocked**: `False`

#### `FIB-BYP-004`: Mandatory Gate Silently Skipped
- **Severity**: `HIGH`
- **Target Component**: Policy Gate Completeness Verifier
- **Preconditions**: Policy mandates `['SCHEMA', 'VALUE_INTEGRITY', 'MULTIVERSE_STABILITY']`.
- **Injection Method**: Evaluate only `['SCHEMA', 'VALUE_INTEGRITY']`.
- **Expected Detection**: `True`
- **Expected Diagnosis**: `REQUIRED_GATE_NOT_EVALUATED`
- **Expected Gate Outcome**: `FAIL`
- **Expected Deployment Blocked**: `False`

#### `FIB-BYP-005`: Stale Verification Result Reused for Different Dataset (Critical)
- **Severity**: `CRITICAL`
- **Target Component**: Result Binding & Dataset Fingerprint Verifier
- **Preconditions**: Dataset A with hash `abc123` verified. Dataset B has hash `xyz789`.
- **Injection Method**: Submit verification certificate of Dataset A to approve Dataset B.
- **Expected Detection**: `True`
- **Expected Diagnosis**: `DATASET_FINGERPRINT_MISMATCH`
- **Expected Gate Outcome**: `FAIL`
- **Expected Deployment Blocked**: `True`

#### `FIB-BYP-006`: All Required Gates Executed and Passed (Clean Control)
- **Severity**: `LOW`
- **Target Component**: Gate Aggregation & Deployment Enforcer
- **Preconditions**: Clean valid verification run.
- **Injection Method**: None.
- **Expected Detection**: `False`
- **Expected Diagnosis**: `NONE`
- **Expected Gate Outcome**: `PASS`
- **Expected Deployment Blocked**: `False`

---

### Category F: Storage and Persistence Faults

#### `FIB-STO-001`: Database Persistence Operation Fails
- **Severity**: `HIGH`
- **Target Component**: MongoDB Atlas Adapter
- **Preconditions**: Storage operation attempted.
- **Injection Method**: Inject connection error / write exception during `insert_one`.
- **Expected Detection**: `True`
- **Expected Diagnosis**: `STORAGE_PERSISTENCE_FAILURE`
- **Expected Gate Outcome**: `FAIL`
- **Expected Deployment Blocked**: `False`

#### `FIB-STO-002`: Persisted Record Differs from Authoritative Memory
- **Severity**: `HIGH`
- **Target Component**: Write Confirmation & Readback Integrity Verifier
- **Preconditions**: Record written to database.
- **Injection Method**: Readback record returns modified fields (e.g., metric altered during storage).
- **Expected Detection**: `True`
- **Expected Diagnosis**: `PERSISTENCE_READBACK_MISMATCH`
- **Expected Gate Outcome**: `FAIL`
- **Expected Deployment Blocked**: `False`

#### `FIB-STO-003`: Prohibited Silent Local File Fallback Chosen (Critical)
- **Severity**: `CRITICAL`
- **Target Component**: Database Fallback Policy Verifier
- **Preconditions**: Remote Atlas database unavailable.
- **Injection Method**: System silently redirects persistent metadata to unapproved local file without raising alert.
- **Expected Detection**: `True`
- **Expected Diagnosis**: `UNAUTHORIZED_STORAGE_FALLBACK`
- **Expected Gate Outcome**: `FAIL`
- **Expected Deployment Blocked**: `True`

#### `FIB-STO-004`: Unconfirmed Write Claimed as Durable Success
- **Severity**: `HIGH`
- **Target Component**: Storage Write Acknowledgment Verifier
- **Preconditions**: Asynchronous write queued.
- **Injection Method**: Return `persistence_status='CONFIRMED'` before database acknowledgment received.
- **Expected Detection**: `True`
- **Expected Diagnosis**: `UNCONFIRMED_WRITE_MISREPRESENTED`
- **Expected Gate Outcome**: `FAIL`
- **Expected Deployment Blocked**: `False`

#### `FIB-STO-005`: Atlas Write Confirmed and Validated (Clean Control)
- **Severity**: `MEDIUM`
- **Target Component**: Storage Layer & Persistence Verifier
- **Preconditions**: Atlas connection active, write acknowledged.
- **Injection Method**: None.
- **Expected Detection**: `False`
- **Expected Diagnosis**: `NONE`
- **Expected Gate Outcome**: `PASS`
- **Expected Deployment Blocked**: `False`

---

### Category G: Frontend and API Integrity Faults

#### `FIB-API-001`: API Returns Malformed JSON Response
- **Severity**: `MEDIUM`
- **Target Component**: API Gateway Response Serializer
- **Preconditions**: Client issues `GET /api/verification-benchmark/runs/{id}`.
- **Injection Method**: Truncate JSON string or inject unescaped characters.
- **Expected Detection**: `True`
- **Expected Diagnosis**: `API_MALFORMED_RESPONSE`
- **Expected Gate Outcome**: `FAIL`
- **Expected Deployment Blocked**: `False`

#### `FIB-API-002`: API Returns Error but UI Attempts to Display SUCCESS
- **Severity**: `HIGH`
- **Target Component**: Frontend Response Gate & Error State Handler
- **Preconditions**: Backend endpoint returns HTTP 500 error payload.
- **Injection Method**: Mock client component ignoring status and rendering default success state.
- **Expected Detection**: `True`
- **Expected Diagnosis**: `FRONTEND_ERROR_MASKING_ATTEMPT`
- **Expected Gate Outcome**: `FAIL`
- **Expected Deployment Blocked**: `False`

#### `FIB-API-003`: Displayed Metric Fails Backend Hash Validation
- **Severity**: `HIGH`
- **Target Component**: Cryptographic Integrity Verifier
- **Preconditions**: Backend computes `detection_rate = 94.2%` with SHA-256 fingerprint.
- **Injection Method**: Frontend alters displayed metric to `99.9%` while preserving old hash.
- **Expected Detection**: `True`
- **Expected Diagnosis**: `METRIC_TAMPERING_DETECTED`
- **Expected Gate Outcome**: `FAIL`
- **Expected Deployment Blocked**: `False`

#### `FIB-API-004`: Unauthorized User Attempts to Fetch Benchmark Report
- **Severity**: `HIGH`
- **Target Component**: API Security & Authorization Controller
- **Preconditions**: Run ID belongs to `project_omega`.
- **Injection Method**: Request presented without valid project authentication token.
- **Expected Detection**: `True`
- **Expected Diagnosis**: `UNAUTHORIZED_BENCHMARK_ACCESS`
- **Expected Gate Outcome**: `FAIL`
- **Expected Deployment Blocked**: `False`

#### `FIB-API-005`: API Contract Valid and Matching Backend (Clean Control)
- **Severity**: `LOW`
- **Target Component**: API Gateway & Frontend Contract Verifier
- **Preconditions**: Synchronized schemas between backend and frontend.
- **Injection Method**: None.
- **Expected Detection**: `False`
- **Expected Diagnosis**: `NONE`
- **Expected Gate Outcome**: `PASS`
- **Expected Deployment Blocked**: `False`

---

### Category H: Audit and Evidence Faults

#### `FIB-AUD-001`: Required Audit Event Missing
- **Severity**: `HIGH`
- **Target Component**: Audit Logging Pipeline
- **Preconditions**: Verification run produces audit events: `[RUN_STARTED, GATE_EVALUATED, RUN_COMPLETED]`.
- **Injection Method**: Omit `GATE_EVALUATED` event from audit trail.
- **Expected Detection**: `True`
- **Expected Diagnosis**: `MISSING_AUDIT_EVENT`
- **Expected Gate Outcome**: `FAIL`
- **Expected Deployment Blocked**: `False`

#### `FIB-AUD-002`: Required Scenario Evidence Missing
- **Severity**: `HIGH`
- **Target Component**: Scenario Result Evidence Binder
- **Preconditions**: Scenario result requires non-empty evidence dictionary.
- **Injection Method**: Set `evidence_references = []`.
- **Expected Detection**: `True`
- **Expected Diagnosis**: `MISSING_SCENARIO_EVIDENCE`
- **Expected Gate Outcome**: `FAIL`
- **Expected Deployment Blocked**: `False`

#### `FIB-AUD-003`: Run Identifier Mismatched in Audit Record
- **Severity**: `HIGH`
- **Target Component**: Audit Integrity Verifier
- **Preconditions**: Active run ID `fib_run_100`.
- **Injection Method**: Attach audit event labeled `fib_run_999`.
- **Expected Detection**: `True`
- **Expected Diagnosis**: `AUDIT_RUN_ID_MISMATCH`
- **Expected Gate Outcome**: `FAIL`
- **Expected Deployment Blocked**: `False`

#### `FIB-AUD-004`: Gate Decision Missing Link to Evidence Payload
- **Severity**: `HIGH`
- **Target Component**: Gate Audit Traceability Verifier
- **Preconditions**: Gate decision `FAIL`.
- **Injection Method**: Decision record lacks `evidence_link_hash`.
- **Expected Detection**: `True`
- **Expected Diagnosis**: `UNLINKED_GATE_DECISION`
- **Expected Gate Outcome**: `FAIL`
- **Expected Deployment Blocked**: `False`

#### `FIB-AUD-005`: Complete Audit Trail with Valid Hashes (Clean Control)
- **Severity**: `MEDIUM`
- **Target Component**: Audit Engine & Evidence Linker
- **Preconditions**: Full audit trail, validated hashes, correct chronological timestamps.
- **Injection Method**: None.
- **Expected Detection**: `False`
- **Expected Diagnosis**: `NONE`
- **Expected Gate Outcome**: `PASS`
- **Expected Deployment Blocked**: `False`
