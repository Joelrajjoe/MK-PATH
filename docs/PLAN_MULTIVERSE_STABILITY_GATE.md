# Plan-Multiverse Stability Gate (PMSG)

**Component Type:** Core Verification & Analytical Robustness Engine  
**Module Path:** `backend/app/stability/`  
**API Endpoints:** `/api/stability/*`  
**Frontend Component:** `frontend/src/components/verification/PlanMultiverseStabilityGate.tsx`  
**Persistence:** MongoDB Atlas (`pmsg_runs` collection) & DuckDB Parquet Native Views  

---

## 1. Executive Summary & Purpose

In classical data analysis, an autonomous agent or human analyst often arrives at an empirical conclusion based on a single analytical pipeline. For example:

> *"Road type 'Urban arterial' has the highest proportion of recorded accidents."*

However, in real-world data science, that conclusion can be an artifact of subtle, defensible choices:
- How missing values are filtered vs. retained.
- How the denominator is defined (e.g., valid events vs. total population vs. group observations).
- How extreme values or outliers are treated.
- Whether infrequent or sparse categories are grouped into aggregate buckets.
- Which temporal partition or observation window is selected.

The **Plan-Multiverse Stability Gate (PMSG)** operationalizes analytical robustness by systematically generating, executing, and evaluating a controlled multiverse of defensible analytical specifications against real dataset contents.

**Core Principle:** An analytical finding never receives a verification `PASS` simply because one execution succeeded. Its stability must be deterministically proven using actual empirical computations across predefined, valid analysis variants.

---

## 2. Core Architectural Principles & Estimand Separation

### 2.1 The Four-Tier Variant Taxonomy

A critical flaw in naive sensitivity analysis is treating all analytical variations as interchangeable implementations of the same question. PMSG enforces a strict four-tier taxonomy:

1. **Implementation Variants (`IMPLEMENTATION`):**  
   Alternative safe computations estimating the *identical* target estimand.  
   *Example:* Handling missing grouping values by complete-case exclusion vs. assigning an explicit `'Unknown'` category.
2. **Reasonable Specification Variants (`SPECIFICATION`):**  
   Defensible alternative choices that affect numerical estimates but preserve the core research question sufficiently for ranking and comparison.  
   *Example:* Trimming 99th percentile speed extremes, merging categories with $<10\%$ sample share into an aggregate bucket, or evaluating temporal half-windows.
3. **Context / Estimand Divergence Variants (`ESTIMAND_CHANGE`):**  
   Alternative specifications that answer a *fundamentally different research question*.  
   *Example:* Calculating accident rate within each road type (accidents / total observations on that road type) answers *"Where is individual accident risk highest per observation?"*, whereas population share (accidents on road type / all accidents) answers *"Where do the bulk of recorded accidents occur?"*.  
   **Rule:** Estimand-change variants are *never* combined into the primary stability percentage; they are evaluated in isolated families with explicit divergence disclosures.
4. **Invalid / Incompatible Variants (`INVALID`):**  
   Analytical choices unsupported by the actual dataset schema.  
   *Example:* Evaluating accident rate per million Vehicle Miles Traveled (VMT) when the dataset possesses no exposure or continuous traffic volume column.  
   **Rule:** Rather than fabricating fake exposure data, PMSG records the variant as `INCOMPATIBLE` with transparent reasoning.

---

## 3. Variant Grammar & Controlled Generation

The variant generator (`backend/app/stability/generator.py`) applies a deterministic, bounded operator grammar with a maximum variant budget (default 12–15) to prevent combinatorial explosion:

| Operator Category | Base Primary Choice | Defensible Alternatives | Classification |
| :--- | :--- | :--- | :--- |
| **A. Missing-Value Policy** | Complete-case exclusion (`exclude_missing`) | Explicit `'Unknown'` category (`include_unknown`) | `IMPLEMENTATION` |
| **B. Denominator Definition** | Total target events (`valid_population_total`) | Total observed records (`all_records_total`) | `SPECIFICATION` |
| **B. Denominator (Estimand)** | Target population total | Occurrence rate within group (`within_group_total`) | `ESTIMAND_CHANGE` |
| **B. Denominator (Exposure)** | Target population total | Exposure-normalized rate (VMT) | `INVALID` (if schema lacks VMT) |
| **C. Outlier Policy** | No filtering (`none`) | 99th percentile cap on continuous columns | `SPECIFICATION` |
| **D. Category Policy** | Preserve all categories (`preserve_all`) | Merge sparse categories ($<10\%$) into `'Other'` | `SPECIFICATION` |
| **E. Date Window** | Entire observation span (`all_time`) | Early ($50\%$) & Late ($50\%$) temporal partitions | `SPECIFICATION` |
| **Joint Interaction** | Base specifications | Combined `'Unknown'` category + Outlier trim | `SPECIFICATION` |

---

## 4. Deterministic Execution Engine

The execution engine (`backend/app/stability/executor.py`) interfaces directly with DuckDB Parquet native views (`ds_<dataset_id>`):
- Parameterized and binder-safe SQL queries constructed for each variant.
- Tracks:
  - Exact row count and usable sample size $N$.
  - Number of excluded rows and specific exclusion reasons.
  - Computed numerators and denominators for every category.
  - Computed metric values (rounded to 6 decimal places).
  - Deterministic fractional rankings with ties handled.
  - Execution duration in milliseconds.
  - Cryptographic SHA-256 query hash.
- Captures individual query failures with full tracebacks; never treats execution failures as stability evidence.

---

## 5. Mathematical Stability Metrics

The metrics engine (`backend/app/stability/metrics.py`) computes pure deterministic metrics across comparable variants:

### 5.1 Direction Stability & Top-Category Persistence
$$\text{Top1 Persistence} = \frac{\sum_{v=1}^{V} \mathbb{I}(\text{TopCategory}_v = \text{TopCategory}_{\text{primary}})}{V}$$
Where $V$ is the number of successfully executed comparable variants.

### 5.2 Spearman Rank Correlation with Arbitrary Ties
For each variant $v$, mutual categories are assigned fractional ranks $R_i$ (for primary) and $S_i$ (for variant). Spearman's $\rho$ is computed as the Pearson correlation of fractional ranks:
$$\rho = \frac{\sum (R_i - \bar{R})(S_i - \bar{S})}{\sqrt{\sum (R_i - \bar{R})^2 \sum (S_i - \bar{S})^2}}$$
The mean Spearman $\rho$ across all variants measures global ranking consistency.

### 5.3 Effect-Size Dispersion
For the primary top category:
$$\text{Absolute Range} = \max_v(\theta_v) - \min_v(\theta_v)$$
$$\text{Relative Range} = \frac{\max_v(\theta_v) - \min_v(\theta_v)}{\theta_{\text{primary}}} \quad (\text{if } \theta_{\text{primary}} > 0)$$

### 5.4 Conclusion Reversal Rate
Frequency of material reversals where either the top-ranked group shifts or the metric value shifts beyond a practical bound ($>25\%$ relative shift):
$$\text{Reversal Rate} = \frac{N_{\text{reversals}}}{V}$$

### 5.5 Variant Coverage
$$\text{Coverage Ratio} = \frac{V_{\text{completed}}}{V_{\text{valid}}}$$

---

## 6. Versioned Gate Decision Engine

The gate evaluator (`backend/app/stability/gate.py`) evaluates computed metrics against predeclared policy thresholds:

### Policy `PMSG-POLICY-v1.0` (Standard Verification)
- **Minimum Coverage:** $\ge 80.0\%$
- **Maximum Reversal Rate:** $\le 15.0\%$
- **Minimum Top-1 Persistence:** $\ge 80.0\%$
- **Minimum Spearman Rank Correlation:** $\ge 0.70$
- **Execution Integrity:** 0 failed variants allowed.

### Decision Statuses:
- `PASS`: All required comparable variants evaluated, coverage $\ge 80\%$, persistence $\ge 80\%$, reversal rate $\le 15\%$, and 0 query failures. Deployment is **PERMITTED**.
- `WARNING`: Partial sensitivity detected (e.g. reversal rate $15-30\%$ or coverage $60-80\%$). Deployment requires manual review.
- `FAIL`: Mandatory stability condition violated (e.g. top category reversal or persistence $<80\%$). Deployment is **BLOCKED**.
- `HUMAN_REVIEW`: Incompatible question, unresolvable ambiguities, or zero executed variants. Deployment is **BLOCKED**.

---

## 7. Real Dataset Validation Example

Tested against `synthetic_road_accidents_prevention.csv` (2,500 records, 30 columns):

**Primary Finding:** *"Urban arterial has the highest proportion of recorded accidents at 26.13% (Denominator=907 recorded accidents)."*

### Multiverse Results:
- **Baseline (Primary):** Urban arterial ($26.13\%$, Rank 1, Highway Rank 2).
- **Missing Values (Unknown Category):** Urban arterial ($26.13\%$, Rank 1).
- **Denominator (All 2,500 Records):** Urban arterial ($9.48\%$, Rank 1).
- **Outlier Trim (99th percentile speed):** Urban arterial ($26.13\%$, Rank 1).
- **Category Merging (Merge $<10\%$):** Urban arterial ($26.13\%$, Rank 1).
- **Temporal Partitions (Early & Late 50%):** Urban arterial ($28.09\%$ & $24.24\%$, Rank 1).
- **Top-Category Persistence:** **$100.0\%$** across 8 comparable variants.
- **Spearman Rank Correlation:** **$0.979$**.
- **Conclusion Reversal Rate:** **$12.5\%$** (due to scale shift under unconditional denominator).
- **Gate Decision:** **`PASS`** (Deployment Permitted).

### Estimand Divergence Isolation:
When evaluating the alternative estimand *"Accident rate within road type"*:
- Residential is Rank 1 ($39.39\%$).
- Highway is Rank 2 ($37.20\%$).
- Urban arterial drops to Rank 6 ($34.30\%$).
**PMSG correctly isolated this variant into the `within_group_rate` family**, preventing an invalid averaging of fundamentally different research questions.
