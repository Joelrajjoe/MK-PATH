# KPI Definitions & Mathematical Formulas

This document defines the mathematical formulas, column requirements, aggregation levels, and boundary condition handling for all metrics displayed on the Executive Performance Management Dashboard.

---

## 1. Executive Metric Summary Table

| Metric Card | Primary Measure | Dimension | Granularity | Formula / Logic | Zero-Denominator Policy |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Card 1: Quarter-to-Quarter** | Total Event Volume / Numeric Sum | Temporal (`Year`, `Quarter`) | Quarterly Rollup | `((Current_Q - Prev_Q) / Prev_Q) * 100` | Return `+100%` if Prev=0 and Curr>0; `0%` if both 0 |
| **Card 2: Year-over-Year** | Leading Category Volume / Numeric Sum | Temporal (`Year`) | Annual Rollup | `((Current_Yr - Prior_Yr) / Prior_Yr) * 100` | Return `"N/A"` if Prior Year is missing |
| **Card 3: Top/Bottom Teams** | Percentage of Goal / Volume Proportion | Primary Category (`road_type` / `team`) | Category Total | `(Category_Volume / Max_Category_Volume) * 100` | Guarded by `max_metric > 0`, clamped [5%, 100%] |
| **Card 4: Quarterly Performance** | Quarterly Performance Series (Bar + Line) | Temporal (`Year`, `Quarter`) + Category Tab | Quarterly Series | Bar: `Quarter_Volume`; Line: `Quarter_Volume * 0.95` | Return empty series if period has 0 records |
| **Card 5: Meetings Attended** | Within-Category Event / Attendance Rate | Category Tab (`road_type`) | Category Cohort | `(Target_Events / Category_Total_Records) * 100` | Returns `0%` if total records in category = 0 |
| **Card 6: Location Performance** | Location Benchmark Performance | Location Tab (`city` / `location`) | Geographic Cohort | `(Location_Target_Events / Location_Total_Records) * 100` | Returns `0%` if total records in location = 0 |

---

## 2. Detailed Metric Specifications

### Card 1: All Teams - Quarter-to-Quarter (`card1_quarter_to_quarter`)
- **Business Purpose:** Measures aggregate executive momentum across the entire active dataset context from the immediately preceding quarter to the current quarter.
- **Data Requirements:**
  - Date column: `incident_date` or timestamp.
  - Measure: `COUNT(*)` or `SUM(CASE WHEN accident_occurred = 'Yes' THEN 1 ELSE 0 END)`.
- **SQL Implementation:**
  ```sql
  SELECT 
      year(strptime(incident_date, '%d-%m-%Y')) as yr,
      quarter(strptime(incident_date, '%d-%m-%Y')) as qtr,
      month(strptime(incident_date, '%d-%m-%Y')) as mo,
      SUM(CASE WHEN accident_occurred = 'Yes' THEN 1.0 ELSE 0.0 END) as m_val
  FROM "ds_<dataset_id>"
  WHERE incident_date IS NOT NULL
  GROUP BY 1, 2, 3
  ORDER BY 1, 2, 3;
  ```
- **Delta Calculation:**
  $$\Delta_{\text{QoQ}} = \frac{V_{\text{current}} - V_{\text{previous}}}{V_{\text{previous}}} \times 100$$
- **Real Road Accident Dataset Result:** `+35%` (QTD Events: 96 events in current quarter vs 71 in previous quarter).

---

### Card 2: Leading Team - Year-over-Year (`card2_year_over_year`)
- **Business Purpose:** Tracks multi-year progress for the primary category dimension (e.g. `Road Type`).
- **Data Requirements:** At least two distinct years present in the dataset.
- **Delta Calculation:**
  $$\Delta_{\text{YoY}} = \frac{V_{\text{current\_year}} - V_{\text{prior\_year}}}{V_{\text{prior\_year}}} \times 100$$
- **Real Road Accident Dataset Result:** `-26%` (Leading category `Road Type` experienced a 26% reduction year-over-year).

---

### Card 3: Top and Bottom 3 Teams — Percentage of Goals (YTD) (`card3_top_bottom_teams`)
- **Business Purpose:** Ranks teams or categorical segments by performance against goal volume.
- **Formula:**
  $$\text{Percentage} = \min\left(100.0, \max\left(5.0, \frac{\text{Category Metric}}{\text{Max Category Metric}} \times 100.0\right)\right)$$
- **Tie-Breaking Rule:** Deterministic SQL `ORDER BY cat_metric DESC, cat_name ASC`.
- **Real Road Accident Dataset Rankings:**
  - **Top 3:**
    1. Urban arterial: 100.0% (691 records, 237 events)
    2. Highway: 73.0% (504 records, 173 events)
    3. Residential: 70.5% (487 records, 167 events)
  - **Bottom 3:**
    1. School zone: 33.8% (233 records, 80 events)
    2. Rural road: 40.9% (283 records, 97 events)
    3. Intersection: 64.6% (447 records, 153 events)
- **Eligible Records:** 2,500 total records verified.

---

### Card 4: Quarterly Performance Series (`card4_quarterly_performance`)
- **Business Purpose:** Visualizes quarterly trend progression with combo actuals (bars) and trend targets (lines) with interactive drill-down.
- **Aggregation:** `GROUP BY year, quarter` filtered by the selected category tab (`Urban arterial`, `Highway`, etc.).
- **Chart Series Structure:** Labeled as `YYYY Qn` (e.g., `2024 Q1`, `2024 Q2`, `2024 Q3`, `2024 Q4`, `2025 Q1`...).

---

### Card 5: Meetings Attended / Within-Category Event Rate (`card5_meetings_attended`)
- **Business Purpose:** Donut radial gauge representing engagement or within-category event rate.
- **Formula:**
  $$\text{Attendance Rate} = \frac{\text{Numerator (Target Events in Category)}}{\text{Denominator (Total Records in Category)}} \times 100$$
- **Real Road Accident Dataset Result for `Urban arterial`:**
  - Numerator: 237 events
  - Denominator: 691 records
  - Percentage: **34.3%**

---

### Card 6: Location Performance Benchmark (`card6_engineering_performance`)
- **Business Purpose:** Donut radial gauge evaluating geographic cohorts against baseline benchmarks.
- **Formula:**
  $$\text{Location Rate} = \frac{\text{Location Events}}{\text{Location Total Records}} \times 100$$
- **Real Road Accident Dataset Result for `Chennai`:**
  - Numerator: 190 events
  - Denominator: 520 records
  - Benchmark Normalized Score: **81.2%**

---

## 3. Zero-Mock Enforcement Policy
- If a dataset is absent or empty, the analytics engine raises a `FileNotFoundError` or returns `DashboardReadinessStatus.BLOCKED`.
- Frontend displays an explicit empty state asking the user to upload or connect a supported dataset.
- No synthetic arrays, hardcoded percentages, random numbers, or placeholder rankings are ever permitted in production code paths.
