# FIB-VG Testing & Verification Guide
## Automated Test Suite Architecture & Verification Protocols

This document details the automated test suite implemented in `backend/tests/test_fib_vg.py` for evaluating the Fault-Injection Benchmark for Verification Gates (FIB-VG) in MK-Path.

---

## 1. Test Suite Architecture

The test suite spans 24 automated test cases covering five distinct verification tiers:

```
backend/tests/test_fib_vg.py
├── Tier 1: Unit & Schema Verification (5 tests)
│   ├── test_scenario_catalog_integrity
│   ├── test_metric_formulas_exact
│   ├── test_zero_denominator_graceful_handling
│   ├── test_skipped_and_errored_scenarios_excluded_from_detection
│   └── test_release_policy_pass & test_release_policy_blocked_on_critical_escape
├── Tier 2: Real Component Execution & Containment (3 tests)
│   ├── test_engine_executes_real_verification_gate
│   ├── test_engine_executes_clean_control
│   └── test_critical_failure_blocks_ml_deployment_artifacts
├── Tier 3: Full Benchmark Run & Service Integration (1 test)
│   └── test_full_benchmark_run_service_execution
├── Tier 4: API Gateway Contract Verification (1 test)
│   └── test_api_benchmark_endpoints
├── Tier 5: 12 Mandatory Critical Regression Tests (12 tests)
│   ├── test_regression_01_critical_gate_returns_fail_and_deployment_blocked
│   ├── test_regression_02_verifier_failure_cannot_be_converted_to_pass
│   ├── test_regression_03_missing_mandatory_stage_cannot_silently_pass
│   ├── test_regression_04_missing_required_evidence_field_is_detected
│   ├── test_regression_05_persistence_failure_cannot_be_reported_as_durable_success
│   ├── test_regression_06_prohibited_local_storage_fallback_rejected
│   ├── test_regression_07_unauthorized_dataset_access_attempt_is_blocked
│   ├── test_regression_08_stale_result_cannot_be_reused_for_different_dataset
│   ├── test_regression_09_hardcoded_frontend_metric_cannot_override_authoritative_response
│   ├── test_regression_10_clean_valid_input_is_not_incorrectly_blocked
│   ├── test_regression_11_execution_error_does_not_count_as_successful_detection
│   └── test_regression_12_skipped_critical_scenario_prevents_fully_verified_release
└── Tier 6: Mutation Testing (1 test)
    └── test_mutation_detection_relaxed_threshold_caught
```

---

## 2. 12 Mandatory Critical Regression Matrix

The prompt mandates explicit automated verification of 12 critical failure modes:

| # | Regression Test Name | Fault Condition Tested | Expected System Behavior | Verification Status |
| :-: | :--- | :--- | :--- | :---: |
| **01** | `test_regression_01_critical_gate_returns_fail_and_deployment_blocked` | Critical schema & value failure injected | Gate returns `FAIL`, deployment artifact generation is blocked | **PASSED** |
| **02** | `test_regression_02_verifier_failure_cannot_be_converted_to_pass` | Tampering attempt to override gate outcome | Tampering detected; aggregate remains `FAIL` | **PASSED** |
| **03** | `test_regression_03_missing_mandatory_stage_cannot_silently_pass` | Mandatory verification stage omitted | Pipeline fails; missing stage flagged | **PASSED** |
| **04** | `test_regression_04_missing_required_evidence_field_is_detected` | Evidence payload omitted | Gate returns `FAIL`; missing evidence recorded | **PASSED** |
| **05** | `test_regression_05_persistence_failure_cannot_be_reported_as_durable_success` | Database connection or write failure | Persistence status reported as `UNCONFIRMED` | **PASSED** |
| **06** | `test_regression_06_prohibited_local_storage_fallback_rejected` | Local file fallback attempted | Local file fallback rejected; alert logged | **PASSED** |
| **07** | `test_regression_07_unauthorized_dataset_access_attempt_is_blocked` | Cross-tenant dataset access requested | Unauthorized access blocked (`HTTP 403` / `CROSS_TENANT_ACCESS_DENIED`) | **PASSED** |
| **08** | `test_regression_08_stale_result_cannot_be_reused_for_different_dataset` | Verification cert of Dataset A applied to B | Cryptographic fingerprint mismatch detected | **PASSED** |
| **09** | `test_regression_09_hardcoded_frontend_metric_cannot_override_authoritative_response` | Client attempts to submit fabricated metric | Hash mismatch caught; authoritative response enforced | **PASSED** |
| **10** | `test_regression_10_clean_valid_input_is_not_incorrectly_blocked` | Clean valid baseline dataset | Gate returns clean `PASS`; false alarm rate $= 0.0\%$ | **PASSED** |
| **11** | `test_regression_11_execution_error_does_not_count_as_successful_detection` | Test runner experiences crash or timeout | Marked `ERROR`; excluded from detected count | **PASSED** |
| **12** | `test_regression_12_skipped_critical_scenario_prevents_fully_verified_release` | Prerequisite missing on critical test | Scenario marked `SKIPPED`; release status becomes `RELEASE_BLOCKED` | **PASSED** |

---

## 3. Mutation Testing Protocol

In `test_mutation_detection_relaxed_threshold_caught`, a deliberately weakened verification policy is simulated:

1. **Clean Protection**: Verifier requires `['record_id', 'group_id', 'numerator_val', 'denominator_val', 'metric_value']`.
2. **Injected Mutation**: A compromised verifier weakens checks by requiring only `['record_id']`.
3. **Execution**: The benchmark runs `FIB-DAT-001` (missing `denominator_val`).
4. **Result**: The weakened verifier fails to detect the missing column. The benchmark's independent oracle flags that `observed_detection != expected_detection`, turning the scenario result to `FAIL` and asserting that the benchmark successfully detects verifier regressions.

---

## 4. Execution Instructions

### Running the Full Test Suite
To run the automated suite locally in the Python virtual environment:

```powershell
# From the project root (E:\MKPATH)
.\backend\.venv\Scripts\pytest backend\tests\test_fib_vg.py -v
```

### Execution Output
```
============================= test session starts =============================
platform win32 -- Python 3.10.7, pytest-9.1.1
collected 24 items

backend/tests/test_fib_vg.py::test_scenario_catalog_integrity PASSED     [  4%]
backend/tests/test_fib_vg.py::test_metric_formulas_exact PASSED          [  8%]
backend/tests/test_fib_vg.py::test_zero_denominator_graceful_handling PASSED [ 12%]
backend/tests/test_fib_vg.py::test_skipped_and_errored_scenarios_excluded_from_detection PASSED [ 16%]
backend/tests/test_fib_vg.py::test_release_policy_pass PASSED            [ 20%]
backend/tests/test_fib_vg.py::test_release_policy_blocked_on_critical_escape PASSED [ 25%]
backend/tests/test_fib_vg.py::test_engine_executes_real_verification_gate PASSED [ 29%]
backend/tests/test_fib_vg.py::test_engine_executes_clean_control PASSED  [ 33%]
backend/tests/test_fib_vg.py::test_critical_failure_blocks_ml_deployment_artifacts PASSED [ 37%]
backend/tests/test_fib_vg.py::test_full_benchmark_run_service_execution PASSED [ 41%]
backend/tests/test_fib_vg.py::test_api_benchmark_endpoints PASSED        [ 45%]
backend/tests/test_fib_vg.py::test_regression_01_critical_gate_returns_fail_and_deployment_blocked PASSED [ 50%]
backend/tests/test_fib_vg.py::test_regression_02_verifier_failure_cannot_be_converted_to_pass PASSED [ 54%]
backend/tests/test_fib_vg.py::test_regression_03_missing_mandatory_stage_cannot_silently_pass PASSED [ 58%]
backend/tests/test_fib_vg.py::test_regression_04_missing_required_evidence_field_is_detected PASSED [ 62%]
backend/tests/test_fib_vg.py::test_regression_05_persistence_failure_cannot_be_reported_as_durable_success PASSED [ 66%]
backend/tests/test_fib_vg.py::test_regression_06_prohibited_local_storage_fallback_rejected PASSED [ 70%]
backend/tests/test_fib_vg.py::test_regression_07_unauthorized_dataset_access_attempt_is_blocked PASSED [ 75%]
backend/tests/test_fib_vg.py::test_regression_08_stale_result_cannot_be_reused_for_different_dataset PASSED [ 79%]
backend/tests/test_fib_vg.py::test_regression_09_hardcoded_frontend_metric_cannot_override_authoritative_response PASSED [ 83%]
backend/tests/test_fib_vg.py::test_regression_10_clean_valid_input_is_not_incorrectly_blocked PASSED [ 87%]
backend/tests/test_fib_vg.py::test_regression_11_execution_error_does_not_count_as_successful_detection PASSED [ 91%]
backend/tests/test_fib_vg.py::test_regression_12_skipped_critical_scenario_prevents_fully_verified_release PASSED [ 95%]
backend/tests/test_fib_vg.py::test_mutation_detection_relaxed_threshold_caught PASSED [100%]

================= 24 passed in 147.02s =================
```
