"""Deterministic mathematical stability metrics calculation.

Calculates:
1. Direction Stability & Top-Category Persistence
2. Rank Correlation (Spearman rho with ties handling)
3. Effect-Size Variation (Min, Max, Absolute Range, Relative Range)
4. Conclusion Reversal Rate & Reversal Explanations
5. Variant Coverage Ratios (Planned, Valid, Completed, Failed, Incompatible)
6. Estimand Divergence Isolation (Prevents conflating different research questions)
"""
import math
from typing import Any, Dict, List, Optional, Tuple

from .models import (
    StabilityMetrics,
    VariantClass,
    VariantExecutionResult,
)


def _compute_fractional_ranks(values: List[float], reverse: bool = True) -> List[float]:
    """
    Compute fractional ranks (1-based) handling ties correctly according to standard statistical rules.
    If reverse=True, higher values receive rank 1.
    """
    n = len(values)
    if n == 0:
        return []

    # Sort with original indices
    indexed = sorted(enumerate(values), key=lambda x: x[1], reverse=reverse)
    ranks = [0.0] * n

    i = 0
    while i < n:
        j = i
        while j < n - 1 and math.isclose(indexed[j][1], indexed[j + 1][1], rel_tol=1e-9, abs_tol=1e-9):
            j += 1
        # Ties from i to j get average rank
        # 1-based ranks from (i+1) to (j+1)
        avg_rank = sum(range(i + 1, j + 2)) / (j - i + 1)
        for k in range(i, j + 1):
            ranks[indexed[k][0]] = avg_rank
        i = j + 1

    return ranks


def calculate_spearman_rho(ranks_a: List[float], ranks_b: List[float]) -> float:
    """
    Calculate Pearson correlation between two sets of fractional ranks.
    Guarantees mathematically exact Spearman rho with arbitrary ties.
    """
    n = len(ranks_a)
    if n < 2:
        return 1.0

    mean_a = sum(ranks_a) / n
    mean_b = sum(ranks_b) / n

    numerator = sum((a - mean_a) * (b - mean_b) for a, b in zip(ranks_a, ranks_b))
    var_a = sum((a - mean_a) ** 2 for a in ranks_a)
    var_b = sum((b - mean_b) ** 2 for b in ranks_b)

    denominator = math.sqrt(var_a * var_b)
    if denominator == 0.0 or math.isclose(denominator, 0.0, abs_tol=1e-12):
        return 1.0 if math.isclose(var_a, var_b, abs_tol=1e-9) else 0.0

    rho = numerator / denominator
    return max(-1.0, min(1.0, round(rho, 6)))


def evaluate_stability(
    all_results: List[VariantExecutionResult],
    primary_variant_id: str = "var_primary_base",
) -> Tuple[StabilityMetrics, Optional[StabilityMetrics]]:
    """
    Compute deterministic stability metrics across executed variants.
    Strictly isolates comparable variants from estimand-divergent variants.
    """
    # 1. Locate primary execution result
    primary_res = next((r for r in all_results if r.variant_id == primary_variant_id), None)
    if not primary_res or primary_res.status != "SUCCESS":
        # Fall back to first successful variant
        primary_res = next((r for r in all_results if r.status == "SUCCESS"), None)

    if not primary_res:
        # No successful executions exist
        empty_metrics = StabilityMetrics(
            comparable_family="none",
            direction_stability=0.0,
            top_category_persistence=0.0,
            spearman_rank_correlation=0.0,
            effect_size_min=0.0,
            effect_size_max=0.0,
            effect_size_range=0.0,
            effect_size_relative_range=0.0,
            conclusion_reversal_rate=1.0,
            reversals_observed=[{"reason": "No variant completed successfully."}],
            planned_variants=len(all_results),
            valid_variants=len([r for r in all_results if r.status != "INCOMPATIBLE"]),
            completed_variants=0,
            failed_variants=len([r for r in all_results if r.status == "FAILED"]),
            incompatible_variants=len([r for r in all_results if r.status == "INCOMPATIBLE"]),
            skipped_variants=0,
            coverage_ratio=0.0,
            estimand_variants_count=0,
            estimand_divergence_noted=False,
        )
        return empty_metrics, None

    primary_family = primary_res.estimand_family
    primary_top = primary_res.top_category
    primary_val = primary_res.top_value or 0.0

    # 2. Partition results into comparable vs estimand-divergent
    comparable_results: List[VariantExecutionResult] = []
    estimand_results: List[VariantExecutionResult] = []

    for r in all_results:
        if r.variant_class == VariantClass.ESTIMAND_CHANGE or r.estimand_family != primary_family:
            estimand_results.append(r)
        else:
            comparable_results.append(r)

    # 3. Analyze coverage within comparable family
    planned_comparable = len(comparable_results)
    valid_comparable = len([r for r in comparable_results if r.status != "INCOMPATIBLE"])
    completed_comparable = [r for r in comparable_results if r.status == "SUCCESS"]
    failed_comparable = len([r for r in comparable_results if r.status == "FAILED"])
    incompatible_comparable = len([r for r in comparable_results if r.status == "INCOMPATIBLE"])
    coverage_ratio = len(completed_comparable) / valid_comparable if valid_comparable > 0 else 0.0

    # 4. Compute metrics across completed comparable variants
    top_matches = 0
    spearman_scores: List[float] = []
    top_cat_values: List[float] = []
    reversals: List[Dict[str, Any]] = []

    # Map primary groups to ranks
    primary_rank_map = {item["group"]: item["rank"] for item in primary_res.rankings}

    for var_res in completed_comparable:
        # A. Direction / Top category agreement
        is_top_match = (var_res.top_category == primary_top)
        if is_top_match:
            top_matches += 1
        else:
            reversals.append({
                "variant_id": var_res.variant_id,
                "variant_name": var_res.variant_name,
                "reversal_type": "TOP_CATEGORY_SHIFT",
                "observed_top": var_res.top_category,
                "expected_top": primary_top,
                "observed_value": var_res.top_value,
                "details": f"Top category shifted from '{primary_top}' to '{var_res.top_category}'."
            })

        # Track value of primary top category under this variant
        v_top_val = var_res.metric_values.get(primary_top)
        if v_top_val is not None:
            top_cat_values.append(v_top_val)

            # Check for practical magnitude reversal (> 25% relative shift)
            if primary_val > 0.0:
                rel_diff = abs(v_top_val - primary_val) / primary_val
                if rel_diff > 0.25 and is_top_match:
                    reversals.append({
                        "variant_id": var_res.variant_id,
                        "variant_name": var_res.variant_name,
                        "reversal_type": "EFFECT_MAGNITUDE_SHIFT",
                        "observed_value": v_top_val,
                        "expected_value": primary_val,
                        "relative_difference": round(rel_diff, 4),
                        "details": f"Metric value for '{primary_top}' shifted by {rel_diff:.1%} (exceeds 25% stability bound)."
                    })

        # B. Spearman rank correlation over mutual groups
        common_groups = [g for g in primary_rank_map if g in var_res.metric_values]
        if len(common_groups) >= 2:
            p_ranks = [float(primary_rank_map[g]) for g in common_groups]
            # Calculate fractional ranks for variant
            v_vals = [var_res.metric_values[g] for g in common_groups]
            v_ranks = _compute_fractional_ranks(v_vals, reverse=True)
            rho = calculate_spearman_rho(p_ranks, v_ranks)
            spearman_scores.append(rho)

    total_completed = len(completed_comparable)
    if total_completed > 0:
        top_persistence = top_matches / total_completed
        direction_stability = top_persistence  # for proportion ranking, top category agreement is direction
        mean_spearman = sum(spearman_scores) / len(spearman_scores) if spearman_scores else 1.0
        reversal_rate = len(reversals) / total_completed
    else:
        top_persistence = 0.0
        direction_stability = 0.0
        mean_spearman = 0.0
        reversal_rate = 1.0

    # Dispersion
    if top_cat_values:
        eff_min = min(top_cat_values)
        eff_max = max(top_cat_values)
        eff_range = eff_max - eff_min
        eff_rel_range = (eff_range / primary_val) if primary_val > 0.0 else 0.0
    else:
        eff_min = primary_val
        eff_max = primary_val
        eff_range = 0.0
        eff_rel_range = 0.0

    # 5. Check for estimand divergence
    estimand_divergence = False
    for est_r in estimand_results:
        if est_r.status == "SUCCESS" and est_r.top_category != primary_top:
            estimand_divergence = True
            break

    comparable_metrics = StabilityMetrics(
        comparable_family=primary_family,
        direction_stability=round(direction_stability, 4),
        top_category_persistence=round(top_persistence, 4),
        spearman_rank_correlation=round(mean_spearman, 4),
        effect_size_min=round(eff_min, 6),
        effect_size_max=round(eff_max, 6),
        effect_size_range=round(eff_range, 6),
        effect_size_relative_range=round(eff_rel_range, 4),
        conclusion_reversal_rate=round(reversal_rate, 4),
        reversals_observed=reversals,
        planned_variants=planned_comparable,
        valid_variants=valid_comparable,
        completed_variants=total_completed,
        failed_variants=failed_comparable,
        incompatible_variants=incompatible_comparable,
        skipped_variants=0,
        coverage_ratio=round(coverage_ratio, 4),
        estimand_variants_count=len(estimand_results),
        estimand_divergence_noted=estimand_divergence,
    )

    # 6. Secondary metrics for estimand variants (if any)
    estimand_metrics = None
    if estimand_results:
        est_completed = [r for r in estimand_results if r.status == "SUCCESS"]
        if est_completed:
            est_top = est_completed[0].top_category
            est_matches = sum(1 for r in est_completed if r.top_category == est_top)
            estimand_metrics = StabilityMetrics(
                comparable_family=est_completed[0].estimand_family,
                direction_stability=round(est_matches / len(est_completed), 4),
                top_category_persistence=round(est_matches / len(est_completed), 4),
                spearman_rank_correlation=1.0,
                effect_size_min=round(est_completed[0].top_value or 0.0, 6),
                effect_size_max=round(est_completed[0].top_value or 0.0, 6),
                effect_size_range=0.0,
                effect_size_relative_range=0.0,
                conclusion_reversal_rate=0.0,
                reversals_observed=[],
                planned_variants=len(estimand_results),
                valid_variants=len([r for r in estimand_results if r.status != "INCOMPATIBLE"]),
                completed_variants=len(est_completed),
                failed_variants=len([r for r in estimand_results if r.status == "FAILED"]),
                incompatible_variants=len([r for r in estimand_results if r.status == "INCOMPATIBLE"]),
                skipped_variants=0,
                coverage_ratio=round(len(est_completed) / len(estimand_results), 4),
                estimand_variants_count=len(estimand_results),
                estimand_divergence_noted=estimand_divergence,
            )

    return comparable_metrics, estimand_metrics
