# Changelog: MK-Path Analytics Platform

All notable changes to the Executive Performance Management Dashboard and analytics engine are documented here.

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
