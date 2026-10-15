"""Strongly typed data models and schemas for Fault-Injection Benchmark for Verification Gates (FIB-VG).

Defines versioned, audited schemas for:
- Scenario catalog specifications
- Controlled fault injections and execution contexts
- Expected outcomes vs observed outcomes (independent oracle)
- Deterministic benchmark metrics with explicit numerators and denominators
- Release gate policies and deployment-blocking records
"""
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ExecutionStatus(str, Enum):
    PASS = "PASS"          # Observed behavior matched independent expected outcome
    FAIL = "FAIL"          # Observed behavior violated independent expected outcome
    ERROR = "ERROR"        # Benchmark could not reliably evaluate scenario (e.g. timeout, unhandled exception)
    SKIPPED = "SKIPPED"    # Declared precondition was not satisfied
    BLOCKED = "BLOCKED"    # Prerequisite safety gate or isolation check prevented requested operation
    PENDING = "PENDING"
    RUNNING = "RUNNING"


class FaultCategory(str, Enum):
    DATA_INTEGRITY = "DATA_INTEGRITY"
    ANALYTICAL_CORRECTNESS = "ANALYTICAL_CORRECTNESS"
    SEMANTIC_GOVERNANCE = "SEMANTIC_GOVERNANCE"
    AGENT_ORCHESTRATION = "AGENT_ORCHESTRATION"
    VERIFICATION_GATE_BYPASS = "VERIFICATION_GATE_BYPASS"
    STORAGE_PERSISTENCE = "STORAGE_PERSISTENCE"
    FRONTEND_API_INTEGRITY = "FRONTEND_API_INTEGRITY"
    AUDIT_EVIDENCE = "AUDIT_EVIDENCE"


class Severity(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class GateOutcome(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    WARNING = "WARNING"
    HUMAN_REVIEW = "HUMAN_REVIEW"
    BLOCKED = "BLOCKED"


class BenchmarkReleaseStatus(str, Enum):
    RELEASE_APPROVED = "RELEASE_APPROVED"
    RELEASE_BLOCKED = "RELEASE_BLOCKED"
    CONDITIONAL_REVIEW = "CONDITIONAL_REVIEW"


class ScenarioSpec(BaseModel):
    """Immutable, versioned specification of a benchmark scenario."""
    scenario_id: str
    catalog_version: str = "FIB-CATALOG-v1.0"
    category: FaultCategory
    severity: Severity
    title: str
    fault_description: str
    target_component: str
    preconditions: List[str] = Field(default_factory=list)
    is_clean_control: bool = False
    clean_control_id: Optional[str] = None
    
    # Independent Expected Outcomes (The Oracle)
    expected_detection: bool
    expected_gate_decision: GateOutcome
    expected_diagnosis_category: str
    expected_deployment_blocked: bool
    expected_audit_event: str
    requires_diagnosis: bool = True
    timeout_seconds: float = 10.0


class ScenarioExecutionResult(BaseModel):
    """Detailed observation and outcome of an individual scenario execution."""
    scenario_id: str
    category: FaultCategory
    severity: Severity
    title: str
    fault_description: str
    is_clean_control: bool = False
    clean_control_id: Optional[str] = None

    # Injection State
    injection_status: str  # APPLIED, CLEAN, ERROR, SKIPPED
    injection_details: Dict[str, Any] = Field(default_factory=dict)

    # Independent Oracle Expectations
    expected_detection: bool
    expected_gate_decision: GateOutcome
    expected_diagnosis_category: str
    expected_deployment_blocked: bool
    expected_audit_event: str

    # Real System Observations
    observed_detection: bool
    observed_gate_decision: GateOutcome
    observed_diagnosis: Optional[str] = None
    observed_diagnosis_matched: bool = False
    observed_deployment_blocked: bool = False
    downstream_action_blocked: bool = False

    # Evidence & Audit
    evidence_references: List[str] = Field(default_factory=list)
    audit_event_logged: bool = False
    audit_completeness: float = 100.0  # 0 to 100%

    # Final Outcome Evaluation
    execution_status: ExecutionStatus  # PASS, FAIL, ERROR, SKIPPED, BLOCKED
    failure_reason: Optional[str] = None
    cleanup_verified: bool = True
    duration_ms: float = 0.0
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class CategoryMetricBreakdown(BaseModel):
    category: FaultCategory
    total_scenarios: int
    completed: int
    passed: int
    failed: int
    errored: int
    skipped: int
    blocked: int
    detected_faults: int
    eligible_faults: int
    detection_rate: Optional[float] = None
    clean_controls: int
    clean_blocked: int
    false_block_rate: Optional[float] = None


class SeverityMetricBreakdown(BaseModel):
    severity: Severity
    total_scenarios: int
    completed: int
    passed: int
    failed: int
    critical_escapes: int


class BenchmarkAggregateMetrics(BaseModel):
    """Strictly deterministic aggregate metrics with explicit numerators and denominators."""
    total_registered_scenarios: int
    completed_scenarios: int
    passed_scenarios: int
    failed_scenarios: int
    error_scenarios: int
    skipped_scenarios: int
    blocked_scenarios: int

    # A. Detection Rate
    detected_faults: int
    eligible_fault_scenarios: int
    detection_rate_pct: Optional[float] = None

    # B. False-Block Rate (Clean Controls)
    clean_controls_blocked: int
    eligible_clean_controls: int
    false_block_rate_pct: Optional[float] = None

    # C. Critical Escape Rate
    critical_faults_passed: int
    eligible_critical_faults: int
    critical_escape_rate_pct: Optional[float] = None

    # D. Diagnosis Accuracy
    correct_diagnoses: int
    eligible_diagnosis_scenarios: int
    diagnosis_accuracy_pct: Optional[float] = None

    # E. Audit Completeness
    valid_audit_elements: int
    total_required_audit_elements: int
    audit_completeness_pct: Optional[float] = None

    # F. Deployment-Blocking Effectiveness
    correctly_blocked_deployments: int
    eligible_critical_blocked_scenarios: int
    deployment_blocking_rate_pct: Optional[float] = None

    # G. Coverage
    scenario_coverage_pct: float

    # Breakdowns
    category_breakdown: Dict[str, CategoryMetricBreakdown] = Field(default_factory=dict)
    severity_breakdown: Dict[str, SeverityMetricBreakdown] = Field(default_factory=dict)


class ReleasePolicySpec(BaseModel):
    """Configurable, versioned release gate policy specification."""
    policy_id: str = "FIB-RELEASE-POLICY-v1.0"
    policy_name: str = "Production Safety & Deployment Verification Gate Policy"
    max_critical_escapes: int = 0
    min_deployment_blocking_rate_pct: float = 100.0
    max_false_block_rate_pct: float = 0.0
    min_detection_rate_pct: float = 95.0
    min_audit_completeness_pct: float = 90.0
    max_execution_errors: int = 0
    require_zero_unresolved_critical_scenarios: bool = True


class ReleaseGateDecision(BaseModel):
    """Authoritative decision regarding release readiness based on benchmark metrics."""
    policy_id: str
    overall_status: BenchmarkReleaseStatus
    passed_policy_criteria: bool
    summary: str
    violations: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    evaluated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class BenchmarkRunRecord(BaseModel):
    """Complete, versioned benchmark run envelope persisted in MongoDB Atlas."""
    run_id: str
    project_id: str
    benchmark_version: str = "1.0.0"
    scenario_catalog_version: str = "FIB-CATALOG-v1.0"
    policy_id: str = "FIB-RELEASE-POLICY-v1.0"
    started_at: str
    completed_at: str
    execution_status: ExecutionStatus
    persistence_status: str = "CONFIRMED"
    environment_fingerprint: Dict[str, Any] = Field(default_factory=dict)
    dataset_fingerprint: Optional[str] = None
    created_by: str = "automated_benchmark_system"

    # Full scenario results and deterministic metrics
    scenario_results: List[ScenarioExecutionResult] = Field(default_factory=list)
    aggregate_metrics: BenchmarkAggregateMetrics
    gate_decision: ReleaseGateDecision
    audit_integrity_status: str = "VALID"
