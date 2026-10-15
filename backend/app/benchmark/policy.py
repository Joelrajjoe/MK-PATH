"""Versioned release gate policies for Fault-Injection Benchmark for Verification Gates.

Defines the authoritative decision criteria for whether a system passes release gates
and is approved for downstream production deployment.
"""
from typing import Dict, List
from .models import (
    BenchmarkAggregateMetrics,
    BenchmarkReleaseStatus,
    ReleaseGateDecision,
    ReleasePolicySpec,
)

DEFAULT_RELEASE_POLICY = ReleasePolicySpec(
    policy_id="FIB-RELEASE-POLICY-v1.0",
    policy_name="Production Verification Gate Release Policy",
    max_critical_escapes=0,
    min_deployment_blocking_rate_pct=100.0,
    max_false_block_rate_pct=0.0,
    min_detection_rate_pct=95.0,
    min_audit_completeness_pct=90.0,
    max_execution_errors=0,
    require_zero_unresolved_critical_scenarios=True,
)

POLICIES: Dict[str, ReleasePolicySpec] = {
    DEFAULT_RELEASE_POLICY.policy_id: DEFAULT_RELEASE_POLICY,
}


def evaluate_release_decision(
    metrics: BenchmarkAggregateMetrics,
    policy: ReleasePolicySpec = DEFAULT_RELEASE_POLICY,
) -> ReleaseGateDecision:
    """Evaluate whether benchmark metrics satisfy the versioned release policy."""
    violations: List[str] = []
    recommendations: List[str] = []

    # 1. Zero Critical Escapes
    critical_escapes = metrics.critical_faults_passed
    if critical_escapes > policy.max_critical_escapes:
        violations.append(
            f"Critical Escapes ({critical_escapes}) exceeded allowed threshold ({policy.max_critical_escapes}). "
            f"Dangerous faults escaped verification gates without detection."
        )
        recommendations.append("Strengthen gate assertions and prevent unverified passes.")

    # 2. Deployment-Blocking Effectiveness
    if metrics.deployment_blocking_rate_pct is not None:
        if metrics.deployment_blocking_rate_pct < policy.min_deployment_blocking_rate_pct:
            violations.append(
                f"Deployment-blocking effectiveness ({metrics.deployment_blocking_rate_pct}%) is below required "
                f"threshold ({policy.min_deployment_blocking_rate_pct}%). Some critical failures did not block downstream deployment."
            )
            recommendations.append("Ensure ML Engineer Agent and deployment hooks verify report.deployment_status == 'READY'.")

    # 3. False-Block Rate (Clean Controls)
    if metrics.false_block_rate_pct is not None:
        if metrics.false_block_rate_pct > policy.max_false_block_rate_pct:
            violations.append(
                f"False-block rate on clean controls ({metrics.false_block_rate_pct}%) exceeds maximum allowable "
                f"threshold ({policy.max_false_block_rate_pct}%). Valid work is being incorrectly blocked."
            )
            recommendations.append("Calibrate sensitivity thresholds on non-anomalous baseline datasets.")

    # 4. Minimum Detection Rate
    if metrics.detection_rate_pct is not None:
        if metrics.detection_rate_pct < policy.min_detection_rate_pct:
            violations.append(
                f"Overall fault detection rate ({metrics.detection_rate_pct}%) is below minimum standard "
                f"({policy.min_detection_rate_pct}%)."
            )
            recommendations.append("Investigate uncovered failure modes and add target verifiers.")

    # 5. Audit Completeness
    if metrics.audit_completeness_pct is not None:
        if metrics.audit_completeness_pct < policy.min_audit_completeness_pct:
            violations.append(
                f"Audit completeness ({metrics.audit_completeness_pct}%) is below mandatory threshold "
                f"({policy.min_audit_completeness_pct}%). Evidence references or audit records were omitted."
            )
            recommendations.append("Ensure every verification gate emits structured audit events with evidence envelopes.")

    # 6. Execution Errors
    if metrics.error_scenarios > policy.max_execution_errors:
        violations.append(
            f"Benchmark encountered {metrics.error_scenarios} unresolved execution errors. "
            f"Results cannot be verified reliably."
        )
        recommendations.append("Resolve system timeouts or environment unhandled exceptions.")

    passed_policy = len(violations) == 0
    overall_status = BenchmarkReleaseStatus.RELEASE_APPROVED if passed_policy else BenchmarkReleaseStatus.RELEASE_BLOCKED

    summary = (
        f"Benchmark Release Gate Approved: All {metrics.completed_scenarios} scenarios passed safety criteria "
        f"with 0 critical escapes."
        if passed_policy
        else f"Benchmark Release Gate Blocked: {len(violations)} safety policy violation(s) identified."
    )

    return ReleaseGateDecision(
        policy_id=policy.policy_id,
        overall_status=overall_status,
        passed_policy_criteria=passed_policy,
        summary=summary,
        violations=violations,
        recommendations=recommendations,
    )
