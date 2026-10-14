# Changelog: MK-Path Analytics Platform

All notable changes to the Executive Performance Management Dashboard and analytics engine are documented here.

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
