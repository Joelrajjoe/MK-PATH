# Data Dictionary: Executive Performance Management Dashboard

This data dictionary outlines the schema of the verified benchmark dataset (`synthetic_road_accidents_prevention.csv`, 2,500 rows, 30 columns) and specifies column roles within the Power BI analytics engine.

---

## 1. Verified Benchmark Dataset Schema

| Column Name | Physical Data Type | Role in Dashboard | Nullable | Description & Domain Values |
| :--- | :--- | :--- | :--- | :--- |
| `incident_id` | `VARCHAR` | Identifier | No | Unique incident key (e.g. `INC-2024-0001`). Excluded from grouping. |
| `incident_date` | `VARCHAR` (`DD-MM-YYYY`) | Temporal Dimension | No | Event date parsed into Year, Quarter, Month for Time Intelligence. |
| `day_of_week` | `VARCHAR` | Temporal Cohort | No | Day of occurrence (`Monday`, `Tuesday`, etc.). |
| `month` | `INTEGER` | Temporal Slicing | No | Month integer (1 to 12). |
| `hour_of_day` | `INTEGER` | Time of Day | No | Hour of occurrence (0 to 23). |
| `city` | `VARCHAR` | Secondary Location Dimension | No | Geographic location for **Card 6** (`Chennai`, `Mumbai`, `Delhi`, etc.). |
| `segment_id` | `VARCHAR` | Segment Key | No | Road segment key (e.g. `SEG-0051`). Excluded from primary grouping. |
| `road_type` | `VARCHAR` | Primary Categorical Dimension | No | Category for **Card 3, 4, 5** (`Urban arterial`, `Highway`, `Residential`, etc.). |
| `speed_limit` | `INTEGER` | Numeric Measure | No | Speed limit in km/h (40, 60, 80, 100). |
| `traffic_volume` | `INTEGER` | Numeric Measure | No | Average hourly vehicle flow. |
| `weather_condition` | `VARCHAR` | Environmental Filter | No | Weather (`Clear`, `Rain`, `Fog`, `Overcast`). |
| `road_condition` | `VARCHAR` | Road Surface | No | Surface condition (`Dry`, `Wet`, `Potholes`). |
| `lighting_condition` | `VARCHAR` | Visibility Cohort | No | Lighting (`Daylight`, `Night - lit`, `Night - unlit`). |
| `primary_contributing_factor` | `VARCHAR` | Causality Factor | No | Cause (`Speeding`, `Driver inattention`, `Failure to yield`). |
| `severity` | `VARCHAR` | Event Severity | No | Severity level (`Minor`, `Serious`, `Fatal`, `None`). |
| `vehicles_involved` | `INTEGER` | Numeric Metric | No | Count of vehicles involved in incident. |
| `casualties` | `INTEGER` | Numeric Metric | No | Total casualties (injured or deceased). |
| `emergency_response_minutes` | `DOUBLE` | Operational Metric | No | Minutes to dispatch and arrive on site. |
| `accident_occurred` | `VARCHAR` | Target Event Outcome | No | Binary outcome flag (`Yes` or `No`). Used as primary numerator. |
| `intervention_status` | `VARCHAR` | Action Tracking | No | Remediation status (`Completed`, `Pending`, `Under Review`). |
| `enforcement_camera_present` | `VARCHAR` | Control Feature | No | Presence of speed/enforcement cameras (`Yes`, `No`). |
| `pedestrian_density` | `VARCHAR` | Exposure Factor | No | Density level (`Low`, `Medium`, `High`). |
| `visibility_meters` | `DOUBLE` | Environmental Measure | No | Visual sightline distance in meters. |
| `braking_distance_meters` | `DOUBLE` | Technical Metric | No | Measured braking distance. |
| `surface_friction_coefficient`| `DOUBLE` | Technical Metric | No | Friction coefficient (0.2 to 0.9). |
| `road_curvature_deg` | `DOUBLE` | Geometric Measure | No | Road curve degrees. |
| `gradient_pct` | `DOUBLE` | Geometric Measure | No | Road slope percentage. |
| `pavement_quality_index` | `DOUBLE` | Infrastructure Quality | No | PQI score (0 to 100). |
| `audit_status` | `VARCHAR` | Verification State | No | Data validation status. |
| `data_source` | `VARCHAR` | Origin System | No | Ingestion source sensor / telemetry. |

---

## 2. Dynamic Schema Introspection Rules

When a user uploads a new custom dataset, the analytics engine executes automated role assignment via `_detect_schema_roles()`:

1. **Temporal Dimension Detection:**
   - Evaluates column names matching: `date`, `time`, `timestamp`, `incident_date`, `created_at`, `order_date`.
   - Inspects SQL data types (`DATE`, `TIMESTAMP`).
   - If found, parses strings using `strptime` or `TRY_CAST` to derive `Year`, `Quarter`, and `Month`.

2. **Target Outcome Detection:**
   - Evaluates column names matching: `accident_occurred`, `occurred`, `target`, `converted`, `is_event`, `success`, `outcome`, `status`.
   - Identifies affirmative values (`'Yes'`, `'1'`, `'True'`, `'true'`, `'Y'`) to compute event rates.

3. **Primary Categorical Dimension Detection:**
   - Evaluates text/varchar columns excluding identifier patterns (`*_id`, `id_*`, `id`).
   - Prefers column names containing: `road_type`, `team`, `department`, `category`, `segment`, `division`.
   - Assigns this column to **Card 3 (Top & Bottom Teams)**, **Card 4 (Quarterly Performance Tabs)**, and **Card 5 (Meetings Attended)**.

4. **Secondary Dimension Detection:**
   - Evaluates text/varchar columns excluding primary category and IDs.
   - Prefers column names containing: `city`, `location`, `weather`, `region`, `state`, `branch`, `area`.
   - Assigns this column to **Card 6 (Location Performance Benchmark)**.

5. **Primary Numeric Measure Detection:**
   - Identifies non-ID numeric columns (`INTEGER`, `FLOAT`, `DOUBLE`, `DECIMAL`).
   - Uses sum or average as fallback when no binary event column exists.
