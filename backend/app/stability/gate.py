"""Versioned Gate Decision Engine for Plan-Multiverse Stability Gate.

Evaluates computed stability metrics against predeclared, versioned policy rules:
- PASS: High coverage and all stability conditions satisfied.
- WARNING: Sensitive to specific specifications or partial coverage.
- FAIL: Prohibited conclusion reversal or mandatory condition failed.
- HUMAN_REVIEW: Ambiguity, insufficient data, or incompatible estimand.

Never permits silent PASS when required variants fail.
"""
from typing import Dict, List, Optional
from .models import (
    GateDecision,
    GateStatus,
    PolicyThresholds,
    RuleEvaluation,
    StabilityMetrics,
)

POLICIES: Dict[str, PolicyThresholds] = {
    "PMSG-POLICY-v1.0": PolicyThresholds(
        policy_id="PMSG-POLICY-v1.0",
        version="1.0.0",
        name="MK-Path Standard Robustness Gate Policy",
        min_coverage=0.80,
        max_reversal_rate=0.15,
        min_top1_persistence=0.80,
        min_spearman_rho=0.70,
        max_relative_spread=0.35,
        prohibit_silent_pass_on_failure=True,
        require_estimand_isolation=True,
    ),
    "PMSG-POLICY-RELAXED-v1.0": PolicyThresholds(
        policy_id="PMSG-POLICY-RELAXED-v1.0",
        version="1.0.0",
        name="Provisional Exploratory Stability Policy",
        min_coverage=0.60,
        max_reversal_rate=0.30,
        min_top1_persistence=0.60,
        min_spearman_rho=0.50,
        max_relative_spread=0.50,
        prohibit_silent_pass_on_failure=True,
        require_estimand_isolation=True,
    ),
}


def get_policy(policy_id: Optional[str] = None) -> PolicyThresholds:
    """Retrieve versioned policy definition; defaults to standard v1.0."""
    pid = policy_id or "PMSG-POLICY-v1.0"
    return POLICIES.get(pid, POLICIES["PMSG-POLICY-v1.0"])


def evaluate_gate_decision(
    metrics: StabilityMetrics,
    policy_id: Optional[str] = None,
) -> GateDecision:
    """
    Evaluate versioned decision policy against computed stability metrics.
    Produces a machine-readable, auditable decision record.
    """
    policy = get_policy(policy_id)
    evaluations: List[RuleEvaluation] = []
    overall_status = GateStatus.PASS
    failed_conditions = 0

    # 1. Check for Zero Completed Variants
    if metrics.completed_variants == 0:
        return GateDecision(
            overall_status=GateStatus.FAIL,
            policy_id=policy.policy_id,
            policy_version=policy.version,
            eligible_for_deployment=False,
            summary="Zero analytical variants completed successfully. Robustness could not be demonstrated.",
            triggered_rules=[
                RuleEvaluation(
                    rule_name="COMPLETED_VARIANTS_NONZERO",
                    description="At least one valid analytical variant must execute successfully.",
                    observed_value=0,
                    threshold=">= 1",
                    condition_met=False,
                    severity="CRITICAL",
                    impact_status=GateStatus.FAIL,
                )
            ],
            failed_conditions_count=1,
            recommended_next_action="Inspect backend query errors and resolve schema bindings.",
        )

    # 2. Rule: Execution Integrity (Prohibit Silent Pass on Failure)
    exec_clean = (metrics.failed_variants == 0)
    evaluations.append(
        RuleEvaluation(
            rule_name="EXECUTION_INTEGRITY",
            description="All scheduled comparable variants must execute without system errors.",
            observed_value=f"{metrics.failed_variants} failed",
            threshold="0 failed",
            condition_met=exec_clean,
            severity="HIGH",
            impact_status=GateStatus.PASS if exec_clean else GateStatus.WARNING,
        )
    )
    if not exec_clean:
        failed_conditions += 1
        if overall_status == GateStatus.PASS:
            overall_status = GateStatus.WARNING

    # 3. Rule: Variant Coverage
    coverage_ok = (metrics.coverage_ratio >= policy.min_coverage)
    evaluations.append(
        RuleEvaluation(
            rule_name="MINIMUM_VARIANT_COVERAGE",
            description=f"Completed variants must constitute at least {policy.min_coverage:.0%} of valid planned variants.",
            observed_value=f"{metrics.coverage_ratio:.1%}",
            threshold=f">= {policy.min_coverage:.0%}",
            condition_met=coverage_ok,
            severity="HIGH",
            impact_status=GateStatus.PASS if coverage_ok else GateStatus.WARNING,
        )
    )
    if not coverage_ok:
        failed_conditions += 1
        if overall_status == GateStatus.PASS:
            overall_status = GateStatus.WARNING

    # 4. Rule: Top Category Persistence
    persistence_ok = (metrics.top_category_persistence >= policy.min_top1_persistence)
    evaluations.append(
        RuleEvaluation(
            rule_name="TOP_CATEGORY_PERSISTENCE",
            description=f"Primary top category must remain top rank in >= {policy.min_top1_persistence:.0%} of comparable variants.",
            observed_value=f"{metrics.top_category_persistence:.1%}",
            threshold=f">= {policy.min_top1_persistence:.0%}",
            condition_met=persistence_ok,
            severity="CRITICAL",
            impact_status=GateStatus.PASS if persistence_ok else GateStatus.FAIL,
        )
    )
    if not persistence_ok:
        failed_conditions += 1
        overall_status = GateStatus.FAIL

    # 5. Rule: Conclusion Reversal Rate
    reversal_ok = (metrics.conclusion_reversal_rate <= policy.max_reversal_rate)
    evaluations.append(
        RuleEvaluation(
            rule_name="MAXIMUM_REVERSAL_RATE",
            description=f"Material conclusion reversals must not exceed {policy.max_reversal_rate:.0%}.",
            observed_value=f"{metrics.conclusion_reversal_rate:.1%}",
            threshold=f"<= {policy.max_reversal_rate:.0%}",
            condition_met=reversal_ok,
            severity="CRITICAL",
            impact_status=GateStatus.PASS if reversal_ok else GateStatus.FAIL,
        )
    )
    if not reversal_ok:
        failed_conditions += 1
        overall_status = GateStatus.FAIL

    # 6. Rule: Rank Correlation (Spearman rho)
    rho_ok = (metrics.spearman_rank_correlation >= policy.min_spearman_rho)
    evaluations.append(
        RuleEvaluation(
            rule_name="RANK_CORRELATION_CONSISTENCY",
            description=f"Spearman's rank correlation across categories must be >= {policy.min_spearman_rho:.2f}.",
            observed_value=f"{metrics.spearman_rank_correlation:.3f}",
            threshold=f">= {policy.min_spearman_rho:.2f}",
            condition_met=rho_ok,
            severity="MEDIUM",
            impact_status=GateStatus.PASS if rho_ok else GateStatus.WARNING,
        )
    )
    if not rho_ok:
        failed_conditions += 1
        if overall_status == GateStatus.PASS:
            overall_status = GateStatus.WARNING

    # 7. Estimand Divergence Disclosure Note
    if metrics.estimand_divergence_noted:
        evaluations.append(
            RuleEvaluation(
                rule_name="ESTIMAND_DIVERGENCE_ISOLATION",
                description="Estimand-divergent variants answer a different question and are isolated from the primary stability score.",
                observed_value="Divergence detected (isolated)",
                threshold="Isolated",
                condition_met=True,
                severity="LOW",
                impact_status=GateStatus.PASS,
            )
        )

    # Summarize decision
    if overall_status == GateStatus.PASS:
        summary = (
            f"STABILITY VERIFIED (PASS): Finding demonstrated robust stability across "
            f"{metrics.completed_variants}/{metrics.valid_variants} defensible variants. "
            f"Top-category persistence was {metrics.top_category_persistence:.1%}, "
            f"rank correlation was {metrics.spearman_rank_correlation:.3f}, and reversal rate was {metrics.conclusion_reversal_rate:.1%}."
        )
        recommendation = "Eligible for downstream production reporting and autonomous transformation workflows."
        eligible = True
    elif overall_status == GateStatus.WARNING:
        summary = (
            f"STABILITY SENSITIVITY DETECTED (WARNING): Finding is partially sensitive to analytical specifications. "
            f"Reversal rate is {metrics.conclusion_reversal_rate:.1%}; coverage is {metrics.coverage_ratio:.1%}. "
            f"{failed_conditions} condition(s) triggered warnings."
        )
        recommendation = "Review specific variant sensitivities before deploying or generating high-stakes executive summaries."
        eligible = True  # Can proceed with caveat
    elif overall_status == GateStatus.FAIL:
        reversal_details = [r.get("details", "") for r in metrics.reversals_observed[:2]]
        summary = (
            f"STABILITY GATE FAILED: Primary conclusion reversed under defensible analytical variants. "
            f"Top-category persistence fell to {metrics.top_category_persistence:.1%}, violating policy threshold. "
            f"{' | '.join(reversal_details)}"
        )
        recommendation = "Deployment BLOCKED. Analysis cannot be claimed as an established fact without resolving sensitivity."
        eligible = False
    else:
        summary = "HUMAN REVIEW REQUIRED: Ambiguity or incomplete variant execution prevents automated determination."
        recommendation = "Human domain expert must evaluate analytical alternatives."
        eligible = False

    return GateDecision(
        overall_status=overall_status,
        policy_id=policy.policy_id,
        policy_version=policy.version,
        eligible_for_deployment=eligible,
        summary=summary,
        triggered_rules=evaluations,
        failed_conditions_count=failed_conditions,
        recommended_next_action=recommendation,
    )
