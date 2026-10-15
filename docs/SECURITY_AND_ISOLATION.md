# Security & Isolation Guarantees
## Safety Boundaries, Storage Constraints, and Execution Isolation in FIB-VG

This document defines the security architecture, resource boundaries, and isolation guarantees enforced by the Fault-Injection Benchmark for Verification Gates (FIB-VG) in MK-Path.

---

## 1. Storage & Drive Constraints

- **Strict E: Drive Confinement**:
  - All dataset ingestion, DuckDB temporary views, Parquet columnar files, scenario execution logs, and benchmark artifacts are strictly confined to `E:\MKPATH\data` and `E:\MKPATH\artifacts`.
  - **Zero C: Drive Impact**: No temporary files, Docker container volumes, or dependency caches are written to `C:\`. This ensures compliance with the host machine's drive configuration.
- **In-Memory Disposal**:
  - Fault scenarios that mutate DataFrames execute entirely in ephemeral memory (`pd.DataFrame.copy()`). Once evaluated, references are dereferenced for garbage collection. Original datasets on disk are never altered.

---

## 2. Database Architecture & Atlas Isolation

- **MongoDB Atlas Cloud Database Only**:
  - Persistent benchmark metadata is committed exclusively to MongoDB Atlas via `MONGODB_URI` / `MONGO_URI`.
  - **Zero Local MongoDB**: No local `mongod` service, background daemon, or Windows service is installed or started.
  - **Zero Docker Requirement**: The entire benchmark executes natively in Python 3.10 and Node.js without requiring Docker or container engines.
- **Degraded Environment Honesty**:
  - In environments without active Atlas internet connectivity, benchmark records are flagged as `persistence_status = "UNCONFIRMED"`. The system **never** silently switches to an unapproved local SQLite or flat-file fallback and never disguises an unconfirmed write as durable cloud storage.

---

## 3. Fault-Injection Execution Boundary

- **Production Immutability Guarantee**:
  - Fault injection is strictly prohibited from mutating live production tables, active user sessions, or original project files.
  - Every scenario operates against isolated synthetic copies created on-the-fly.
- **Registered Catalog Restriction**:
  - Only scenarios formally defined in `backend/app/benchmark/catalog.py` can be executed.
  - The API router rejects arbitrary mutation payloads, un-registered scenario IDs, and user-supplied scripts with `HTTP 404 / 400`.
- **Synthetic Data Safety**:
  - All fault payloads use generated synthetic identifiers (`INC-SYNTH-001`, `mock_user_123`).
  - No real user credentials, actual SSNs, or live API keys are ever stored or injected into test payloads.

---

## 4. Tenant and Workspace Isolation

- **Cross-Tenant Protection**:
  - Scenario `FIB-SEM-003` verifies that when an entity belonging to `proj_alpha` attempts to access data tagged with `proj_beta_foreign_tenant`, the request is rejected with `HTTP 403 Forbidden` and logged as a security violation.
- **Credential Masking in Audit Logs**:
  - Scenario `FIB-SEM-002` verifies that evidence envelopes strip or mask sensitive tokens before storing audit events in Atlas.

---

## 5. Non-Authoritative LLM Guardrail

- **Deterministic Oracle Supremacy**:
  - While LLMs may be invoked to provide qualitative summaries or user explanations, **all benchmark metrics, gate evaluations, and release decisions are computed via deterministic Python logic**.
  - No LLM prompt response can override a failed verification gate, alter a detection score, or promote a release status.
