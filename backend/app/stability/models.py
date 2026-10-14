"""Pydantic data models and schemas for Plan-Multiverse Stability Gate (PMSG).

Enforces strictly typed and versioned representation for primary analysis plans,
variant specifications, execution provenance, stability metrics, and gate decisions.
"""
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class AnalysisType(str, Enum):
    CATEGORY_PROPORTION = "category_proportion"
    GROUP_COMPARISON = "group_comparison"
    METRIC_ESTIMATION = "metric_estimation"
    RATE_ESTIMATION = "rate_estimation"


class VariantClass(str, Enum):
    IMPLEMENTATION = "IMPLEMENTATION"          # Different safe implementations of identical estimand
    SPECIFICATION = "SPECIFICATION"            # Reasonable alternative choices preserving core estimand
    ESTIMAND_CHANGE = "ESTIMAND_CHANGE"        # Answers a materially different research question
    INVALID = "INVALID"                        # Cannot be evaluated with current schema/assumptions


class GateStatus(str, Enum):
    PASS = "PASS"
    WARNING = "WARNING"
    FAIL = "FAIL"
    HUMAN_REVIEW = "HUMAN_REVIEW"


class MissingValuePolicy(str, Enum):
    EXCLUDE_MISSING = "exclude_missing"
    INCLUDE_UNKNOWN = "include_unknown"


class OutlierPolicy(str, Enum):
    NONE = "none"
    QUANTILE_TRIM_99 = "quantile_trim_99"
    STD_TRIM_3 = "std_trim_3"


class CategoryPolicy(str, Enum):
    PRESERVE_ALL = "preserve_all"
    MERGE_RARE_THRESHOLD = "merge_rare_threshold"


class TimeWindowPolicy(str, Enum):
    ALL_TIME = "all_time"
    EARLY_WINDOW = "early_window"
    LATE_WINDOW = "late_window"


class AnalysisPlanSpec(BaseModel):
    """Canonical specification of primary analysis estimand."""
    analysis_id: str = Field(description="Unique identifier for this analysis specification")
    project_id: str
    dataset_id: str
    dataset_version: str = "v1"
    dataset_fingerprint: str = ""
    analysis_question: str
    analysis_type: AnalysisType = AnalysisType.CATEGORY_PROPORTION
    target_variable: str
    grouping_column: str
    metric_type: str = "proportion"  # proportion, rate, sum, mean, count
    population_filter: Optional[str] = None  # e.g. "accident_occurred = 'Yes'"
    denominator_definition: str = "valid_population_total"
    missing_value_policy: MissingValuePolicy = MissingValuePolicy.EXCLUDE_MISSING
    outlier_policy: OutlierPolicy = OutlierPolicy.NONE
    category_policy: CategoryPolicy = CategoryPolicy.PRESERVE_ALL
    time_window: TimeWindowPolicy = TimeWindowPolicy.ALL_TIME
    date_column: Optional[str] = None
    assumptions: List[str] = Field(default_factory=list)
    required_columns: List[str] = Field(default_factory=list)
    estimand_family: str = "population_share"
    predeclared_stability_policy_id: str = "PMSG-POLICY-v1.0"
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    created_by: str = "analyst_agent"


class AnalysisVariant(BaseModel):
    """Specification of a single analytical alternative."""
    variant_id: str
    name: str
    variant_class: VariantClass
    operator_category: str  # base, missing_values, denominator, outlier, category, time_window
    estimand_family: str
    description: str
    is_primary: bool = False
    parameters: Dict[str, Any] = Field(default_factory=dict)
    compatibility_status: str = "COMPATIBLE"  # COMPATIBLE, INCOMPATIBLE
    incompatibility_reason: Optional[str] = None


class GroupMetricResult(BaseModel):
    group: str
    numerator: float
    denominator: float
    metric_value: float
    rank: int


class VariantExecutionResult(BaseModel):
    """Provable execution record of a variant against real dataset."""
    variant_id: str
    variant_name: str
    variant_class: VariantClass
    estimand_family: str
    status: str  # SUCCESS, FAILED, SKIPPED, INCOMPATIBLE
    sample_size: int = 0
    excluded_rows: int = 0
    exclusion_reasons: Dict[str, int] = Field(default_factory=dict)
    metric_values: Dict[str, float] = Field(default_factory=dict)
    rankings: List[Dict[str, Any]] = Field(default_factory=list)
    top_category: Optional[str] = None
    top_value: Optional[float] = None
    primary_finding_summary: str = ""
    query_sql: str = ""
    query_hash: str = ""
    duration_ms: float = 0.0
    error_message: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class StabilityMetrics(BaseModel):
    """Deterministic mathematical measures of finding stability."""
    comparable_family: str
    direction_stability: float  # [0.0, 1.0]
    top_category_persistence: float  # [0.0, 1.0]
    spearman_rank_correlation: float  # [-1.0, 1.0]
    effect_size_min: float
    effect_size_max: float
    effect_size_range: float
    effect_size_relative_range: float
    conclusion_reversal_rate: float  # [0.0, 1.0]
    reversals_observed: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Coverage metrics
    planned_variants: int = 0
    valid_variants: int = 0
    completed_variants: int = 0
    failed_variants: int = 0
    incompatible_variants: int = 0
    skipped_variants: int = 0
    coverage_ratio: float = 0.0  # completed / valid
    
    # Estimand separation disclosure
    estimand_variants_count: int = 0
    estimand_divergence_noted: bool = False


class PolicyThresholds(BaseModel):
    policy_id: str
    version: str
    name: str
    min_coverage: float = 0.80
    max_reversal_rate: float = 0.15
    min_top1_persistence: float = 0.80
    min_spearman_rho: float = 0.70
    max_relative_spread: float = 0.35
    prohibit_silent_pass_on_failure: bool = True
    require_estimand_isolation: bool = True


class RuleEvaluation(BaseModel):
    rule_name: str
    description: str
    observed_value: Any
    threshold: Any
    condition_met: bool
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW
    impact_status: GateStatus


class GateDecision(BaseModel):
    """Versioned verification decision for PMSG."""
    overall_status: GateStatus
    policy_id: str
    policy_version: str
    eligible_for_deployment: bool
    summary: str
    triggered_rules: List[RuleEvaluation] = Field(default_factory=list)
    failed_conditions_count: int = 0
    recommended_next_action: str
    evaluated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class PmsgRunRecord(BaseModel):
    """Full persistent execution and verification record for MongoDB Atlas."""
    run_id: str
    project_id: str
    dataset_id: str
    dataset_version: str = "v1"
    dataset_fingerprint: str = ""
    question: str
    plan: AnalysisPlanSpec
    variants: List[AnalysisVariant]
    execution_results: List[VariantExecutionResult]
    stability_metrics: StabilityMetrics
    estimand_divergent_results: List[VariantExecutionResult] = Field(default_factory=list)
    estimand_metrics: Optional[StabilityMetrics] = None
    gate_decision: GateDecision
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    created_by: str = "pmsg_engine"
    duration_total_ms: float = 0.0
