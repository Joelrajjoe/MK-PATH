# Architecture: Real-Time Dynamic Executive Performance Management Dashboard

## 1. System Overview

The **MK-Path Executive Performance Management Dashboard** is a high-performance, Power BI-inspired analytics application engineered on top of **DuckDB** and **FastAPI**, with a reactive **React 19 / TypeScript** frontend.

The core principle of this architecture is: **DATA MUST BE VERIFIED BEFORE IT IS DISPLAYED.**
Every metric, sparkline trend, ranking, combo bar-line series, and radial donut gauge is mathematically computed server-side directly over Parquet data storage using zero-mock, deterministic DuckDB SQL aggregations.

```mermaid
graph TD
    A[Source Files: CSV / Excel / JSON / Parquet] --> B[Ingestion & Security Gate]
    B --> C[Parquet Columnar Storage & DuckDB Registry]
    C --> D[DuckDB SQL Analytics Engine]
    D --> E[Independent Deterministic Reconciliation Engine]
    E --> F[FastAPI Dashboard Router]
    F --> G[Dynamic Executive Dashboard Frontend]
    G --> H[Cascading Filters & Drilldown Modals]
    G --> I[Independent SQL Assertion Drawer]
    G --> J[Verified CSV/JSON Reports]
```

---

## 2. Component Architecture

### A. Storage & Ingestion Tier
- **Local Parquet Fact Storage:** Data files uploaded via `/api/datasets/upload` are validated, sanitized, and stored as standardized Apache Parquet files in `datasets/parquet/<dataset_id>.parquet`.
- **DuckDB View Registry (`app.ingestion.registry`):** Dynamically registers dataset views as `"ds_<dataset_id>"` on an in-memory DuckDB connection, allowing instant sub-millisecond SQL queries over 2,500+ records.

### B. Power BI Analytics Engine (`app.analytics.engine`)
- **Schema Introspection:**
  - Automated role detection identifying temporal/date columns, primary categorical dimensions (e.g. `road_type`, `department`, `team`), secondary attributes (e.g. `city`, `location`), numeric measures, and binary target outcomes (`accident_occurred = 'Yes'`).
  - Strict exclusion of identifier keys (`*_id`, `id`) from category groupings.
- **Time Intelligence & Hierarchies:**
  - Automatic string date parsing (`strptime(incident_date, '%d-%m-%Y')` and ISO format support).
  - Multi-level time rollups: Year, Quarter, Month, and QTD (Quarter-to-Date).
  - Quarter-over-Quarter (QoQ) and Year-over-Year (YoY) trajectory deltas with percentage change calculations.
- **Dynamic Cascading Filter Context:**
  - Parameterized WHERE clause compilation preventing SQL injection.
  - Multi-dimensional filtering by Year, Quarter, Team/Category, Location, and text search.
- **Zero-Denominator & Safety Gate:**
  - Safe divisions guarded with explicit checks; returns `"N/A"` or unavailable status when denominators or prior periods are absent.

### C. Independent Reconciliation Engine (`app.analytics.reconciliation`)
- Standalone, un-nested SQL assertions executed directly against raw DuckDB tables.
- Compares:
  1. Total Record Count (`SELECT count(*)`)
  2. Filtered Record Count Context (`SELECT count(*) WHERE {filters}`)
  3. Dimension Group Sum Integrity (`SELECT sum(group_counts)`)
  4. Gauge Rate Numerators and Denominators
  5. Location Benchmark Counts
- Evaluates against a **0.0 tolerance** (exact match requirement).
- If any check deviates, the engine sets `reconciliation_passed = False` and logs a verification failure.

### D. API Tier (`app.routers.dashboard`)
- `POST /api/dashboard/analytics`: Computes complete typed payload (`DashboardAnalyticsPayload`).
- `GET /api/dashboard/filters`: Returns distinct years, quarters, teams, and locations for filter selectors.
- `POST /api/dashboard/drilldown`: Returns paginated raw underlying records for any drilled card or bar.
- `POST /api/dashboard/verify`: Executes the 5 independent SQL assertions and returns exact match telemetry.
- `POST /api/dashboard/export`: Generates executive reports in CSV or JSON format reconciling with dashboard figures.

### E. Frontend Presentation Tier (`ExecutivePerformanceDashboard.tsx`)
- Dark Executive Theme matching visual reference `#232b3b`:
  - Dark Navy Header (`#232b3b`) with live record counter and readiness status badge (`READY`, `READY_WITH_WARNINGS`, `BLOCKED`, `STALE`).
  - Dark Navy Vertical Navigation Sidebar (`#232b3b`) supporting Dashboard, Reports, Audit, and Settings views.
  - Crisp White Cards with Slate Headers (`#475569` / `#5f7185`) and `···` contextual action menus.
  - 6 Data-Driven Cards:
    1. Card 1: All teams - quarter-to-quarter (+35% QoQ, monthly sparkline).
    2. Card 2: Leading team - year-over-year (-26% YoY, yearly sparkline).
    3. Card 3: Top and bottom 3 teams - percentage of goals (YTD, green/red progress bars).
    4. Card 4: Quarterly team performance (tabbed combo bar + line chart with interactive drilldown).
    5. Card 5: Meetings attended / Engagement rate (tabbed circular radial donut gauge).
    6. Card 6: Location performance benchmark (tabbed circular radial donut gauge).
  - Independent SQL Verification Drawer & Interactive Underlying Record Drilldown Drawer.
