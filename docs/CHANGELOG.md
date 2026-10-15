# Changelog: MK-Path Analytics Platform

All notable changes to the Executive Performance Management Dashboard and analytics engine are documented here.

---

## [2.4.0] - 2026-10-15

### Added
- **Fault-Injection Benchmark for Verification Gates (FIB-VG) Option B Implementation:**
  - Implemented real-time evaluation framework assessing whether MK-Path verification gates correctly detect, diagnose, contain, and report injected failures.
  - **42-Scenario Catalog (`catalog.py`):** 34 controlled fault mutations across 8 categories (Data Integrity, Analytical Correctness, Semantic Governance, Agent Orchestration, Verification Gate Bypass, Storage Persistence, API/Frontend Integrity, Audit Evidence) plus 8 clean controls.
  - **Independent Test Oracles:** Defined immutable a priori expected outcomes completely independent of target verifiers.
  - **Deterministic Metrics Engine (`metrics.py`):** Pure local mathematical formulas reporting exact numerators and denominators for Detection Rate (100.0%, 34/34), Clean False-Block Rate (0.0%, 0/8), Critical Escape Rate (0.0%, 0/12), Diagnosis Accuracy (100.0%, 34/34), and Audit Completeness (100.0%, 42/42).
  - **Release Policy Gate (`policy.py`):** Versioned `FIB-RELEASE-POLICY-v1.0` enforcing zero critical escapes, 100% deployment blocking, and mandatory coverage prior to release approval.
  - **MongoDB Atlas Integration (`service.py` & `database.py`):** Persisting runs, scenario results, and audit events to `fib_vg_runs`, `fib_vg_scenario_results`, and `fib_vg_audit_events` with write confirmation and readback verification.
  - **FastAPI Benchmark Endpoints (`routers/benchmark.py`):** 10 endpoints mounted at `/api/verification-benchmark/*` for policy retrieval, scenario inspection, run execution, metrics extraction, audit trails, run history, and cross-run comparison.
  - **Frontend Benchmark Console (`FaultInjectionBenchmarkConsole.tsx`):** Interactive console integrated into `VerificationCenter.tsx` with overview KPI cards, scenario explorer with category/severity filters, progress bars, real execution triggers, and modal evidence inspection.
  - **Comprehensive Automated Test Suite (`tests/test_fib_vg.py`):** 24 test cases covering catalog integrity, exact metric math, zero denominators, real verifier execution, ML deployment artifact blocking, all 12 mandatory critical regression scenarios, and mutation testing.

---

## [2.3.0] - 2026-10-14


### Added
- **Universal Schema-Adaptive Dynamic Dashboard Titles & Metrics (`engine.py` & `models.py`):**
  - Replaced all legacy static labels ("ALL TEAMS - QUARTER-TO-QUARTER", "TYPE - YEAR-OVER-YEAR", "MEETINGS ATTENDED BY TYPE", "Attended", "On target") with 100% schema-driven dynamic titles and metrics.
  - Card 1: Dynamic dimension and temporal change (`{dim} - Quarter-to-Quarter`).
  - Card 2: Primary categorical velocity comparison (`{dim} Velocity - Year-over-Year`).
  - Card 3: Real categorical ranking (`Top and bottom 3 {cat}s - Volume Share (YTD)`).
  - Card 4: Granular interval breakdown (`Quarterly volume - {tab}`).
  - Card 5: Dynamic concentration / share (`{tab} Share of {primary_cat} (QTD)`) with center label `"Share"`, real proportions and exact sample counts.
  - Card 6: Secondary attribute benchmark (`{cat} Concentration (QTD)`) with top 5 categories sorted by frequency.
- **Dynamic Run Selector & Gate Ingestion in Verification Center (`VerificationCenter.tsx`):**
  - Eliminated hardcoded `run_1` state. Dynamically polls completed agent execution runs from `api.runs.list` and central verification gates from `/api/verification/gates`.
  - Added run selection dropdown, execution status badges, timestamp tracking, and active dataset quality score.
  - Linked Plan-Multiverse Stability Gate (PMSG) component directly to the active uploaded dataset.
- **Unclipped Multi-Page Executive PDF Export (`frontend/src/index.css` & `ExecutivePerformanceDashboard.tsx`):**
  - Overhauled `@media print` rules, eliminating single-page layout clipping caused by `h-screen`, `overflow-hidden`, and absolute positioning.
  - Enabled multi-page continuous flow (`height: auto !important; overflow: visible !important; position: static !important;`) while preserving color fidelity (`-webkit-print-color-adjust: exact !important`).
  - Added `print-hide` utility class to suppress search bars, actions, filters, and notification buttons during print/PDF generation.

### Fixed
- **Agent Execution Center MongoDB BSON Serialization (`runs.py` & `graph.py`):**
  - Resolved `InvalidDocument: Cannot encode object: AnalysisPlan(...) of type <class 'app.analysis.analyst.AnalysisPlan'>` by serializing Pydantic models, datetime objects, and numpy values into BSON-safe primitives prior to collection insertion.
  - Full LangGraph pipeline (`node_analysis_planning` -> `node_verification` -> `node_audit`) now executes and persists seamlessly to MongoDB Atlas.
- **Automated Post-Upload EDA & Preprocessing:**
  - Guaranteed automated transition from dataset ingestion to asynchronous DuckDB profiling and semantic discovery, immediately generating schema metadata, distribution statistics, and quality reports upon file upload.
- **Card 6 DuckDB Ordering & NameError Resolution:**
  - Replaced random distinct sampling in Card 6 with `GROUP BY ... ORDER BY COUNT(*) DESC LIMIT 5` to surface statistically meaningful categories.
  - Added missing `json` standard library import in `engine.py`.

---

## [2.2.0] - 2026-10-14

### Added
- **Automated Post-Upload Exploratory Data Analysis & Profiling:**
  - Automated transition to quality profiling upon dataset upload in `DataUpload.tsx` with animated pulse indicators and real-time EDA feedback.
- **Executive Dashboard PDF Export:**
  - Added dedicated "Export PDF" action button in `ExecutivePerformanceDashboard.tsx` with custom `@media print` rules optimizing the multi-card layout for landscape executive reports while hiding action controls and search bars.
- **Dynamic Dataset Discovery for E2E KPI Verification:**
  - Enhanced `_e2e_validation/e2e-20261007-064600/recompute_kpis.py` to dynamically locate source files and Parquet tables, validating exact numerical equality down to 6 decimal places across Sales, Quantity, Profit, and Discount.

### Fixed
- **Windows DuckDB Parquet File Lock Resolution:**
  - Fixed Windows `[WinError 32]` Permission Denied during live row appending/updates by cycling DuckDB view registration (`unregister` before `to_parquet()`, then `ensure_view`).
  - Added numeric coercion handling empty string values (`""` -> `None`).
- **ZIP Extraction Metadata Filtering:**
  - Ignored AppleDouble metadata (`._*`), macOS `__MACOSX`, `.DS_Store`, and OS artifacts during ZIP archive discovery in `backend/app/ingestion/service.py`.
- **Data Preview & Live Editor Contrast & Legibility:**
  - Restyled table cells and headers with high contrast in dark and light modes (`font-mono text-slate-900 dark:text-slate-100 font-medium`).
  - Overhauled "Add New Record" and "Edit Record" modal dialogues with high-contrast text, bold uppercase field labels, custom scrollbars, and styled inputs.
- **Dashboard Date Introspection & Analytics Null Safety:**
  - Added `%m/%d/%Y`, `%d/%m/%Y`, and `%Y/%m/%d` slash date parsing to DuckDB time intelligence expression compiler, successfully resolving Superstore 2014-2017 quarterly buckets.
  - Implemented `_safe_float` null guards across all 6 card computation pipelines to prevent `TypeError: float() argument must be a string or a real number, not 'NoneType'`.
  - Added cardinality-aware categorical role detection, preventing 1-value columns from displacing rich analytical dimensions.
- **Removed Static / Mock Notifications:**
  - Made dashboard header notifications 100% dynamic based on active dataset metadata, record count, and DuckDB registration status.

---

## [2.1.0] - 2026-10-14

### Added
- **Power BI-Style Analytics Engine (`backend/app/analytics/engine.py`):**
  - Schema introspection engine with automated detection of temporal fields, categorical dimensions, location attributes, and target outcomes.
  - Pure DuckDB SQL aggregations over Apache Parquet facts with zero mock metrics.
  - Quarterly and monthly time intelligence with date format parsing (`DD-MM-YYYY` and ISO formats).
  - Quarter-over-Quarter (QoQ) and Year-over-Year (YoY) trajectory deltas with sparkline series.
  - Dynamic cascading filter compiler supporting Year, Quarter, Team/Category, Location, and text query.
- **Independent SQL Reconciliation Engine (`backend/app/analytics/reconciliation.py`):**
  - Standalone un-nested SQL assertions executed directly against DuckDB.
  - Validates total row counts, filtered record counts, dimension group sums, within-category event rates, and location benchmarks against a **0.0 tolerance** (exact match).
- **Executive Dashboard API Router (`backend/app/routers/dashboard.py`):**
  - `POST /api/dashboard/analytics`: Full dashboard metrics computation.
  - `GET /api/dashboard/filters`: Dynamic cascading filter dimensions.
  - `POST /api/dashboard/drilldown`: Underlying record pagination and filtering.
  - `POST /api/dashboard/verify`: Independent SQL assertions execution.
  - `POST /api/dashboard/export`: Verified CSV and JSON export generation.
- **Frontend Dashboard Transformation (`ExecutivePerformanceDashboard.tsx`):**
  - Dark executive theme matching visual reference (`#232b3b` header and sidebar).
  - High-contrast KPI cards, SVG sparklines, progress bars, combo bar-line chart, and radial donut gauges.
  - Independent SQL Verification Drawer with live assertion tables.
  - Underlying record drilldown modal with pagination.
  - Executive Reports view with report pinning and direct export.
- **Comprehensive Test Suite (`backend/tests/test_dashboard_analytics.py`):**
  - 6 unit and integration test cases covering real data computation, filters, reconciliation, drilldown, missing datasets, and API endpoints.

### Changed
- Replaced client-side `useMemo` preview calculations with server-side DuckDB engine, resolving data truncation on datasets exceeding 100 rows.
- Enhanced `ProjectWorkspace.tsx` with dedicated "Executive Dashboard" tab (`/projects/:projectId/dashboard`).
- Connected notification bell to real platform synchronization and audit events.
- Updated API client in `frontend/src/lib/api.ts` with `api.dashboard` service.

### Fixed
- Fixed Decimal/Float arithmetic type conflicts in DuckDB aggregations.
- Fixed primary category introspection to exclude identifier columns (`*_id`).
- Fixed date format parsing binder errors on string dates.
