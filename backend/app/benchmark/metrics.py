"""Deterministic metrics calculation engine for Fault-Injection Benchmark for Verification Gates.

Implements mathematically rigorous formulas with explicit numerators and denominators:
- Detection Rate: detected_faults / eligible_faults * 100
- False-Block Rate: clean_blocked / eligible_clean_controls * 100
- Critical Escape Rate: critical_passed / eligible_critical_faults * 100
- Diagnosis Accuracy: correct_diagnoses / eligible_diagnosis_scenarios * 100
- Audit Completeness: valid_audit_elements / total_required_elements * 100
- Deployment-Blocking Effectiveness: blocked_deployments / eligible_critical_blocked * 100
- Scenario Coverage: completed / total_registered * 100
"""
from typing import Dict, List, Optional
from .models import (
    BenchmarkAggregateMetrics,
    CategoryMetricBreakdown,
    ExecutionStatus,
    FaultCategory,
    ScenarioExecutionResult,
    Severity,
    SeverityMetricBreakdown,
)


def calculate_benchmark_metrics(
    results: List[ScenarioExecutionResult],
    total_registered: int,
) -> BenchmarkAggregateMetrics:
    """Calculate deterministic benchmark metrics across all executed scenario results."""
    # Partition outcomes
    completed_scenarios = [r for r in results if r.execution_status in (ExecutionStatus.PASS, ExecutionStatus.FAIL)]
    passed_scenarios = [r for r in results if r.execution_status == ExecutionStatus.PASS]
    failed_scenarios = [r for r in results if r.execution_status == ExecutionStatus.FAIL]
    error_scenarios = [r for r in results if r.execution_status == ExecutionStatus.ERROR]
    skipped_scenarios = [r for r in results if r.execution_status == ExecutionStatus.SKIPPED]
    blocked_scenarios = [r for r in results if r.execution_status == ExecutionStatus.BLOCKED]

    # Eligible fault scenarios (non-clean-control, completed without benchmark evaluation error)
    fault_results = [r for r in completed_scenarios if not r.is_clean_control]
    clean_results = [r for r in completed_scenarios if r.is_clean_control]

    # A. Detection Rate
    # Numerator: Completed fault scenarios where the real system detected the injected defect
    # Denominator: All eligible completed fault scenarios
    detected_faults = sum(1 for r in fault_results if r.observed_detection is True)
    eligible_faults = len(fault_results)
    detection_rate_pct = round((detected_faults / eligible_faults * 100.0), 2) if eligible_faults > 0 else None

    # B. False-Block Rate (Clean Controls)
    # Numerator: Clean control scenarios where the system incorrectly blocked the operation
    # Denominator: All eligible completed clean control scenarios
    clean_controls_blocked = sum(1 for r in clean_results if r.observed_deployment_blocked is True or r.observed_gate_decision.value == "FAIL")
    eligible_clean = len(clean_results)
    false_block_rate_pct = round((clean_controls_blocked / eligible_clean * 100.0), 2) if eligible_clean > 0 else None

    # C. Critical Escape Rate
    # A critical escape occurs when a critical fault is present, but the system allows the prohibited action
    # (i.e. fault not detected, gate declared PASS, or required deployment block was not enforced)
    critical_faults = [r for r in fault_results if r.severity == Severity.CRITICAL]
    critical_faults_passed = sum(
        1 for r in critical_faults
        if (r.observed_detection is False)
        or (r.observed_gate_decision.value == "PASS")
        or (r.expected_deployment_blocked is True and r.observed_deployment_blocked is False)
    )
    eligible_critical = len(critical_faults)
    critical_escape_rate_pct = round((critical_faults_passed / eligible_critical * 100.0), 2) if eligible_critical > 0 else None

    # D. Diagnosis Accuracy
    # Evaluates whether the system correctly identified the specific failure category or defect reason
    eligible_diagnosis = [r for r in fault_results if r.expected_diagnosis_category]
    correct_diagnoses = sum(1 for r in eligible_diagnosis if r.observed_diagnosis_matched is True)
    diagnosis_accuracy_pct = round((correct_diagnoses / len(eligible_diagnosis) * 100.0), 2) if eligible_diagnosis else None

    # E. Audit Completeness
    # Validates required audit elements across all evaluated scenarios
    total_audit_elements = len(results) * 3  # audit event logged, evidence references, clean context
    valid_audit_elements = sum(
        (1 if r.audit_event_logged else 0) +
        (1 if len(r.evidence_references) > 0 else 0) +
        (1 if r.cleanup_verified else 0)
        for r in results
    )
    audit_completeness_pct = round((valid_audit_elements / total_audit_elements * 100.0), 2) if total_audit_elements > 0 else None

    # F. Deployment-Blocking Effectiveness
    # Evaluates whether critical scenarios requiring deployment blocks actually blocked deployment
    deployment_critical_scenarios = [r for r in fault_results if r.expected_deployment_blocked is True]
    correctly_blocked = sum(1 for r in deployment_critical_scenarios if r.observed_deployment_blocked is True and r.downstream_action_blocked is True)
    eligible_blocked = len(deployment_critical_scenarios)
    deployment_blocking_rate_pct = round((correctly_blocked / eligible_blocked * 100.0), 2) if eligible_blocked > 0 else None

    # G. Coverage
    scenario_coverage_pct = round((len(completed_scenarios) / total_registered * 100.0), 2) if total_registered > 0 else 0.0

    # Breakdowns by Category
    category_breakdown: Dict[str, CategoryMetricBreakdown] = {}
    for cat in FaultCategory:
        cat_res = [r for r in results if r.category == cat]
        cat_completed = [r for r in cat_res if r.execution_status in (ExecutionStatus.PASS, ExecutionStatus.FAIL)]
        cat_faults = [r for r in cat_completed if not r.is_clean_control]
        cat_clean = [r for r in cat_completed if r.is_clean_control]
        
        c_det = sum(1 for r in cat_faults if r.observed_detection is True)
        c_det_rate = round((c_det / len(cat_faults) * 100.0), 2) if cat_faults else None
        
        c_blk = sum(1 for r in cat_clean if r.observed_deployment_blocked is True)
        c_fb_rate = round((c_blk / len(cat_clean) * 100.0), 2) if cat_clean else None

        category_breakdown[cat.value] = CategoryMetricBreakdown(
            category=cat,
            total_scenarios=len(cat_res),
            completed=len(cat_completed),
            passed=sum(1 for r in cat_res if r.execution_status == ExecutionStatus.PASS),
            failed=sum(1 for r in cat_res if r.execution_status == ExecutionStatus.FAIL),
            errored=sum(1 for r in cat_res if r.execution_status == ExecutionStatus.ERROR),
            skipped=sum(1 for r in cat_res if r.execution_status == ExecutionStatus.SKIPPED),
            blocked=sum(1 for r in cat_res if r.execution_status == ExecutionStatus.BLOCKED),
            detected_faults=c_det,
            eligible_faults=len(cat_faults),
            detection_rate=c_det_rate,
            clean_controls=len(cat_clean),
            clean_blocked=c_blk,
            false_block_rate=c_fb_rate,
        )

    # Breakdowns by Severity
    severity_breakdown: Dict[str, SeverityMetricBreakdown] = {}
    for sev in Severity:
        sev_res = [r for r in results if r.severity == sev]
        sev_completed = [r for r in sev_res if r.execution_status in (ExecutionStatus.PASS, ExecutionStatus.FAIL)]
        sev_escapes = sum(
            1 for r in sev_completed
            if not r.is_clean_control and (r.observed_detection is False or r.observed_gate_decision.value == "PASS")
        )

        severity_breakdown[sev.value] = SeverityMetricBreakdown(
            severity=sev,
            total_scenarios=len(sev_res),
            completed=len(sev_completed),
            passed=sum(1 for r in sev_res if r.execution_status == ExecutionStatus.PASS),
            failed=sum(1 for r in sev_res if r.execution_status == ExecutionStatus.FAIL),
            critical_escapes=sev_escapes,
        )

    return BenchmarkAggregateMetrics(
        total_registered_scenarios=total_registered,
        completed_scenarios=len(completed_scenarios),
        passed_scenarios=len(passed_scenarios),
        failed_scenarios=len(failed_scenarios),
        error_scenarios=len(error_scenarios),
        skipped_scenarios=len(skipped_scenarios),
        blocked_scenarios=len(blocked_scenarios),
        detected_faults=detected_faults,
        eligible_fault_scenarios=eligible_faults,
        detection_rate_pct=detection_rate_pct,
        clean_controls_blocked=clean_controls_blocked,
        eligible_clean_controls=eligible_clean,
        false_block_rate_pct=false_block_rate_pct,
        critical_faults_passed=critical_faults_passed,
        eligible_critical_faults=eligible_critical,
        critical_escape_rate_pct=critical_escape_rate_pct,
        correct_diagnoses=correct_diagnoses,
        eligible_diagnosis_scenarios=len(eligible_diagnosis),
        diagnosis_accuracy_pct=diagnosis_accuracy_pct,
        valid_audit_elements=valid_audit_elements,
        total_required_audit_elements=total_audit_elements,
        audit_completeness_pct=audit_completeness_pct,
        correctly_blocked_deployments=correctly_blocked,
        eligible_critical_blocked_scenarios=eligible_blocked,
        deployment_blocking_rate_pct=deployment_blocking_rate_pct,
        scenario_coverage_pct=scenario_coverage_pct,
        category_breakdown=category_breakdown,
        severity_breakdown=severity_breakdown,
    )
