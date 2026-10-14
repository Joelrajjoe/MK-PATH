"""Comprehensive unit and integration test suite for Plan-Multiverse Stability Gate (PMSG).

Validates:
1. Deterministic, bounded variant generation.
2. Incompatible operator handling and estimand separation.
3. Known-answer mathematical correctness on independent test fixtures.
4. Spearman rho rank correlation with ties handling.
5. Gate decision logic (PASS, WARNING, FAIL, HUMAN_REVIEW).
6. Non-silent pass on execution failure.
7. End-to-end integration with DuckDB execution on real dataset.
"""
import pytest
from typing import Dict, List

from backend.app.stability.models import (
    AnalysisPlanSpec,
    AnalysisType,
    CategoryPolicy,
    GateStatus,
    MissingValuePolicy,
    OutlierPolicy,
    TimeWindowPolicy,
    VariantClass,
    VariantExecutionResult,
)
from backend.app.stability.generator import generate_variants
from backend.app.stability.metrics import (
    _compute_fractional_ranks,
    calculate_spearman_rho,
    evaluate_stability,
)
from backend.app.stability.gate import evaluate_gate_decision, get_policy


def _create_test_plan() -> AnalysisPlanSpec:
    return AnalysisPlanSpec(
        analysis_id="test_plan_001",
        project_id="test_proj",
        dataset_id="test_ds",
        analysis_question="Which category has the highest proportion of target events?",
        analysis_type=AnalysisType.CATEGORY_PROPORTION,
        target_variable="is_event",
        grouping_column="category",
        metric_type="proportion",
        population_filter="is_event = 'Yes'",
        denominator_definition="valid_population_total",
        missing_value_policy=MissingValuePolicy.EXCLUDE_MISSING,
        outlier_policy=OutlierPolicy.NONE,
        category_policy=CategoryPolicy.PRESERVE_ALL,
        time_window=TimeWindowPolicy.ALL_TIME,
        assumptions=["Independent observations"],
        required_columns=["category", "is_event"],
        estimand_family="population_share",
    )


# --------------------------------------------------------------------------
# 1. Variant Generation Tests
# --------------------------------------------------------------------------

def test_variant_generation_determinism():
    """Ensure identical inputs generate bit-for-bit identical variant lists."""
    plan = _create_test_plan()
    cols = ["category", "is_event", "speed", "event_date"]
    types = {"category": "varchar", "is_event": "varchar", "speed": "int", "event_date": "varchar"}

    v1 = generate_variants(plan, cols, types, max_variants=12)
    v2 = generate_variants(plan, cols, types, max_variants=12)

    assert len(v1) == len(v2)
    for a, b in zip(v1, v2):
        assert a.variant_id == b.variant_id
        assert a.name == b.name
        assert a.variant_class == b.variant_class
        assert a.estimand_family == b.estimand_family
        assert a.parameters == b.parameters


def test_variant_budget_enforcement():
    """Ensure variant generator never exceeds configured budget limit."""
    plan = _create_test_plan()
    cols = ["category", "is_event", "speed", "event_date"]
    types = {"category": "varchar", "is_event": "varchar", "speed": "int", "event_date": "varchar"}

    for budget in [1, 3, 5, 8]:
        v = generate_variants(plan, cols, types, max_variants=budget)
        assert len(v) == budget
        # Primary plan must always be the first item
        assert v[0].is_primary is True
        assert v[0].variant_id == "var_primary_base"


def test_incompatible_operator_detection():
    """Ensure traffic exposure denominator without exposure columns is marked INVALID."""
    plan = _create_test_plan()
    cols = ["category", "is_event"]  # No exposure, speed, or date
    types = {"category": "varchar", "is_event": "varchar"}

    variants = generate_variants(plan, cols, types, max_variants=15)
    
    # Check traffic exposure variant
    exp_var = next((v for v in variants if "exposure" in v.variant_id), None)
    assert exp_var is not None
    assert exp_var.compatibility_status == "INCOMPATIBLE"
    assert exp_var.variant_class == VariantClass.INVALID
    assert "traffic exposure" in exp_var.incompatibility_reason.lower()


def test_estimand_change_separation():
    """Ensure within-group occurrence rate is classified as ESTIMAND_CHANGE."""
    plan = _create_test_plan()
    cols = ["category", "is_event", "speed"]
    types = {"category": "varchar", "is_event": "varchar", "speed": "int"}

    variants = generate_variants(plan, cols, types, max_variants=15)
    rate_var = next((v for v in variants if v.variant_id == "var_denom_within_group_rate"), None)
    
    assert rate_var is not None
    assert rate_var.variant_class == VariantClass.ESTIMAND_CHANGE
    assert rate_var.estimand_family == "within_group_rate"
    assert rate_var.estimand_family != plan.estimand_family


# --------------------------------------------------------------------------
# 2. Known-Answer Mathematical Fixture Tests
# --------------------------------------------------------------------------

def test_fractional_ranks_calculation():
    """Test standard fractional ranking handling ties."""
    # Values: [50, 30, 30, 10]
    # In descending order: 50 is rank 1, two 30s tie for ranks 2 and 3 -> rank 2.5 each, 10 is rank 4.
    vals = [50.0, 30.0, 30.0, 10.0]
    ranks = _compute_fractional_ranks(vals, reverse=True)
    assert ranks == [1.0, 2.5, 2.5, 4.0]

    # All identical: [20, 20, 20] -> ranks 1, 2, 3 -> avg rank 2.0 each
    ranks_tied = _compute_fractional_ranks([20.0, 20.0, 20.0], reverse=True)
    assert ranks_tied == [2.0, 2.0, 2.0]


def test_spearman_rho_known_values():
    """Test Spearman rank correlation against known mathematical values."""
    # Identical ranks -> rho = 1.0
    r1 = [1.0, 2.0, 3.0, 4.0]
    r2 = [1.0, 2.0, 3.0, 4.0]
    assert calculate_spearman_rho(r1, r2) == 1.0

    # Perfectly inverted ranks -> rho = -1.0
    r_rev = [4.0, 3.0, 2.0, 1.0]
    assert calculate_spearman_rho(r1, r_rev) == -1.0

    # Tied ranks correlation
    ra = [1.0, 2.5, 2.5, 4.0]
    rb = [1.0, 2.0, 3.0, 4.0]
    rho = calculate_spearman_rho(ra, rb)
    assert 0.90 < rho < 1.0


def test_stability_metrics_on_fixture():
    """
    Evaluate stability calculation on a small, hand-calculated mock fixture.
    Primary: Group A is top (value 0.60, Group B is 0.40)
    Variant 1: Group A is top (value 0.58, Group B is 0.42) -> agrees
    Variant 2: Group A is top (value 0.55, Group B is 0.45) -> agrees
    Variant 3: Group B is top (value 0.52, Group A is 0.48) -> reversal!
    """
    primary = VariantExecutionResult(
        variant_id="var_primary_base",
        variant_name="Primary",
        variant_class=VariantClass.IMPLEMENTATION,
        estimand_family="pop_share",
        status="SUCCESS",
        sample_size=100,
        metric_values={"A": 0.60, "B": 0.40},
        rankings=[{"group": "A", "rank": 1, "metric_value": 0.60}, {"group": "B", "rank": 2, "metric_value": 0.40}],
        top_category="A",
        top_value=0.60,
    )
    v1 = VariantExecutionResult(
        variant_id="var_1",
        variant_name="Variant 1",
        variant_class=VariantClass.SPECIFICATION,
        estimand_family="pop_share",
        status="SUCCESS",
        sample_size=100,
        metric_values={"A": 0.58, "B": 0.42},
        rankings=[{"group": "A", "rank": 1, "metric_value": 0.58}, {"group": "B", "rank": 2, "metric_value": 0.42}],
        top_category="A",
        top_value=0.58,
    )
    v2 = VariantExecutionResult(
        variant_id="var_2",
        variant_name="Variant 2",
        variant_class=VariantClass.SPECIFICATION,
        estimand_family="pop_share",
        status="SUCCESS",
        sample_size=100,
        metric_values={"A": 0.55, "B": 0.45},
        rankings=[{"group": "A", "rank": 1, "metric_value": 0.55}, {"group": "B", "rank": 2, "metric_value": 0.45}],
        top_category="A",
        top_value=0.55,
    )
    v3 = VariantExecutionResult(
        variant_id="var_3",
        variant_name="Variant 3",
        variant_class=VariantClass.SPECIFICATION,
        estimand_family="pop_share",
        status="SUCCESS",
        sample_size=100,
        metric_values={"A": 0.48, "B": 0.52},
        rankings=[{"group": "B", "rank": 1, "metric_value": 0.52}, {"group": "A", "rank": 2, "metric_value": 0.48}],
        top_category="B",
        top_value=0.52,
    )

    metrics, _ = evaluate_stability([primary, v1, v2, v3], primary_variant_id="var_primary_base")

    # 3 out of 4 variants have A as top -> top persistence = 3/4 = 0.75
    assert metrics.top_category_persistence == 0.75
    # 1 reversal observed out of 4 -> reversal rate = 0.25
    assert metrics.conclusion_reversal_rate == 0.25
    assert len(metrics.reversals_observed) == 1
    assert metrics.reversals_observed[0]["observed_top"] == "B"
    # Effect size of A: primary=0.60, v1=0.58, v2=0.55, v3=0.48 -> min=0.48, max=0.60, range=0.12
    assert pytest.approx(metrics.effect_size_min, rel=1e-3) == 0.48
    assert pytest.approx(metrics.effect_size_max, rel=1e-3) == 0.60
    assert pytest.approx(metrics.effect_size_range, rel=1e-3) == 0.12


# --------------------------------------------------------------------------
# 3. Gate Decision Engine Tests
# --------------------------------------------------------------------------

def test_gate_decision_pass():
    """Verify that high persistence and low reversal produce PASS."""
    from backend.app.stability.models import StabilityMetrics
    metrics = StabilityMetrics(
        comparable_family="pop_share",
        direction_stability=1.0,
        top_category_persistence=1.0,
        spearman_rank_correlation=0.98,
        effect_size_min=0.24,
        effect_size_max=0.28,
        effect_size_range=0.04,
        effect_size_relative_range=0.15,
        conclusion_reversal_rate=0.0,
        reversals_observed=[],
        planned_variants=8,
        valid_variants=8,
        completed_variants=8,
        failed_variants=0,
        incompatible_variants=0,
        skipped_variants=0,
        coverage_ratio=1.0,
        estimand_variants_count=1,
        estimand_divergence_noted=False,
    )

    decision = evaluate_gate_decision(metrics, policy_id="PMSG-POLICY-v1.0")
    assert decision.overall_status == GateStatus.PASS
    assert decision.eligible_for_deployment is True
    assert decision.failed_conditions_count == 0


def test_gate_decision_fail_on_reversal():
    """Verify that excessive conclusion reversal triggers mandatory FAIL and blocks deployment."""
    from backend.app.stability.models import StabilityMetrics
    metrics = StabilityMetrics(
        comparable_family="pop_share",
        direction_stability=0.60,
        top_category_persistence=0.60,  # Below 0.80 threshold
        spearman_rank_correlation=0.65,
        effect_size_min=0.10,
        effect_size_max=0.35,
        effect_size_range=0.25,
        effect_size_relative_range=0.80,
        conclusion_reversal_rate=0.40,  # Above 0.15 threshold
        reversals_observed=[{"details": "Top category shifted under outlier trim"}],
        planned_variants=8,
        valid_variants=8,
        completed_variants=8,
        failed_variants=0,
        incompatible_variants=0,
        skipped_variants=0,
        coverage_ratio=1.0,
        estimand_variants_count=1,
        estimand_divergence_noted=True,
    )

    decision = evaluate_gate_decision(metrics, policy_id="PMSG-POLICY-v1.0")
    assert decision.overall_status == GateStatus.FAIL
    assert decision.eligible_for_deployment is False
    assert decision.failed_conditions_count > 0
    # Must report reversal in explanation
    assert "STABILITY GATE FAILED" in decision.summary


def test_gate_prohibits_silent_pass_on_failure():
    """Ensure that any failed execution prevents a silent PASS."""
    from backend.app.stability.models import StabilityMetrics
    metrics = StabilityMetrics(
        comparable_family="pop_share",
        direction_stability=1.0,
        top_category_persistence=1.0,
        spearman_rank_correlation=1.0,
        effect_size_min=0.25,
        effect_size_max=0.25,
        effect_size_range=0.0,
        effect_size_relative_range=0.0,
        conclusion_reversal_rate=0.0,
        reversals_observed=[],
        planned_variants=8,
        valid_variants=8,
        completed_variants=6,
        failed_variants=2,  # 2 variants crashed
        incompatible_variants=0,
        skipped_variants=0,
        coverage_ratio=0.75,  # Below 0.80 threshold
        estimand_variants_count=0,
        estimand_divergence_noted=False,
    )

    decision = evaluate_gate_decision(metrics, policy_id="PMSG-POLICY-v1.0")
    # Must NEVER be PASS
    assert decision.overall_status != GateStatus.PASS
    assert decision.overall_status in (GateStatus.WARNING, GateStatus.FAIL)


# --------------------------------------------------------------------------
# 4. API & Real Dataset Integration Tests
# --------------------------------------------------------------------------

def test_api_policies():
    """Verify GET /api/stability/policies returns versioned policies."""
    from fastapi.testclient import TestClient
    from backend.app.main import app

    with TestClient(app) as client:
        res = client.get("/api/stability/policies")
        assert res.status_code == 200
        data = res.json()
        assert "policies" in data
        assert any(p["policy_id"] == "PMSG-POLICY-v1.0" for p in data["policies"])
        assert data["default_policy_id"] == "PMSG-POLICY-v1.0"


def test_api_plan_and_preview():
    """Verify /api/stability/plan and /api/stability/variants/preview on accident dataset."""
    from fastapi.testclient import TestClient
    from backend.app.main import app

    dataset_id = "2b1bea2f53614aae81af671a84b8eb52"
    project_id = "f926eadaadfb4e73ba593ad1a1bd78c6"

    with TestClient(app) as client:
        # 1. Propose plan
        p_res = client.post("/api/stability/plan", json={
            "dataset_id": dataset_id,
            "project_id": project_id,
            "business_goal": "Accident distribution across road categories"
        })
        if p_res.status_code == 503:
            pytest.skip("MongoDB Atlas not reachable in test environment")

        assert p_res.status_code == 200
        plan = p_res.json()["plan"]
        assert plan["target_variable"] == "accident_occurred"
        assert plan["grouping_column"] == "road_type"

        # 2. Preview variants
        prev_res = client.post("/api/stability/variants/preview", json={
            "dataset_id": dataset_id,
            "plan": plan,
            "max_variants": 10
        })
        assert prev_res.status_code == 200
        prev_data = prev_res.json()
        assert "variants" in prev_data
        assert prev_data["summary"]["total_variants"] <= 10
        assert prev_data["summary"]["comparable_variants"] > 0


def test_api_stability_run_real_dataset():
    """Execute end-to-end PMSG run via POST /api/stability/run against real DuckDB dataset."""
    from fastapi.testclient import TestClient
    from backend.app.main import app

    dataset_id = "2b1bea2f53614aae81af671a84b8eb52"
    project_id = "f926eadaadfb4e73ba593ad1a1bd78c6"

    with TestClient(app) as client:
        run_res = client.post("/api/stability/run", json={
            "dataset_id": dataset_id,
            "project_id": project_id,
            "policy_id": "PMSG-POLICY-v1.0"
        })
        if run_res.status_code == 503:
            pytest.skip("MongoDB Atlas not reachable in test environment")

        assert run_res.status_code == 200
        run_data = run_res.json()
        assert "run_id" in run_data
        run_id = run_data["run_id"]
        assert run_data["gate_decision"]["overall_status"] in ("PASS", "WARNING")
        assert len(run_data["execution_results"]) > 0
        assert run_data["stability_metrics"]["completed_variants"] > 0
        assert run_data["stability_metrics"]["top_category_persistence"] >= 0.80

        # Retrieve run from GET /api/stability/runs/{run_id}
        get_res = client.get(f"/api/stability/runs/{run_id}")
        assert get_res.status_code == 200
        assert get_res.json()["run_id"] == run_id

        # Verify gate inclusion in central /api/verification/gates
        gates_res = client.get(f"/api/verification/gates?project_id={project_id}")
        assert gates_res.status_code == 200
        gates_data = gates_res.json()
        gate_ids = [g["gate_id"] for g in gates_data["summary"]["results"]]
        assert "plan_multiverse_stability" in gate_ids


def test_pmsg_fail_blocks_verification_deployment():
    """Verify that a PMSG FAIL status blocks deployment in central verification engine."""
    from backend.app.verification.engine import run_verification_gates

    project_id = "test_block_proj"
    run_id = "test_block_run"
    context = {
        "data_quality_score": 95.0,
        "temporal_leakage_risk": "LOW",
        "pmsg_status": "FAIL",
        "pmsg_metrics": {
            "top_category_persistence": 0.50,
            "conclusion_reversal_rate": 0.40
        },
        "pmsg_reason": "Primary conclusion reversed in 40% of defensible variants."
    }

    report = run_verification_gates(project_id, run_id, context)
    assert report.deployment_status == "BLOCKED"
    assert report.summary.overall_status == "BLOCKED"

    # Find PMSG gate result
    pmsg_gate = next((g for g in report.summary.results if g.gate_id == "plan_multiverse_stability"), None)
    assert pmsg_gate is not None
    assert pmsg_gate.status == "FAIL"
    assert pmsg_gate.severity == "CRITICAL"
    assert "Resolve analytical instability before deployment" in pmsg_gate.recommendation


def test_blocked_deployment_prevents_ml_artifacts(tmp_path, monkeypatch):
    """Verify that when verification report is BLOCKED, ML deployment artifacts are NOT generated."""
    from backend.app.engineering.ml_engineer import generate_deployment_artifacts
    from backend.app import config

    # Mock artifacts dir to tmp_path
    monkeypatch.setattr(config.settings, "ARTIFACTS_DIR", tmp_path)

    project_id = "proj_blocked_ml"
    run_id = "run_blocked_ml"
    verif_report = {
        "deployment_status": "BLOCKED",
        "summary": {
            "failed_gates": 1,
            "results": [{"gate_id": "plan_multiverse_stability", "status": "FAIL"}]
        }
    }
    model_info = {"model_name": "rf_classifier", "path": "non_existent.pkl"}
    feature_schema = {"feature1": "float"}

    res = generate_deployment_artifacts(project_id, run_id, verif_report, model_info, feature_schema)
    assert res["status"] == "BLOCKED"
    assert "Verification report deployment_status != READY" in res["reason"]

    # Verify diagnostic report was created and model API was NOT created
    artifact_dir = tmp_path / project_id / run_id
    diag_file = artifact_dir / "DIAGNOSTIC_REPORT.md"
    assert diag_file.exists()
    assert "Deployment Blocked" in diag_file.read_text(encoding="utf-8")

    api_file = artifact_dir / "api" / "main.py"
    assert not api_file.exists()


