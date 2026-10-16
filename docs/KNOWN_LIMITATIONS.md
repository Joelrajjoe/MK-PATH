# Known Limitations & Technical Constraints

This document honestly outlines the current technical boundaries, architectural constraints, and future expansion areas for the Executive Performance Management Dashboard.

---

## 1. Current Technical Constraints

### A. Temporal Data Requirements for Time Intelligence
- **Limitation:** Calculating Quarter-over-Quarter (QoQ) and Year-over-Year (YoY) metrics requires an identifiable date or timestamp column with parseable dates.
- **Behavior:** If a dataset lacks a temporal column or contains only a single reporting period, the engine does **NOT** invent historical dates. Instead, it displays a status note: *"Single temporal horizon detected; displaying sequential baseline"* or returns `"N/A"`.
- **Mitigation:** The engine supports `DD-MM-YYYY`, `YYYY-MM-DD`, and standard ISO timestamp string formats via DuckDB `strptime()` and `TRY_CAST()`.

### B. In-Memory View Lifecycle
- **Limitation:** DuckDB views (`ds_<dataset_id>`) reside in the process memory of the FastAPI backend.
- **Behavior:** Parquet files are stored permanently on disk in `datasets/parquet/<dataset_id>.parquet`. If the backend process restarts, views are re-registered lazily upon the first incoming analytics or drilldown query.
- **Performance Impact:** First-request cold query latency is ~10-25ms; subsequent warm queries execute in < 2ms.

### C. Multi-Year Comparisons
- **Limitation:** Year-over-Year (Card 2) requires data spanning at least two distinct years.
- **Behavior:** Datasets confined to a single calendar year (e.g., 2024 only) will display `-6%` variance relative to the mean with an explicit status note: *"1-year evaluation boundary observed; trajectory variance relative to mean"*. It will never synthesize fake prior-year data.

### D. Export Formats
- **Limitation:** Direct backend report generation currently supports CSV and JSON payloads.
- **Mitigation:** Printable PDF reports can be generated via the browser's native print preview (`Ctrl+P` / `Cmd+P`) using CSS print media styles. Server-side headless PDF generation via Weasyprint or Playwright is planned for a future release.

### E. Location Benchmark Dimensions
- **Limitation:** Card 6 (Location Performance Benchmark) requires a categorical column indicating geographic locations or cohorts (e.g. `city`, `location`, `region`).
- **Behavior:** When no geographic column is present, the engine automatically selects the secondary categorical attribute (e.g. `weather_condition`, `status`) and normalizes benchmarks against the dataset total.

---

## 2. FIB-VG Benchmark Constraints & Technical Boundaries

### A. MongoDB Atlas Cloud Connectivity
- **Constraint**: Persistent storage of benchmark runs requires an active outbound network connection to MongoDB Atlas with valid credentials configured in `MONGODB_URI`.
- **Behavior**: If Atlas is unavailable or network times out, the benchmark marks the run as `persistence_status = "UNCONFIRMED"` and preserves in-memory run telemetry. It **never** silently switches to an unapproved local database or writes unencrypted flat files on disk.

### B. Finite Scenario Horizon vs. Production Generalizability
- **Constraint**: FIB-VG evaluates 42 rigorously defined scenarios across 8 failure categories.
- **Limitation**: Passing a finite benchmark suite proves that verification gates correctly catch the 34 modeled failure modes and 8 clean controls. It does not constitute a mathematical guarantee against novel, un-modeled upstream data corruptions. Continuous expansion of the catalog is required as new failure modes emerge.

### C. Concurrency and Execution Model
- **Constraint**: Scenarios are executed sequentially in isolated execution blocks rather than parallel worker processes.
- **Rationale**: Sequential execution prevents race conditions in shared verifier state, ensures deterministic timestamps, and enforces strict memory containment on the host machine without consuming unnecessary CPU or disk bandwidth.

---

## 3. Option C Attestation & Cryptographic Provenance Boundaries

### A. Fail-Closed Network Isolation for Attestation Durability
- **Constraint**: If `require_atlas=True` is specified during envelope creation, the system requires active write confirmation to MongoDB Atlas (`attestation_envelopes` collection).
- **Behavior**: If MongoDB Atlas cloud connectivity is down or times out, the service raises `AtlasPersistenceError` and fails closed. It does **NOT** write un-audited fallback files to local disk or pretend the envelope is durably anchored in cloud storage.

### B. Ephemeral Key Lifetime in Local Development
- **Constraint**: In non-production environments with `MKPATH_DEV_SIGNING=true`, an isolated ephemeral Ed25519 keypair is dynamically generated in memory at server startup.
- **Limitation**: If the server process restarts without configuring `MKPATH_SIGNING_PRIVATE_KEY` in `.env`, a new keypair is generated. Envelopes signed during the prior process run will report `UNKNOWN_KEY` unless public keys were exported and persisted to the public trust store.

### C. Physical File Availability During Reverification
- **Constraint**: When verifying an envelope with `verify_content_files=True`, the verifier checks that source files and derived Parquet files exist at their registered paths on disk.
- **Behavior**: If files have been archived, relocated, or purged due to retention policies, the verifier flags `MISSING_CONTENT` for the missing physical assets while continuing to verify the digital signature over the envelope metadata.

