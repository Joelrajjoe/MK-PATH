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
- **MongoDB:** MongoDB Atlas cluster or local instance (MongoDB 6.0+)
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

## 12. API Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/dashboard/analytics` | Computes all 6 dashboard cards for a given `dataset_id` and `FilterContext` |
| `GET` | `/api/dashboard/filters` | Returns available filter dimensions (quarters, categories, locations) |
| `POST` | `/api/dashboard/drilldown` | Returns paginated row-level records contributing to a specific metric |
| `POST` | `/api/dashboard/verify` | Runs independent raw SQL queries and returns a 0.0-tolerance verification report |
| `POST` | `/api/dashboard/export` | Generates a verified CSV executive performance report with calculation notes |
| `POST` | `/api/stability/gate` | Runs the Plan-Multiverse Stability Gate across comparable analytical variants |

---

## 13. Testing Commands & Verified Results

### Backend Analytical & API Verification Suite
```powershell
cd backend
..\.venv\Scripts\python -m pytest tests/test_dashboard_analytics.py -v
```
**Results:** `6 passed in 4.15s`
- `test_dashboard_analytics_real_dataset`: Verified DuckDB calculations on 2,500-row real benchmark dataset.
- `test_dashboard_analytics_with_filters`: Verified cascading filter consistency and SQL predicate pushdown.
- `test_independent_sql_reconciliation`: Verified 0.0 tolerance between engine output and independent SQL.
- `test_drilldown_records`: Verified paginated row extraction and column limits.
- `test_missing_dataset_error`: Verified HTTP 404 response on missing dataset.
- `test_dashboard_router_endpoints`: Verified FastAPI endpoints via `TestClient`.

### Full Project Pytest Suite
```powershell
cd backend
..\.venv\Scripts\python -m pytest tests/test_dashboard_analytics.py tests/test_pmsg.py tests/test_semantic.py tests/test_ingestion.py tests/test_profiling.py tests/test_projects.py tests/test_remediation.py -v
```
**Results:** `77 passed in 12.8s` (Zero failures, zero mock fallbacks).

### Frontend Production Build
```powershell
cd frontend
npm run build
```
**Results:** `built in 644ms` with zero TypeScript or bundling errors.

---

## 14. Deployment Instructions

### Production Deployment Strategy
1. **Containerization:** Docker multi-stage build running Uvicorn with Gunicorn process manager (`gunicorn -w 4 -k uvicorn.workers.UvicornWorker app.main:app`).
2. **Reverse Proxy:** Nginx configured with SSL termination (Let's Encrypt), HTTP/2, and gzip compression.
3. **Frontend Static Hosting:** Built assets (`frontend/dist`) served directly via Nginx or Cloudflare Pages with cache-control headers (`max-age=31536000` for hashed assets).
4. **Volume Mounts:** Persistent SSD volume mounted at `STORAGE_PATH` for persistent Parquet datasets.

---

## 15. Security Considerations

- **No Hardcoded Secrets:** Environment secrets are strictly loaded via `.env` and excluded via `.gitignore`.
- **Zip-Bomb & Traversal Defense:** Uploaded archives are inspected in-memory with strict ratio bounds and single-depth extraction.
- **SQL Injection Prevention:** All DuckDB analytical queries use parameterized bindings or sanitized identifier escaping (`_escape_ident`).
- **Data Isolation:** Queries enforce project and dataset authorization checks before reading Parquet files.

---

## 16. Known Limitations & Future Improvements

- **Arbitrary Temporal Formats:** Unconventional custom timestamp formats may require manual column type declaration if DuckDB automatic string inference cannot parse them.
- **Multi-Million Row In-Memory Charting:** For datasets exceeding 10M rows, server-side dynamic binning and histogram aggregation are recommended over client-side point rendering.
- **Real-Time Streaming Ingestion:** Currently optimized for batch-uploaded files and micro-batches; WebSockets streaming connector is planned for future releases.

---

## License

Internal proprietary software. All rights reserved.
