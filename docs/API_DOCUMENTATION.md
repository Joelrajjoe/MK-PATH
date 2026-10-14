# API Documentation: Executive Performance Dashboard

This document details all API endpoints powering the real-time Executive Performance Management Dashboard, including request bodies, response models, error states, and schema definitions.

---

## 1. Executive Dashboard API Endpoints

### `POST /api/dashboard/analytics`
Calculates deterministic, server-side Power BI-style metrics over DuckDB Parquet storage.

- **Request Body:**
  ```json
  {
    "dataset_id": "2b1bea2f53614aae81af671a84b8eb52",
    "project_id": "default",
    "dataset_name": "Road Accidents Prevention",
    "filter_context": {
      "year": 2024,
      "quarter": "Q1",
      "team": "Urban arterial",
      "location": "Chennai",
      "search_query": ""
    }
  }
  ```
- **Response Model:** `DashboardAnalyticsPayload` (`200 OK`)
  - `dataset_id`: `str`
  - `dataset_name`: `str`
  - `project_id`: `str`
  - `readiness_status`: `"VALIDATING" | "READY" | "READY_WITH_WARNINGS" | "BLOCKED" | "STALE" | "ERROR"`
  - `status_explanation`: `str`
  - `filter_context`: `FilterContext`
  - `quality_summary`: `DataQualitySummary` (total records, filtered records, null rate, date boundaries)
  - `card1_quarter_to_quarter`: `Card1QuarterToQuarter` (QoQ change %, formatted string, sparkline points)
  - `card2_year_over_year`: `Card2YearOverYear` (YoY change %, formatted string, yearly sparkline)
  - `card3_top_bottom_teams`: `Card3TopBottomTeams` (top 3 and bottom 3 items with percentages and icons)
  - `card4_quarterly_performance`: `Card4QuarterlyPerformance` (available tabs, quarterly combo series)
  - `card5_meetings_attended`: `Card5MeetingsAttended` (radial gauge percentage, numerator, denominator)
  - `card6_engineering_performance`: `Card6EngineeringPerformance` (benchmark radial gauge score)
  - `computation_time_ms`: `float`
- **Error Responses:**
  - `404 Not Found`: Dataset not found or Parquet file missing.
  - `500 Internal Server Error`: SQL binder or mathematical computation exception.

---

### `GET /api/dashboard/filters`
Extracts available distinct dimensions for cascading filters from the source dataset.

- **Query Parameters:**
  - `dataset_id` (required): `string`
- **Response Model:** `FilterDimensions` (`200 OK`)
  ```json
  {
    "years": [2024, 2025, 2026],
    "quarters": ["Q1", "Q2", "Q3", "Q4"],
    "teams": ["Urban arterial", "Highway", "Residential", "School zone", "Rural road", "Intersection"],
    "locations": ["Chennai", "Mumbai", "Delhi", "Kolkata", "Bangalore"],
    "date_min": "01-01-2024",
    "date_max": "31-12-2025"
  }
  ```

---

### `POST /api/dashboard/drilldown`
Retrieves verified underlying records for any clicked visual component, card, or ranking item.

- **Request Body:** `DrilldownRequest`
  ```json
  {
    "dataset_id": "2b1bea2f53614aae81af671a84b8eb52",
    "card_id": "card3_top_bottom_teams",
    "category_tab": "Urban arterial",
    "location_tab": null,
    "page": 1,
    "page_size": 15
  }
  ```
- **Response Model:** `DrilldownResponse` (`200 OK`)
  ```json
  {
    "card_id": "card3_top_bottom_teams",
    "filter_description": "Drilldown for card3_top_bottom_teams [Category: Urban arterial]",
    "total_matching_records": 691,
    "page": 1,
    "page_size": 15,
    "columns": ["incident_id", "incident_date", "day_of_week", "month", "hour_of_day", "city", ...],
    "rows": [
      {
        "incident_id": "INC-2024-0001",
        "incident_date": "15-03-2024",
        "city": "Chennai",
        "road_type": "Urban arterial",
        "speed_limit": 60,
        "accident_occurred": "Yes"
      }
    ]
  }
  ```

---

### `POST /api/dashboard/verify`
Executes independent, non-nested DuckDB SQL assertions against raw storage to verify calculation integrity.

- **Request Body:**
  ```json
  {
    "dataset_id": "2b1bea2f53614aae81af671a84b8eb52",
    "project_id": "default",
    "filter_context": null
  }
  ```
- **Response Model:** `ReconciliationResponse` (`200 OK`)
  ```json
  {
    "dataset_id": "2b1bea2f53614aae81af671a84b8eb52",
    "reconciliation_passed": true,
    "verified_at": "2026-10-14T07:53:33.852Z",
    "items": [
      {
        "metric_name": "Total Record Count",
        "dashboard_value": 2500,
        "independent_sql_value": 2500,
        "tolerance": 0.0,
        "is_exact_match": true,
        "sql_query": "SELECT count(*) FROM \"ds_2b1bea2f53614aae81af671a84b8eb52\""
      },
      {
        "metric_name": "Filtered Record Count Context",
        "dashboard_value": 2500,
        "independent_sql_value": 2500,
        "tolerance": 0.0,
        "is_exact_match": true,
        "sql_query": "SELECT count(*) FROM \"ds_2b1bea2f53614aae81af671a84b8eb52\" WHERE 1=1"
      },
      {
        "metric_name": "Sum of road_type Categories vs Filtered Context",
        "dashboard_value": 2500,
        "independent_sql_value": 2500,
        "tolerance": 0.0,
        "is_exact_match": true,
        "sql_query": "SELECT COALESCE(SUM(cat_count), 0) FROM (SELECT COUNT(*) as cat_count FROM \"ds_2b1bea2f...\" GROUP BY road_type)"
      },
      {
        "metric_name": "Card 5 Rate Numerator/Denominator for Urban arterial",
        "dashboard_value": {"num": 237.0, "denom": 691.0},
        "independent_sql_value": {"num": 237.0, "denom": 691.0},
        "tolerance": 0.0,
        "is_exact_match": true,
        "sql_query": "SELECT COUNT(*) as denom, COUNT(CASE WHEN accident_occurred = 'Yes' THEN 1 END) as num ..."
      },
      {
        "metric_name": "Card 6 Benchmark Counts for Chennai",
        "dashboard_value": {"num": 190.0, "denom": 520.0},
        "independent_sql_value": {"num": 190.0, "denom": 520.0},
        "tolerance": 0.0,
        "is_exact_match": true,
        "sql_query": "SELECT COUNT(*) as denom, COUNT(CASE WHEN accident_occurred = 'Yes' THEN 1 END) as num ..."
      }
    ],
    "summary": "Verified 5 independent SQL assertions against DuckDB Parquet storage. All checks passed with zero tolerance (100% exact match)."
  }
  ```

---

### `POST /api/dashboard/export`
Generates an executive reconciliation report in CSV or JSON matching the exact active dashboard calculation.

- **Request Body:**
  ```json
  {
    "dataset_id": "2b1bea2f53614aae81af671a84b8eb52",
    "project_id": "default",
    "format": "csv",
    "filter_context": null
  }
  ```
- **Response:**
  - Content-Type: `text/csv` (or `application/json`)
  - Content-Disposition: `attachment; filename=dashboard_report_2b1bea2f.csv`
  - Contains executive metadata header, cards 1 & 2 highlights, top/bottom team rankings, quarterly series, and donut gauge metrics.
