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
