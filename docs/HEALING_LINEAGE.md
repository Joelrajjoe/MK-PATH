# MK-PATH Option C — Healing Lineage & Tamper-Evident Graph Specification

## 1. Principles of Non-Destructive Data Healing

In automated data platforms, data cleaning routines frequently overwrite or mutate source tables and files, destroying auditability and making downstream results untraceable.

MK-Path Option C enforces the **Immutability Invariant**:
> **Source datasets are immutable.** Under no circumstances may a healing operation overwrite, delete, truncate, or alter the original dataset file on disk or in cloud storage.

When healing is executed (`backend/app/healing/engine.py`):
1. **Pre-Flight Immutability Fingerprint**: The streaming SHA-256 hash of the parent raw file is computed before any transformation.
2. **Derivative Isolation**: Cleaned or imputed data is saved to a distinct derivative storage directory:
   `E:/MKPATH/data/derived/{derived_dataset_id}.parquet`.
3. **Parquet Semantic Preservation**: Cleaned data is stored in Apache Parquet format to retain strict schema types (dates, integers, floats, categories).
4. **Post-Flight Immutability Assertion**: The engine re-reads and re-hashes the parent dataset file from disk and asserts byte equality (`parent_sha256_after == parent_sha256_before`). If any mutation is detected, the operation aborts and raises `SourceImmutabilityViolationError`.
5. **Quality Delta Evidence**: Before-and-after missing value counts, outlier counts, and distribution metrics are calculated and bound into the `HealingOperationRecord`.

---

## 2. Hash-Chained Lineage Graph

To make the execution history verifiable without relying on trust in database state, MK-Path implements an append-only, tamper-evident hash chain (`backend/app/attestation/lineage.py`).

### 2.1 Chaining Formula

Each event in the lineage chain binds to the previous event:

$$\text{event\_hash}_i = \text{SHA256}(\text{canonical\_bytes}(\text{event}_i \setminus \{\text{event\_hash}\}) \parallel \text{previous\_event\_hash}_{i})$$

For the genesis event ($i=1$):
$$\text{previous\_event\_hash}_1 = \text{"0"} \times 64$$

### 2.2 Event Structure

```json
{
  "event_id": "evt_73a9f029b48c",
  "project_id": "proj-cardio-01",
  "run_id": "run-cardio-001",
  "sequence_number": 2,
  "event_type": "HEALING_EXECUTION",
  "previous_event_hash": "a82f...b3c1",
  "input_artifacts": [
    {"id": "ds-patients-001", "hash": "e3b0c442...b855"}
  ],
  "output_artifacts": [
    {"id": "patients_v1_healed", "hash": "5d41402a...450a"}
  ],
  "actor": "mkpath.healing_engine",
  "details": {
    "rules_applied": ["median_impute_age"],
    "parent_dataset_sha256": "e3b0c442...b855",
    "derived_dataset_sha256": "5d41402a...450a"
  },
  "timestamp": "2026-10-16T15:44:30.123456Z",
  "event_hash": "9c12e8b...01fe"
}
```

### 2.3 Cryptographic Chain Integrity Verification

The chain verification algorithm (`LineageTracker.verify_chain`) validates:
1. **Sequence Continuity**: Every event $i > 1$ must have $\text{seq}_i == \text{seq}_{i-1} + 1$.
2. **Pointer Continuity**: $\text{previous\_event\_hash}_i == \text{event\_hash}_{i-1}$.
3. **Payload Integrity**: Recomputing $\text{compute\_event\_hash}(\text{event}_i)$ must produce an exact match with the stored $\text{event\_hash}_i$.
4. **Anti-Cycling**: Genesis pointer must strictly reference the 64-character zero string, preventing cycles.

Any payload modification or out-of-order insertion breaks the cryptographic link and is immediately flagged as `LINEAGE_BROKEN`.

---

## 3. Signed Chain-Head Checkpoints

To anchor the state of a lineage graph and allow external audit without traversing the full event log, MK-Path supports signing chain-head checkpoints (`POST /api/attestations/lineage/runs/{run_id}/checkpoint`):
- Anchors the highest sequence number and final event hash.
- Bound by an active Ed25519 digital signature.
- Checkpoints are persisted in MongoDB Atlas (`lineage_checkpoints` collection).
