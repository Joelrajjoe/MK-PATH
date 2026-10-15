# FIB-VG Metric Definitions & Deterministic Formulas
## Mathematical Specification for Verification Gate Benchmarks

This document formalizes the mathematical equations, eligible subsets, numerators, denominators, and boundary condition behaviors implemented in `backend/app/benchmark/metrics.py`.

All calculations are **100% deterministic local computation**. LLMs, heuristics, or probabilistic approximations are strictly forbidden from altering or computing benchmark metrics.

---

## 1. Scenario Subsets & Eligibility Rules

Let $S$ denote the set of all scenario execution results in a benchmark run:

$$S = \{s_1, s_2, \dots, s_N\}$$

Each scenario result $s$ contains:
- $c(s) \in \{\text{DATA\_INTEGRITY}, \text{ANALYTICAL\_CORRECTNESS}, \dots\}$
- $v(s) \in \{\text{CRITICAL}, \text{HIGH}, \text{MEDIUM}, \text{LOW}\}$
- $e(s) \in \{\text{PASS}, \text{FAIL}, \text{ERROR}, \text{SKIPPED}, \text{BLOCKED}\}$
- $d_{\text{exp}}(s) \in \{\text{True}, \text{False}\}$ (Expected detection)
- $d_{\text{obs}}(s) \in \{\text{True}, \text{False}\}$ (Observed detection)
- $g_{\text{exp}}(s), g_{\text{obs}}(s) \in \{\text{PASS}, \text{FAIL}, \text{ERROR}, \text{SKIPPED}, \text{BLOCKED}\}$
- $b_{\text{exp}}(s), b_{\text{obs}}(s) \in \{\text{True}, \text{False}\}$ (Deployment blocked)
- $\text{diag}_{\text{exp}}(s), \text{diag}_{\text{obs}}(s)$ (Diagnosis codes)
- $a(s) \in [0.0, 1.0]$ (Audit completeness fraction)

### Completed Set ($S_{\text{completed}}$)
A scenario is completed if its execution status is either `PASS` or `FAIL`:

$$S_{\text{completed}} = \{s \in S \mid e(s) \in \{\text{PASS}, \text{FAIL}\}\}$$

*Crucial rule*: Scenarios with $e(s) \in \{\text{ERROR}, \text{SKIPPED}, \text{BLOCKED}\}$ are excluded from completed evaluation sets and **never** counted as detections.

---

## 2. Core Benchmark Formulas

### A. Fault Detection Rate ($R_{\text{det}}$)

Measures the proportion of injected faults that were correctly detected by the target verification controls.

$$\text{Eligible Fault Scenarios: } S_{\text{fault}} = \{s \in S_{\text{completed}} \mid d_{\text{exp}}(s) = \text{True}\}$$

$$\text{Correctly Detected Faults: } S_{\text{det}} = \{s \in S_{\text{fault}} \mid d_{\text{obs}}(s) = \text{True}\}$$

$$R_{\text{det}} = \begin{cases} 
\frac{|S_{\text{det}}|}{|S_{\text{fault}}|} \times 100\% & \text{if } |S_{\text{fault}}| > 0 \\ 
100.0\% & \text{if } |S_{\text{fault}}| = 0 
\end{cases}$$

- **Numerator**: $|S_{\text{det}}|$ (Count of correctly detected injected faults)
- **Denominator**: $|S_{\text{fault}}|$ (Total completed fault scenarios expecting detection)
- **Benchmark Run Baseline**: $34 / 34 = 100.0\%$

---

### B. Clean Control False-Block Rate ($R_{\text{false\_block}}$)

Measures the proportion of valid, unmutated control scenarios that were incorrectly blocked or flagged as failures by over-aggressive gates.

$$\text{Eligible Clean Controls: } S_{\text{clean}} = \{s \in S_{\text{completed}} \mid d_{\text{exp}}(s) = \text{False}\}$$

$$\text{Incorrectly Blocked Clean: } S_{\text{blocked\_clean}} = \{s \in S_{\text{clean}} \mid g_{\text{obs}}(s) \in \{\text{FAIL}, \text{BLOCKED}\} \lor d_{\text{obs}}(s) = \text{True}\}$$

$$R_{\text{false\_block}} = \begin{cases} 
\frac{|S_{\text{blocked\_clean}}|}{|S_{\text{clean}}|} \times 100\% & \text{if } |S_{\text{clean}}| > 0 \\ 
0.0\% & \text{if } |S_{\text{clean}}| = 0 
\end{cases}$$

- **Numerator**: $|S_{\text{blocked\_clean}}|$ (Clean controls incorrectly rejected)
- **Denominator**: $|S_{\text{clean}}|$ (Total completed clean control scenarios)
- **Benchmark Run Baseline**: $0 / 8 = 0.0\%$

---

### C. Critical Escape Rate ($R_{\text{esc}}$)

Measures the proportion of critical fault scenarios that either went undetected, were incorrectly permitted to pass verification gates, or failed to block deployment.

$$\text{Eligible Critical Faults: } S_{\text{crit}} = \{s \in S_{\text{completed}} \mid v(s) = \text{CRITICAL} \land d_{\text{exp}}(s) = \text{True}\}$$

$$\text{Critical Escapes: } S_{\text{esc}} = \{s \in S_{\text{crit}} \mid d_{\text{obs}}(s) = \text{False} \lor g_{\text{obs}}(s) = \text{PASS} \lor (b_{\text{exp}}(s) = \text{True} \land b_{\text{obs}}(s) = \text{False})\}$$

$$R_{\text{esc}} = \begin{cases} 
\frac{|S_{\text{esc}}|}{|S_{\text{crit}}|} \times 100\% & \text{if } |S_{\text{crit}}| > 0 \\ 
0.0\% & \text{if } |S_{\text{crit}}| = 0 
\end{cases}$$

- **Numerator**: $|S_{\text{esc}}|$ (Critical faults incorrectly allowed to escape or pass)
- **Denominator**: $|S_{\text{crit}}|$ (Total completed critical fault scenarios)
- **Benchmark Run Baseline**: $0 / 12 = 0.0\%$ (Zero critical escapes)

---

### D. Diagnosis Accuracy ($R_{\text{diag}}$)

Measures whether the verifier correctly pinpointed the specific fault category and diagnosis code rather than issuing a generic unclassified failure.

$$\text{Eligible Diagnosable: } S_{\text{diag}} = \{s \in S_{\text{completed}} \mid \text{diag}_{\text{exp}}(s) \neq \text{"NONE"}\}$$

$$\text{Correct Diagnoses: } S_{\text{diag\_ok}} = \{s \in S_{\text{diag}} \mid \text{diag}_{\text{obs}}(s) = \text{diag}_{\text{exp}}(s)\}$$

$$R_{\text{diag}} = \begin{cases} 
\frac{|S_{\text{diag\_ok}}|}{|S_{\text{diag}}|} \times 100\% & \text{if } |S_{\text{diag}}| > 0 \\ 
100.0\% & \text{if } |S_{\text{diag}}| = 0 
\end{cases}$$

- **Numerator**: $|S_{\text{diag\_ok}}|$
- **Denominator**: $|S_{\text{diag}}|$
- **Benchmark Run Baseline**: $34 / 34 = 100.0\%$

---

### E. Audit Completeness Rate ($R_{\text{audit}}$)

Measures the presence and integrity of mandatory audit attributes: `audit_completeness`, `evidence_references`, `run_id`, and `hash_validity`.

$$R_{\text{audit}} = \begin{cases} 
\frac{\sum_{s \in S_{\text{completed}}} a(s)}{|S_{\text{completed}}|} \times 100\% & \text{if } |S_{\text{completed}}| > 0 \\ 
100.0\% & \text{if } |S_{\text{completed}}| = 0 
\end{cases}$$

- **Benchmark Run Baseline**: $42 / 42 = 100.0\%$

---

### F. Deployment-Blocking Effectiveness ($R_{\text{deploy\_block}}$)

Measures whether critical failures correctly halted downstream artifact generation and containerization.

$$\text{Critical Deployment-Blocking Scenarios: } S_{\text{deploy\_crit}} = \{s \in S_{\text{completed}} \mid b_{\text{exp}}(s) = \text{True}\}$$

$$\text{Successfully Blocked: } S_{\text{blocked}} = \{s \in S_{\text{deploy\_crit}} \mid b_{\text{obs}}(s) = \text{True}\}$$

$$R_{\text{deploy\_block}} = \begin{cases} 
\frac{|S_{\text{blocked}}|}{|S_{\text{deploy\_crit}}|} \times 100\% & \text{if } |S_{\text{deploy\_crit}}| > 0 \\ 
100.0\% & \text{if } |S_{\text{deploy\_crit}}| = 0 
\end{cases}$$

- **Numerator**: $|S_{\text{blocked}}|$ (12 critical scenarios blocked)
- **Denominator**: $|S_{\text{deploy\_crit}}|$ (12 critical scenarios requiring block)
- **Benchmark Run Baseline**: $12 / 12 = 100.0\%$

---

### G. Scenario Coverage ($R_{\text{cov}}$)

$$R_{\text{cov}} = \frac{|S_{\text{completed}}|}{|S_{\text{registered}}|} \times 100\% = \frac{42}{42} \times 100\% = 100.0\%$$

---

## 3. Boundary & Error Handling Rules

1. **Zero Denominator Robustness**: If a filter produces zero eligible cases (e.g., zero clean controls in a custom subset), the system returns a safe identity default ($0.0\%$ for false blocks and escapes, $100.0\%$ for detection and diagnosis) and logs a `ZERO_DENOMINATOR_GUARD` diagnostic note.
2. **Error Isolation**: Scenarios that abort due to environmental timeout or unhandled exception are marked `execution_status='ERROR'` and are explicitly accounted for in `execution_errors_count`. They can never boost detection rates.
3. **Skipped Cases**: Scenarios with unsatisfied prerequisites are labeled `SKIPPED`. If any mandatory scenario is skipped, the release gate decision transitions from `RELEASE_APPROVED` to `RELEASE_BLOCKED`.
