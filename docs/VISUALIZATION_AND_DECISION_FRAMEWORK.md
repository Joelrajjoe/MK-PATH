# Visualization, Analysis & Decision Framework Specification

## 1. Overview
This document specifies the technical architecture, implementation, and verification for:
1. **ZIP Archive Ingestion & Data Model Development**
2. **Context-Driven Business Goal Analysis, Empirical Conclusions & Strategic Decision-Making Framework**
3. **18-Chart Analytics Visualization Suite Across 5 Categories**
4. **Zero-Warning Scikit-Learn Model Tournament Pipelines**

---

## 2. Ingestion & Data Model Development

### 2.1 Archive Validation & Size Thresholds
- **Upload Payload Limit:** Expanded to 500 MB (`MAX_UPLOAD_MB = 500`), resolving HTTP 413 `Request Entity Too Large` errors during multi-dataset uploads.
- **Archive Entry Quota:** 1,000 entries max (`MAX_ZIP_ENTRIES = 1000`).
- **Decompressed Size Limit:** 2,000 MB (`MAX_ZIP_UNCOMPRESSED_MB = 2000`).
- **Nesting Depth Budget:** 1 level (`MAX_ZIP_DEPTH = 1`), safeguarding against recursion bombs while cleanly supporting nested archives.
- **Supported Formats:** `.csv`, `.tsv`, `.txt`, `.json`, `.parquet`, `.xlsx`, `.xls`, `.sql`, `.zip`.

### 2.2 Relational Model & DuckDB Registration
When a ZIP file containing multiple datasets is uploaded:
1. Each archive member is extracted to isolated temporary staging.
2. The file is validated (extension check, magic byte sniff, path-traversal prevention).
3. The table is converted to normalized Parquet on storage.
4. An immediate DuckDB analytical view (`ds_<uuid>`) is registered.
5. Column metadata and types are parsed via `DESCRIBE "ds_<uuid>"`.
6. Dataset metadata documents are persisted into MongoDB/local fallback with `archive_member` tracking and `table_name`.

---

## 3. Business Goal Analysis, Data Conclusions & Decision Framework

### 3.1 Objective Formulation & Dynamic Schema Grounding
The analysis pipeline (`POST /api/analysis/plan`) takes the user's natural language business goal and matches requested metrics and segment dimensions against columns that actually exist in the table view.
- **Binder Error Prevention:** The engine inspects DuckDB `DESCRIBE` schema output before query generation. If a requested column does not exist in the active dataset, the engine dynamically falls back to the top statistical numeric or categorical columns rather than failing.

### 3.2 Empirical Data Conclusions
In `POST /api/analysis/execute`, DuckDB computes real statistical aggregations over verified rows:
- **Total Accumulation & Benchmark Means:** `SUM`, `AVG`, `MIN`, `MAX`, `STDDEV`.
- **Primary Segment Concentration:** Percentage share of top categories to total records.
- **Filter Segment Evidence:** Targeted sub-cohort totals and record counts.

### 3.3 Strategic Decision-Making Statements & Decision Matrix
The system synthesizes context-aware strategic directives:
- **Prioritize Capital & Resource Reallocation:** Targeted operational workflows for categories holding dominant volume share.
- **Benchmark Variance Safeguards:** Dynamic outlier bounding and standard deviation triggers around mean values.
- **Multidimensional Cross-Cohort Audits:** Disaggregated tracking across primary and secondary dimensions.
- **Decision Matrix Structure:**
  | Focus Area | Key Finding | Strategic Recommendation | Impact | Confidence |
  | :--- | :--- | :--- | :--- | :--- |
  | Segment Optimization | 50.0% volume in top cohort | Dedicated SLA controls | High | 98% |
  | Metric Variance Control | Mean vs Max spread detected | Standard deviation bounds | High | 95% |
  | Multivariate Alignment | Independent group dynamics | Automated cross-cohort tabs | Medium | 92% |

---

## 4. 18-Chart Visualization Suite Across 5 Categories

Implemented as pure, responsive React SVG in `frontend/src/components/visualization/DataVisualizer.tsx`:

### Category 1: Comparison & Ranking
| Chart Type | Key Characteristic | Ideal Use Case |
| :--- | :--- | :--- |
| **Vertical Bar Chart** | SVG vertical rectangles with value tops | Discrete category comparison |
| **Horizontal Bar Chart** | SVG horizontal bars with category axis | Ranking items with long text labels |
| **Grouped Bar Chart** | Side-by-side multi-series bars | Comparing secondary cohorts within categories |
| **Stacked Bar Chart** | Vertically stacked bars | Showing part-to-whole categorical contributions |
| **Line Chart** | Connected SVG polyline/spline with points | Continuous metric trajectories over time |
| **Area Chart** | Shaded gradient area under line | Emphasizing cumulative volume of change |

### Category 2: Composition & Part-to-Whole
| Chart Type | Key Characteristic | Ideal Use Case |
| :--- | :--- | :--- |
| **Donut / Pie Chart** | Polar arc paths with center metric sum | 3–7 category proportional breakdown |
| **Treemap** | Proportional nested rectangular partitions | High-density multi-category hierarchy |
| **Stacked Area Chart** | Cumulative stacked continuous bands | Evolution of category compositions over time |
| **Waterfall Chart** | Floating positive/negative delta blocks | Financial & operational margin reconciliation |

### Category 3: Distribution & Spread
| Chart Type | Key Characteristic | Ideal Use Case |
| :--- | :--- | :--- |
| **Histogram** | Equal-width frequency bins | Shape of continuous metric distribution |
| **Box & Whisker Plot** | 5-number summary (Min, Q1, Med, Q3, Max) | Spread, interquartile range & outliers |
| **Density Plot (KDE)** | Gaussian kernel density estimate curve | Continuous probability distribution smoothing |
| **Violin Plot** | Mirrored KDE envelope with median dot | Combined density shape & quartile markers |

### Category 4: Correlation & Relationship
| Chart Type | Key Characteristic | Ideal Use Case |
| :--- | :--- | :--- |
| **Scatter Plot** | Bivariate Cartesian points with trendline | Identifying clusters and correlations |
| **Bubble Chart** | Cartesian points with 3rd-variable radius | Tri-variate relationship analysis |
| **Heatmap** | 2D color intensity matrix grid | Cross-category density & correlation mapping |

### Category 5: Specialized & Advanced Workflows
| Chart Type | Key Characteristic | Ideal Use Case |
| :--- | :--- | :--- |
| **Sankey Diagram** | Curved bezier ribbons connecting nodes | Tracking volume transfers & process stages |
| **Choropleth (Map)** | Regional tiles shaded by metric intensity | Geographic distribution & state/region density |
| **Radar / Spider Chart**| Equiangular polygonal web on radial axes | Multi-metric profile comparison |

---

## 5. Model Tournament Stability
- Wrapped all linear and logistic classifiers inside `make_pipeline(StandardScaler(), ...)` with `max_iter=2000` and `random_state=42`.
- Completely resolved Scikit-learn `ConvergenceWarning: lbfgs failed to converge after 1000 iteration(s)`.
- Verified 100% deterministic tournament ranking between Logistic Regression, Random Forest, and LightGBM.

---

## 6. Test Suite & Verification Results
- **Ingestion Test Suite (`tests/test_ingestion.py`):** 35 passed, 0 failed (100% passing).
- **Profiling Test Suite (`tests/test_profiling.py`):** 7 passed, 0 failed (100% passing).
- **Projects & Remediation Suites (`tests/test_projects.py`, `tests/test_remediation.py`):** 2 passed, 0 failed (100% passing).
- **End-to-End User Verification Script (`scratch/test_user_requirements.py`):**
  - ZIP multi-dataset bundle upload: Status 201 Created.
  - DuckDB views registered and verified: 100% successful.
  - Dynamic goal analysis execution: 100% successful.
  - Empirical conclusions & decision matrix generated: 100% populated.
  - Model tournament: Zero warnings, 100% successful.
- **Frontend Production Build (`npm run build`):** Built in 32.00s with 0 TypeScript and 0 Vite errors.
