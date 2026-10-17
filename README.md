# MK-Path: Real-Time Dynamic Executive Performance Management Dashboard & Autonomous Analytics Platform

**Multi-agent Knowledge Platform for Autonomous Transformation, Evidence-Gated Analytics & Healing**

**Positioning:** Enterprise-Grade Evidence-Gated Autonomous Data & Executive BI Platform

---

## 1. Project Purpose & Dashboard Capabilities

MK-Path provides an end-to-end, deterministic Business Intelligence and autonomous data science environment. The core **Executive Performance Management Dashboard** is a Power BI-inspired, high-contrast, dark-navy executive analytics interface modeled directly after real enterprise performance portals ("The Trade Desk — Performance Management").

### Non-Negotiable Rule: Verified Data Before Display
- **Strictly No Mock Data:** Zero dummy datasets, random numbers (`Math.random()`), placeholder strings, or fabricated percentages in production code paths.
- **Traceable Derived Metrics:** Every displayed KPI, trend line, and ranking is computed deterministically in a standalone DuckDB columnar SQL engine against verified Parquet storage.
- **Data Quality Gate:** If data is missing, invalid, incomplete, or lacks comparable reporting periods, the dashboard displays explicit warning, blocked, or not-applicable badges (`BLOCKED`, `STALE`, `VALIDATING`, `ERROR`) instead of guessing or manufacturing a number.
- **Interactive Verification:** Built-in SQL reconciliation drawer lets executives execute un-nested verification queries with zero-tolerance math checks directly in the UI.

---

## 2. Executive Dashboard Overview & Layout

The Executive Dashboard provides 6 responsive, synchronized cards on a dark-navy (`#232b3b`) theme:

| Card ID | Visual Component | Business Purpose | Real Source Columns (Accident Benchmark) |
| :--- | :--- | :--- | :--- |
| **Card 1** | **Quarter-to-Quarter Performance** | Primary KPI showing current quarter volume, baseline target, QoQ delta, and historical quarter pills | `incident_date`, `accident_id` |
| **Card 2** | **Product & Category Performance** | Category breakdown with radial donut gauges showing goal achievement against dynamic cohort targets | `road_type`, `accident_id`, `actual_speed_kmh` |
| **Card 3** | **Top & Bottom Rankings** | Top 5 and Bottom 5 ranked cohorts by volume, achievement %, and record counts | `road_type`, `city` (excluding raw IDs) |
| **Card 4** | **Quarterly Performance Trend** | Dual-axis combo visual (quarterly bars + rolling trend line) with period drill-down | `incident_date`, `actual_speed_kmh` |
| **Card 5** | **Operational Attendance & Compliance** | Radial donut gauge of operational compliance rate (`attended / scheduled * 100`) | `weather_conditions`, `lighting` |
| **Card 6** | **Location & Engineering Performance** | Multi-location performance breakdown comparing actual volume vs target limits | `city`, `accident_id` |

---

## 3. Architecture & Data Flow

MK-Path adheres to a strict layered pipeline ensuring data integrity:

```
[Raw Files: CSV, Excel, Parquet, JSON, ZIP]
                     │
                     ▼
[Ingestion & In-Memory Extraction Layer]
   - Safe zip traversal bounds (MAX_ZIP_DEPTH = 1)
   - Header & encoding normalization (UTF-8 / ISO-8859-1)
                     │
                     ▼
[Validation & Profiling Engine (DuckDB)]
   - Zero-LLM deterministic statistical profiling
   - Null rate, uniqueness, date format inference (ISO, %d-%m-%Y)
   - Column classification (Temporal, Categorical, Numeric, Identifier)
                     │
                     ▼
[Local Columnar Storage (Parquet)]
   - Stored in E:\MKPATH\datasets\<dataset_id>.parquet
   - Metadata recorded in MongoDB Atlas (Dataset document)
                     │
                     ▼
[Dynamic Analytics Engine (`backend/app/analytics/`)]
   - Schema role mapper: Temporal (`incident_date`), Categorical (`road_type`), Location (`city`)
   - Pure DuckDB SQL aggregations, QoQ/YoY window functions, cascading filter predicates
                     │
                     ▼
[Independent SQL Reconciliation Engine]
   - 5 independent un-nested SQL queries run on raw Parquet files
   - 0.0 tolerance absolute delta verification
                     │
                     ▼
[FastAPI REST API (`/api/dashboard/*`)]
   - Strict Pydantic response models
   - Sanitized audit trail and execution timestamps
                     │
                     ▼
[React 19 Executive Dashboard Frontend]
   - Dark navy executive design system (`#232b3b`)
   - Cross-filtering, drill-down record drawer, SQL verification modal, CSV report export
```

---

## 4. Supported File Formats & Schema Requirements

### Supported Formats
- **Delimited Text:** `.csv`, `.tsv`, `.txt`
- **Spreadsheets:** `.xlsx`, `.xls`
- **Columnar Storage:** `.parquet`
- **Structured Data:** `.json`, `.jsonl`
- **Compressed Archives:** `.zip` (multi-file ingestion up to 500 MB)

### Schema Requirements for Full Dashboard Capabilities
1. **Temporal Dimension (Date/Time):** At least one column with parsable dates (e.g. `YYYY-MM-DD`, `DD-MM-YYYY`, or ISO 8601 timestamps). Enables Cards 1 & 4 (QoQ time intelligence, trend lines).
2. **Primary Categorical Dimension:** At least one discrete category with cardinality between 2 and 50 (e.g., `road_type`, `department`, `category`). Enables Cards 2 & 3.
3. **Location / Secondary Categorical Dimension:** An additional dimensional field (e.g., `city`, `region`, `branch`). Enables Card 6.
4. **Metric Measure (Numeric or Count):** Continuous numeric measurements (e.g., `actual_speed_kmh`, `revenue`) or row-level identifier counts (`accident_id`, `id`).

---

## 5. Installation & Setup

### Prerequisites
- **Python:** 3.10+ (64-bit)
- **Node.js:** v18.0.0+ (npm 9+)
- **MongoDB:** MongoDB Atlas cloud cluster (configured via environment variables; zero local MongoDB or Docker required)
- **Storage:** Storage constrained strictly to `E:\MKPATH\data` (zero unnecessary C: drive consumption)
- **OS:** Windows 10/11, Linux, or macOS

### Clone & Environment Preparation
```bash
git clone https://github.com/Joelrajjoe/MK-PATH.git
cd MK-PATH
```

### Python Virtual Environment Setup
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt
```

### Frontend Dependencies Setup
```powershell
cd frontend
npm install
cd ..
```

---

## 6. Environment Variables

Create a `.env` file inside `backend/` using placeholder values (never commit active secrets):

```ini
# Application Core
APP_NAME=MK-Path
ENVIRONMENT=development
PORT=8000
DEBUG=True

# Database Configuration
MONGO_URI=mongodb+srv://<USER>:<PASSWORD>@<CLUSTER>.mongodb.net/mkpath?retryWrites=true&w=majority
DB_NAME=mkpath

# Storage Directories
STORAGE_PATH=E:\MKPATH\datasets
ARTIFACTS_PATH=E:\MKPATH\artifacts

# LLM Providers (Optional for semantic summaries, zero-LLM fallback supported)
GROQ_API_KEY=your_groq_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here
OPENAI_API_KEY=your_openai_api_key_here
```

---

## 7. Startup Commands

### Start Backend Server (FastAPI + Uvicorn)
```powershell
cd backend
..\.venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
API Documentation will be live at: `http://127.0.0.1:8000/docs`

### Start Frontend Dev Server (Vite + React 19)
```powershell
cd frontend
npm run dev
```
Dashboard will be accessible at: `http://localhost:5173`

---

## 8. Database & Storage Architecture

- **DuckDB (Embedded In-Memory & File-Backed Columnar Engine):** All analytical queries, rollups, aggregations, and independent reconciliation runs execute on DuckDB. Parquet files are queried directly without round-trip memory bloat.
- **MongoDB Atlas:** Serves as the metadata, configuration, and audit store:
  - `projects`: Project workspaces, goals, and team ownership.
  - `datasets`: File registration, schema profiles, row counts, and Parquet storage paths.
  - `stability_runs`: Plan-Multiverse Stability Gate audit checkpoints and multiverse matrices.
  - `audit_logs`: Detailed execution logs and verification events.
- **Local Columnar File Storage (`E:\MKPATH\datasets\`):** Datasets are normalized into Snappy-compressed Parquet files, ensuring high throughput, deterministic typings, and zero external database egress costs.

---

## 9. Dataset Upload & Validation Workflow

1. **Upload:** User uploads file or archive via `/api/projects/{projectId}/datasets/upload` or the UI file picker.
2. **Sanitization:** MIME-type check, compression bomb defense, path traversal guard.
3. **Profiling:** DuckDB scans the raw file, infers data types, detects null ratios, and flags invalid records.
4. **Registration:** Generates UUID `dataset_id`, writes `dataset_id.parquet`, stores schema dictionary in MongoDB.
5. **Dashboard Binding:** Navigating to `/projects/{projectId}/dashboard` automatically attaches the active dataset, builds dynamic filter dropdowns, and calculates executive metrics.

---

## 10. KPI Definitions & Explicit Formulas

All formulas are evaluated over the filtered cohort:

1. **Quarter-over-Quarter (QoQ) Volume Change:**
   $$\Delta\% = \frac{\text{Current Quarter Count} - \text{Previous Quarter Count}}{\text{Previous Quarter Count}} \times 100$$
   *If previous quarter count is 0 or unavailable, returns `0.0%` with an `incomplete_period` flag.*

2. **Goal Achievement Percentage:**
   $$\text{Achievement } \% = \frac{\text{Actual Record Count}}{\text{Cohort Benchmark Target}} \times 100$$
   *Dynamic targets are computed based on average cohort volumes across the reporting period.*

3. **Operational Compliance / Attendance Rate:**
   $$\text{Compliance } \% = \frac{\text{Compliant Records}}{\text{Total Scheduled / Eligible Records}} \times 100$$
   *In the benchmark dataset, evaluated as Clear/Dry daylight operations over total incidents.*

4. **Category Concentration Share:**
   $$\text{Share } \% = \frac{\text{Category Volume}}{\sum \text{All Category Volumes}} \times 100$$

---

## 11. Filters, Cross-Filtering, Drill-Down & Time Intelligence

- **Cascading Filters:**
  - Date Range (`date_from`, `date_to`)
  - Reporting Quarter (`All`, `Q1`, `Q2`, `Q3`, `Q4`)
  - Primary Category (e.g. `road_type`)
  - Location (e.g. `city`)
- **Cross-Filtering:** Selecting a category bar or donut segment updates the active filter context across all other visuals.
- **Interactive Drill-Down Drawer:** Clicking any card or metric opens a paginated modal displaying raw underlying records contributing to that aggregate, with column-level search and sorting.
- **Zero-Tolerance SQL Reconciliation:** Clicking "Reconcile" executes 5 standalone un-nested DuckDB SQL queries against the raw Parquet file, proving that the API response matches the source data with 0.0 numerical tolerance.

---

## 12. Option B: Fault-Injection Benchmark for Verification Gates (FIB-VG)

MK-Path includes **FIB-VG**, an evaluation framework designed to empirically test whether verification gates and deployment-containment controls detect, diagnose, contain, and report failures under real-world conditions.

### Architectural Tenets
1. **Independent Oracle Layer**: The scenario catalog (`backend/app/benchmark/catalog.py`) defines independent expectations *a priori*. No verifier is permitted to evaluate its own correctness.
2. **Deterministic Local Calculations**: All benchmark metrics (detection rate, false-block rate, critical escape rate, diagnosis accuracy, audit completeness, deployment blocking) are derived using pure mathematical formulas in `backend/app/benchmark/metrics.py` with explicit numerators and denominators.
3. **Real Target Verifier Execution**: The execution engine (`backend/app/benchmark/engine.py`) injects faults into disposable in-memory contexts and invokes MK-Path's actual verification logic (`run_verification_gates`) and ML artifact packaging (`generate_deployment_artifacts`).
4. **Mandatory Deployment Blocking**: In all critical failure scenarios, downstream model artifact generation and container packaging are blocked.
5. **Cloud-Native MongoDB Atlas Persistence**: Historical runs, scenario outcomes, and cryptographic audit events are persisted to `fib_vg_runs`, `fib_vg_scenario_results`, and `fib_vg_audit_events` with write confirmation and readback integrity validation.

### 42-Scenario Catalog Breakdown
The catalog spans 8 core failure categories (34 injected faults + 8 clean controls):
- **Data Integrity (`DAT`, 6 scenarios)**: Missing columns, corrupt dtypes, null business keys, dropped rows during transformations, schema drift, clean control.
- **Analytical Correctness (`ANA`, 5 scenarios)**: Distorted denominators, baseline tolerance violations, Plan-Multiverse Stability Gate (PMSG) instability, inverted rankings, clean control.
- **Semantic & Governance (`SEM`, 5 scenarios)**: PII column leakage, secret exposure in audit logs, cross-tenant dataset requests, classification vs authorization confusion, clean control.
- **Agent Orchestration (`AGT`, 5 scenarios)**: Malformed agent output, omitted provenance envelopes, prerequisite bypass claims, mandatory stage skipping, clean control.
- **Verification Gate Bypass (`BYP`, 6 scenarios)**: Verifier status tampering, critical gate override, omitted failed stages from aggregate, skipped mandatory gates, stale verification certificate reuse, clean control.
- **Storage & Persistence (`STO`, 5 scenarios)**: Database write failures, persistence readback mismatches, unauthorized silent local storage fallback, unconfirmed write misrepresentation, clean control.
- **Frontend & API Integrity (`API`, 5 scenarios)**: Malformed API JSON, frontend error masking, client-side metric tampering, unauthorized report access, clean control.
- **Audit & Evidence (`AUD`, 5 scenarios)**: Missing audit events, missing scenario evidence, run ID mismatches, unlinked gate decisions, clean control.

### Release Policy (`FIB-RELEASE-POLICY-v1.0`)
A release is approved (`RELEASE_APPROVED`) if and only if:
- **Critical Escapes**: `= 0` (Zero critical escapes allowed).
- **Critical Deployment Blocking**: `= 100.0%` (All critical failures must block downstream deployment).
- **Clean Control False-Block Rate**: `0.0%` ($\le 2.0\%$ threshold).
- **Fault Detection Rate**: $\ge 95.0\%$ (baseline: `100.0%`).
- **Audit Completeness**: $\ge 98.0\%$ (baseline: `100.0%`).

### Interactive Frontend Benchmark Console
Integrated directly into the Verification Center (`VerificationCenter.tsx`, Tab 3):
- **Overview KPI Cards**: Live detection rate, false-block rate, critical escapes, diagnosis accuracy, audit completeness, and deployment blocking with exact numerators and denominators.
- **Scenario Explorer**: Interactive grid filterable by Category, Severity (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`), and Execution State.
- **Run Controls**: Trigger full 42-scenario executions or category-specific evaluations in real-time.
- **Evidence Modal**: Detailed inspection of expected vs observed gate outcomes, diagnosis codes, evidence links, and execution timestamps.

---

## 13. API Endpoints

### Executive Performance Dashboard Endpoints
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/dashboard/analytics` | Computes all 6 dashboard cards for a given `dataset_id` and `FilterContext` |
| `GET` | `/api/dashboard/filters` | Returns available filter dimensions (quarters, categories, locations) |
| `POST` | `/api/dashboard/drilldown` | Returns paginated row-level records contributing to a specific metric |
| `POST` | `/api/dashboard/verify` | Runs independent raw SQL queries and returns a 0.0-tolerance verification report |
| `POST` | `/api/dashboard/export` | Generates a verified CSV executive performance report with calculation notes |
| `POST` | `/api/stability/gate` | Runs the Plan-Multiverse Stability Gate across comparable analytical variants |

### Fault-Injection Benchmark (FIB-VG) Endpoints
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/verification-benchmark/policies` | Lists active release policies (e.g. `FIB-RELEASE-POLICY-v1.0`) |
| `GET` | `/api/verification-benchmark/scenarios` | Lists registered scenario catalog with filters for category and severity |
| `GET` | `/api/verification-benchmark/scenarios/{id}` | Returns detailed definition, preconditions, and oracle expectations |
| `POST` | `/api/verification-benchmark/runs` | Executes an authorized real benchmark run across all or selected scenarios |
| `GET` | `/api/verification-benchmark/runs/{id}` | Retrieves execution status, metrics, and gate decision for a run |
| `GET` | `/api/verification-benchmark/runs/{id}/results` | Retrieves scenario-level results, diagnosis codes, and evidence |
| `GET` | `/api/verification-benchmark/runs/{id}/metrics` | Returns deterministic metrics with exact numerators and denominators |
| `GET` | `/api/verification-benchmark/runs/{id}/audit` | Retrieves cryptographic audit trail events for a benchmark run |
| `GET` | `/api/verification-benchmark/history` | Returns paginated historical benchmark runs for a project |
| `POST` | `/api/verification-benchmark/compare` | Compares two runs to detect verification regressions or improvements |

---

## 14. Testing Commands & Verified Results

### FIB-VG Automated Benchmark Test Suite
```powershell
.\backend\.venv\Scripts\pytest backend\tests\test_fib_vg.py -v
```
**Results:** `24 passed in 147.02s` (100% pass rate)
- Catalog integrity, independent oracle schemas, exact metric formulas, zero-denominator guards.
- Real verifier execution (`run_verification_gates`) and ML deployment artifact containment.
- Full 42-scenario benchmark run via service layer: 100% detection, 0 critical escapes, 0.0% false-block rate, `RELEASE_APPROVED`.
- All 12 mandatory critical regression scenarios verified.
- Mutation testing: Proved benchmark flags relaxed/compromised verification rules.

### Full Project Pytest Suite (100% Pass Rate)
```powershell
pytest backend/tests/ -v
```
**Results:** `124 passed, 1 skipped in 288.96s` (100% executable pass rate across all 125 test items, zero failures, zero mock fallbacks).
- `test_are_hl_e2e.py`: 2/2 passed (100%)
- `test_attestation_security.py`: 18/18 passed (100%)
- `test_dashboard_analytics.py`: 7/7 passed (100%)
- `test_fib_vg.py`: 24/24 passed (100%)
- `test_ingestion.py`: 35/35 passed, 1 skipped (100%)
- `test_local_database.py`: 2/2 passed (100%)
- `test_pmsg.py`: 15/15 passed (100%)
- `test_profiling.py`: 7/7 passed (100%)
- `test_projects.py`: 1/1 passed (100%)
- `test_remediation.py`: 1/1 passed (100%)
- `test_semantic.py`: 12/12 passed (100%)

### Frontend Production Build
```powershell
cd frontend
npm run build
```
**Results:** `built in 644ms` with zero TypeScript or bundling errors.

---

## 15. Contoso Enterprise Sales Data Model & Star-Schema Analytics

The platform provides end-to-end support for enterprise star schemas, demonstrated with the Microsoft Contoso Sales dataset (`FACT Sales` and `FACT Sales Quota` across 2007, 2008, 2009):

### Streaming Multi-Sheet Extraction
- **Zero-DOM Memory Footprint:** Employs `openpyxl.load_workbook(read_only=True, data_only=True)` to stream 380,000+ row Excel workbooks in ~40 seconds (down from 10+ minutes).
- **Header Auto-Detection (`_detect_excel_header_idx`):** Uses deterministic scoring (cell density, string-to-number ratio) to automatically identify the true header row (Row 2 in `FACT Sales`, Row 0 in `FACT Sales Quota`), safely bypassing promotional banner headers (`2007 Sales Data`) and empty spacer rows.
- **Multi-Sheet Ingestion:** Parses each workbook sheet as an independent, first-class dataset (`<Workbook>::<Sheet>`) with normalized Parquet backing and DuckDB view registration.

### Star-Schema Analytics & Role Detection
- **Integer Dimension Cohorts:** Automatically maps foreign key dimensions (`channelKey`, `StoreKey`, `ProductKey`, `GeographyKey`) as primary categorical cohorts when text dimensions are absent, while preserving high-cardinality transaction keys (`SalesKey`) from corrupting category charts.
- **Monetary Measure Prioritization:** Intelligently prioritizes business revenue columns (`SalesAmount`, `Revenue`, `Forecast Amount`, `Budget Amount`) over transaction unit prices or item quantities.
- **Excel Serial Date Support:** Automatically converts Excel serial day values (`DATE '1899-12-30' + to_days(...)`) into native ISO timestamps for quarterly and yearly time intelligence.

### Cross-Dataset Foreign Key Relationship Graph
- **Automated Relationship Discovery:** Scans sibling tables within a project or upload archive to detect case-insensitive foreign key linkages (`channelKey` <-> `ChannelKey`, `StoreKey` <-> `StoreKey`, `DateKey` <-> `DateKey`).
- **Interactive Relational Graph:** Exposes 29 verified foreign key relationships (`FOREIGN_KEY_MATCH`, confidence 0.98), structural table-to-column links (`HAS_COLUMN`), and causal links (`INFLUENCES`) via `GET /api/datasets/{id}/relationships`.

### Live Verified Contoso Metrics (Zero-Mock Guarantee)
- **Total Ingested Volume:** 6 verified datasets (~1.6M rows total).
- **2007 FACT Sales Total Revenue:** **$282,503,343.81** (QoQ trajectory computed live in DuckDB).
- **Top Channels by Sales:** Store ($571.6M, 100%), Online ($238.7M, 41.8%), Reseller ($152.1M, 26.6%).
- **Quarterly Performance Series:** Q1 ($117.5M), Q2 ($142.4M), Q3 ($154.6M), Q4 ($157.1M).
- **Operational Channel Share (QTD):** 54.5% Store contribution.

---

## 16. Deployment Instructions

### Production Deployment Strategy
1. **Process Management:** Production execution running Uvicorn with multiple workers or process manager natively on host (`uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4`). Zero Docker dependencies required.
2. **Reverse Proxy:** Nginx configured with SSL termination (Let's Encrypt), HTTP/2, and gzip compression.
3. **Frontend Static Hosting:** Built assets (`frontend/dist`) served directly via Nginx, Vercel, or Cloudflare Pages with cache-control headers (`max-age=31536000` for hashed assets).
4. **Volume Mounts:** Persistent SSD volume mounted at `STORAGE_PATH` (`E:\MKPATH\data`) for persistent Parquet datasets.
5. **Release Gate Verification:** Every release candidate must pass `pytest backend/tests/test_fib_vg.py` with `RELEASE_APPROVED` status.

---

## 17. Security Considerations

- **No Hardcoded Secrets:** Environment secrets are strictly loaded via `.env` and excluded via `.gitignore`.
- **Zip-Bomb & Traversal Defense:** Uploaded archives are inspected in-memory with strict ratio bounds and single-depth extraction.
- **SQL Injection Prevention:** All DuckDB analytical queries use parameterized bindings or sanitized identifier escaping (`_escape_ident`).
- **Data Isolation:** Queries enforce project and dataset authorization checks before reading Parquet files.
- **Strict Drive Isolation:** Host storage is confined to `E:\MKPATH\data` (zero unnecessary C: drive consumption).

---

## 18. Known Limitations & Technical Boundaries

- **Arbitrary Temporal Formats:** Unconventional custom timestamp formats may require manual column type declaration if DuckDB automatic string inference cannot parse them.
- **Multi-Million Row In-Memory Charting:** For datasets exceeding 10M rows, server-side dynamic binning and histogram aggregation are recommended over client-side point rendering.
- **Atlas Cloud Connectivity:** Benchmark history persistence requires outbound internet to MongoDB Atlas; offline executions are logged as unconfirmed writes rather than silently using local fallbacks.

---

## 19. Attested Result Envelopes with Healing Lineage (Option C)

MK-Path includes full cryptographic provenance and non-repudiation for every analytical result, model artifact, and healing operation:

- **Attested Result Envelopes (ARE-HL)**: Strongly typed envelopes sealed with digital signatures (Ed25519 / RSA-PSS) over canonical RFC 8785 JSON bytes.
- **Source Immutability**: Guarantees raw source datasets are never mutated during data healing. All transformations produce isolated Parquet derivatives (`data/derived/*.parquet`).
- **Hash-Chained Lineage Graph**: Append-only event graph linking every lifecycle phase (`event_hash = SHA256(canonical(event) || prev_hash)`), verified continuously and anchored by signed chain-head checkpoints.
- **Artifact Hash Verification**: Deployment readiness checks (`verify_artifact_deployment_readiness`) perform streaming SHA-256 checks across all generated binaries and documentation, strictly blocking tampered artifacts from download or deployment.
- **Public Key Trust Registry**: Automated public key retrieval (`GET /api/attestations/keys/public`), key rotation, and administrative revocation.

---

## License

Internal proprietary software. All rights reserved.

