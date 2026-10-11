# MK-Path

Multi-agent Knowledge Platform for Autonomous Transformation & Healing

**Positioning:** Evidence-Gated Autonomous Data Platform

---

## Architecture

- **Backend:** Python 3.10+, FastAPI, MongoDB Atlas / Local Fallback, DuckDB (Deterministic Analytical Engine & Zero-LLM Profiling), Scikit-Learn / LightGBM, Semantic Knowledge Layer.
- **Frontend:** React 19, TypeScript, Tailwind CSS, shadcn/ui, Custom Interactive SVG Visualization Engine.
- **Storage:** Fully isolated to the storage environment (`E:\MKPATH`).

---

## Key Capabilities & Core Workflows

### 1. Robust ZIP Archive Ingestion & Multi-Model Development
- **High-Capacity Ingestion:** Configured for large archive bundles (up to 500 MB) preventing HTTP 413 `Request Entity Too Large` limits.
- **Safe Extraction & Bomb Protection:** Enforces strict path-traversal prevention, compression ratio bounds, and nesting depth policies (`MAX_ZIP_DEPTH = 1`).
- **Automatic Data Model Development:** Each data file in an archive (CSV, TSV, JSON, Parquet, Excel, SQL) is independently parsed, validated, and immediately registered as a queryable DuckDB view (`ds_<id>`).
- **Schema & Quality Profiles:** Extract column types, nullability, row/column counts, and deterministic data quality scores (0–100) on demand.

### 2. User-Goal Driven Analysis, Data Conclusions & Strategic Decision Making
- **Custom Business Goal Planning:** Accepts natural language user objectives (e.g. *"Analyze customer segments, order volume, discounting trends, and operational efficiency"* or *"Analyze accident frequency, vehicle types, and emergency response minutes by road segment"*).
- **Schema-Grounded SQL Execution (Zero Binder Errors):** Strict validation between requested analysis metrics and actual table columns prevents SQL runtime binder errors.
- **Empirical Data Conclusions:** Automatically extracts key volume drivers, aggregate benchmarks, mean distributions, and category concentrations directly from verified rows.
- **Actionable Decision-Making Statements:** Synthesizes strategic operational directives (e.g. resource reallocation, benchmark variance controls, cross-segment audits).
- **Structured Decision Matrix:** Formulates a decision table with **Focus Area**, **Key Finding**, **Strategic Recommendation**, **Impact Rating (High/Medium)**, and **Confidence Score**.

### 3. Comprehensive 18-Chart Visualization Suite Across 5 Categories
Integrated directly into the **Data Analyst Workspace** and **Dataset Explorer** via `<DataVisualizer />`:

1. **Comparison & Ranking**
   - **Vertical Bar Chart:** Compares discrete categorical values with proportional heights.
   - **Horizontal Bar Chart:** Ideal for category ranking and long label comparison.
   - **Grouped Bar Chart:** Side-by-side metric comparison across secondary cohorts.
   - **Stacked Bar Chart:** Multi-series categorical breakdown showing relative contributions.
   - **Line Chart:** Continuous metric tracking and temporal fluctuations with hover points.
   - **Area Chart:** Volume-emphasized metric trajectory with translucent gradients.

2. **Composition & Part-to-Whole**
   - **Pie / Donut Chart:** Angle-proportional breakdown with center aggregate totals and interactive slices.
   - **Treemap:** Nested rectangular area partitioning for multi-category hierarchies.
   - **Stacked Area Chart:** Cumulative continuous volume distribution over intervals.
   - **Waterfall Chart:** Financial and operational delta progression (Base → Increments/Decrements → Total).

3. **Distribution & Spread**
   - **Histogram:** Equal-width binning revealing continuous frequency density.
   - **Box and Whisker Plot (Boxplot):** Five-number statistical summary (Min, Q1, Median, Q3, Max) with IQR whiskers.
   - **Density Plot (Kernel Density Estimate):** Smoothed Gaussian probability distribution curve.
   - **Violin Plot:** Mirrored probability density envelope combined with internal median and quartile markers.

4. **Correlation & Relationship**
   - **Scatter Plot:** Bivariate Cartesian mapping of two continuous numeric columns with linear trend analysis.
   - **Bubble Chart:** Tri-variate visualization mapping a 3rd numeric column to bubble radius.
   - **Heatmap:** 2D grid matrix displaying cross-category metric density and intensity shading.

5. **Specialized & Advanced Workflows**
   - **Sankey Diagram:** Flow and volume transfers between source nodes and target outcomes.
   - **Choropleth (Map):** Regional geographic distribution with metric density shading.
   - **Radar / Spider Chart:** Multi-dimensional profile comparison across equiangular radial spokes.

### 4. Robust Modeling Tournament
- **Pre-Scaled Numerical Pipelines:** Logistic Regression and Linear Models wrapped in `StandardScaler` with convergence limits (`max_iter=2000`), completely eliminating scikit-learn `ConvergenceWarning`.
- **Multi-Algorithm Tournament:** Benchmarks Logistic Regression, Random Forest, and LightGBM across AUC, F1, latency, and memory footprint.

---

## Getting Started

### Backend
```bash
cd backend
..\.venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### Frontend
```bash
cd frontend
npm run dev
```

---

## Verification & Testing
Run backend test suites:
```bash
cd backend
..\.venv\Scripts\python -m pytest tests/test_ingestion.py tests/test_profiling.py tests/test_projects.py tests/test_remediation.py
```
Run frontend production build verification:
```bash
cd frontend
npm run build
```
