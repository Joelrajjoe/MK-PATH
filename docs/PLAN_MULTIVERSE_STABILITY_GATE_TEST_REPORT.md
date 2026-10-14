# Plan-Multiverse Stability Gate (PMSG) — Test & Verification Report

**Test Date:** 2026-10-14  
**Environment:** Windows 11, Python 3.10.7, FastAPI 0.136.1, DuckDB 0.10.0, PyMongo 4.15.1, Motor 3.7.1, React 19, Vite 8, Tailwind CSS  
**Metadata Persistence Engine:** MongoDB Atlas (`mk_path` database, collection: `pmsg_runs`)  
**Analytical Execution Engine:** In-Process DuckDB reading PyArrow Parquet views on E: drive  
**Test Suite:** `backend/tests/test_pmsg.py` (13 test cases executed via pytest)  
**Execution Result:** **13 PASSED, 0 FAILED (100% Pass Rate)**  

---

## 1. Verified Target Dataset

The initial functional verification was executed against the project's real synthetic traffic safety dataset:

- **Filename:** `synthetic_road_accidents_prevention.csv`
- **Normalized Parquet Path:** `E:\MKPATH\data\0d8869e35d5f408f965561fae55a0af9\2b1bea2f53614aae81af671a84b8eb52.parquet`
- **Dataset ID:** `2b1bea2f53614aae81af671a84b8eb52`
- **Total Rows Verified:** `2,500`
- **Total Columns Verified:** `30`
- **Key Fields Verified:**
  - `road_type`: Categorical (Urban arterial: 691, Highway: 465, Residential: 424, Intersection: 412, Rural road: 277, School zone: 231)
  - `accident_occurred`: Categorical (`Yes`: 907, `No`: 1,593)
  - `accident_severity`: Categorical (Minor injury: 401, Property damage: 355, Serious injury: 137, Fatal: 14, No accident / near miss: 1,593)
  - `posted_speed_limit_kmh`: Numeric integer
  - `estimated_vehicle_speed_kmh`: Numeric float
  - `incident_date`: Datetime string (`DD-MM-YYYY`)

---

## 2. Test Cases Executed & Results

All 13 test cases in `backend/tests/test_pmsg.py` were executed via PyTest:

| Test Name | Test Category | Target Assertion | Result |
| :--- | :--- | :--- | :--- |
| `test_variant_generation_determinism` | Unit (Generator) | Identical plan and schema produce bit-for-bit identical variant lists across repeated runs. | **PASS** |
| `test_variant_budget_enforcement` | Unit (Generator) | Generator respects budgets (1, 3, 5, 8) and ensures primary plan is always variant #0. | **PASS** |
| `test_incompatible_operator_detection` | Unit (Generator) | Traffic exposure without exposure/VMT column is classified as `INVALID` with diagnostic reason. | **PASS** |
| `test_estimand_change_separation` | Unit (Generator) | Within-group occurrence rate is classified as `ESTIMAND_CHANGE` and placed in distinct family. | **PASS** |
| `test_fractional_ranks_calculation` | Unit (Math) | Ties are assigned standard average fractional ranks (e.g. [50, 30, 30, 10] $\to$ [1, 2.5, 2.5, 4]). | **PASS** |
| `test_spearman_rho_known_values` | Unit (Math) | Correlation evaluates to exactly 1.0 for identical ranks and -1.0 for inverted ranks. | **PASS** |
| `test_stability_metrics_on_fixture` | Unit (Metrics) | Known hand-calculated fixture (3 matches, 1 reversal) outputs exact persistence (0.75) and reversal (0.25). | **PASS** |
| `test_gate_decision_pass` | Unit (Gate) | High persistence (1.0) and low reversal rate (0.0) produce `PASS` and `eligible_for_deployment = True`. | **PASS** |
| `test_gate_decision_fail_on_reversal` | Unit (Gate) | Low persistence (0.60) and high reversal (0.40) produce `FAIL` and `eligible_for_deployment = False`. | **PASS** |
| `test_gate_prohibits_silent_pass_on_failure` | Unit (Gate) | Crashing or failed variant executions prohibit silent `PASS`, issuing `WARNING` or `FAIL`. | **PASS** |
| `test_api_policies` | Integration (API) | `GET /api/stability/policies` returns versioned policy schemas including `PMSG-POLICY-v1.0`. | **PASS** |
| `test_api_plan_and_preview` | Integration (API) | `POST /api/stability/plan` and `/variants/preview` return valid specifications from actual dataset. | **PASS** |
| `test_api_stability_run_real_dataset` | Integration (E2E) | `POST /api/stability/run` executes against real DuckDB dataset, persists to Atlas, and updates `/api/verification/gates`. | **PASS** |

---

## 3. Real Dataset Multiverse Execution Telemetry

Executing `execute_stability_run` on `synthetic_road_accidents_prevention.csv` produced the following measured telemetry:

- **Total Execution Runtime:** `140.23 ms` across all 10 scheduled variants.
- **Planned Variants:** `10`
- **Valid Comparable Variants:** `8`
- **Completed Comparable Variants:** `8` ($100.0\%$ execution coverage)
- **Failed Variants:** `0`
- **Incompatible Variants:** `1` (`var_denom_exposure_incompatible`, transparently skipped due to lack of VMT column)
- **Estimand-Divergent Variants:** `1` (`var_denom_within_group_rate`, isolated in `within_group_rate` family)

### 3.1 Measured Stability Metrics:
- **Top-Category Persistence:** **$100.0\%$**  
  *Urban arterial remained the Rank 1 category in all 8 comparable variants.*
- **Spearman Rank Correlation:** **$0.979$**  
  *Near-perfect ranking consistency across all 6 road types.*
- **Conclusion Reversal Rate:** **$12.5\%$**  
  *(One variant, `var_denom_all_records`, shifted scale from $26.13\%$ to $9.48\%$ because the denominator was expanded to all 2,500 records; ranking order remained identical).*
- **Primary Effect Range:** $[0.0948, 0.2809]$
- **Overall Gate Status:** **`PASS`**
- **Deployment Eligibility:** **`PERMITTED`**
- **MongoDB Atlas Persistence:** Confirmed (`pmsg_runs` collection).

### 3.2 Estimand Sensitivity Observation:
When evaluating the alternative estimand *"Occurrence rate within each road type"* ($N=2,500$):
- **Residential** took Rank 1 ($39.39\%$).
- **Highway** took Rank 2 ($37.20\%$).
- **Intersection** took Rank 3 ($37.14\%$).
- **Urban arterial** dropped to **Rank 6 ($34.30\%$)**.

**Verification Value:** PMSG prevented an autonomous agent or human analyst from mistakenly claiming that Urban arterial is the "most dangerous road type" when in fact Residential has the highest accident rate per observation. PMSG proved that Urban arterial merely accounts for the highest *absolute share* of accidents ($26.13\%$) due to higher exposure/frequency, while Residential exhibits higher within-category occurrence rate.

---

## 4. Frontend & Build Verification

- **TypeScript Compilation (`tsc -b`):** Passed with 0 errors.
- **Vite Production Bundle (`vite build`):** Built in 15.7s. Output: `dist/index.html`, `dist/assets/index-B3VyR6vL.js`.
- **UI Workspaces Verified:**
  1. `VerificationCenter.tsx`: Integrated PMSG as a primary tab and linked gate item in the mandatory gates matrix.
  2. `DataAnalystWorkspace.tsx`: Added direct "Multiverse Stability Gate (PMSG)" action button in header.
  3. `ProjectWorkspace.tsx`: Supported `/projects/:id/verification/stability` deep link.

---

## 5. Non-Negotiable Rules Audit Checklist

- [x] Zero mock findings, fake metrics, or fabricated model results.
- [x] DuckDB deterministic execution on real Parquet views.
- [x] Persistent execution records stored in MongoDB Atlas (`pmsg_runs`).
- [x] No local JSON or SQLite fallback introduced as an invisible substitute for Atlas.
- [x] Separated comparable variants from estimand changes.
- [x] Disclosed skipped and incompatible variants with exact schema reasons.
- [x] Verified deployment-blocking behavior on gate failure.
- [x] No exposure rates calculated without continuous traffic exposure data.
