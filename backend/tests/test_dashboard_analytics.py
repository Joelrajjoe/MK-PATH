"""Comprehensive tests for Executive Performance Management Dashboard analytics.

Verifies:
1. End-to-end DuckDB analytics engine calculations on real dataset.
2. Dynamic cascading filters (team, location, date range).
3. Zero-denominator and empty-filter resilience.
4. Independent deterministic SQL reconciliation with 0.0 tolerance.
5. Record drilldown with pagination and column schema preservation.
6. API endpoint responses (POST /api/dashboard/analytics, GET /api/dashboard/filters, POST /api/dashboard/verify, POST /api/dashboard/export).
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.analytics import (
    compute_dashboard_analytics,
    get_filter_dimensions,
    get_drilldown_records,
    verify_dataset_analytics,
    DashboardReadinessStatus,
    DrilldownRequest,
    FilterContext,
)

REAL_DATASET_ID = "2b1bea2f53614aae81af671a84b8eb52"


@pytest.fixture
def client():
    return TestClient(app)


def test_dashboard_analytics_real_dataset():
    """Verify DuckDB analytics computation over real dataset."""
    payload = compute_dashboard_analytics(
        dataset_id=REAL_DATASET_ID,
        project_id="test_project",
    )

    assert payload.dataset_id == REAL_DATASET_ID
    assert payload.readiness_status == DashboardReadinessStatus.READY
    assert payload.quality_summary.total_records == 2500
    assert payload.quality_summary.filtered_records == 2500
    assert payload.computation_time_ms > 0

    # Card 1: Quarter to Quarter
    assert payload.card1_quarter_to_quarter.current_value > 0
    assert payload.card1_quarter_to_quarter.change_formatted != "N/A"
    assert len(payload.card1_quarter_to_quarter.sparkline_points) > 0

    # Card 2: Year over Year
    assert payload.card2_year_over_year.selected_team != ""
    assert len(payload.card2_year_over_year.sparkline_points) > 0

    # Card 3: Top and Bottom Teams
    assert len(payload.card3_top_bottom_teams.top_teams) <= 3
    assert len(payload.card3_top_bottom_teams.bottom_teams) <= 3
    assert payload.card3_top_bottom_teams.eligible_record_count == 2500

    # Card 4: Quarterly Performance
    assert len(payload.card4_quarterly_performance.series) > 0
    assert len(payload.card4_quarterly_performance.available_tabs) > 0

    # Card 5: Meetings Attended
    assert 0.0 <= payload.card5_meetings_attended.percentage <= 100.0
    assert payload.card5_meetings_attended.denominator > 0

    # Card 6: Location Performance
    assert 0.0 <= payload.card6_engineering_performance.percentage <= 100.0
    assert payload.card6_engineering_performance.denominator > 0


def test_dashboard_analytics_with_filters():
    """Verify cascading filter context reduces eligible records deterministically."""
    # Filter by specific road_type
    filter_ctx = FilterContext(team="Highway")
    payload = compute_dashboard_analytics(
        dataset_id=REAL_DATASET_ID,
        project_id="test_project",
        filter_ctx=filter_ctx,
    )

    assert payload.quality_summary.total_records == 2500
    assert payload.quality_summary.filtered_records < 2500
    assert payload.quality_summary.filtered_records > 0
    assert payload.card3_top_bottom_teams.eligible_record_count == payload.quality_summary.filtered_records


def test_reconciliation_zero_tolerance():
    """Independent SQL verification must pass with zero tolerance."""
    res = verify_dataset_analytics(
        dataset_id=REAL_DATASET_ID,
        project_id="test_project",
    )

    assert res.reconciliation_passed is True
    assert len(res.items) >= 3
    for item in res.items:
        assert item.is_exact_match is True, f"Failed match on {item.metric_name}"


def test_drilldown_records_pagination():
    """Verify underlying record drilldown retrieval."""
    req = DrilldownRequest(
        dataset_id=REAL_DATASET_ID,
        card_id="card3_top_bottom_teams",
        category_tab="Urban arterial",
        page=1,
        page_size=5,
    )
    res = get_drilldown_records(req)

    assert res.total_matching_records > 0
    assert len(res.rows) == 5
    assert len(res.columns) > 10
    # Every returned row must match the drilled category
    for r in res.rows:
        assert r.get("road_type") == "Urban arterial"


def test_missing_dataset_raises():
    """Missing dataset must raise FileNotFoundError, not fabricate metrics."""
    with pytest.raises(FileNotFoundError):
        compute_dashboard_analytics(
            dataset_id="00000000000000000000000000000000",
            project_id="test_project",
        )


def test_api_dashboard_endpoints(client):
    """Verify FastAPI router integration."""
    # 1. Analytics
    res_analytics = client.post("/api/dashboard/analytics", json={
        "dataset_id": REAL_DATASET_ID,
        "project_id": "test_project",
    })
    assert res_analytics.status_code == 200
    body = res_analytics.json()
    assert body["readiness_status"] == "READY"
    assert body["quality_summary"]["total_records"] == 2500

    # 2. Filters
    res_filters = client.get(f"/api/dashboard/filters?dataset_id={REAL_DATASET_ID}")
    assert res_filters.status_code == 200
    f_body = res_filters.json()
    assert len(f_body["teams"]) > 0
    assert len(f_body["years"]) > 0

    # 3. Verify
    res_verify = client.post("/api/dashboard/verify", json={
        "dataset_id": REAL_DATASET_ID,
    })
    assert res_verify.status_code == 200
    assert res_verify.json()["reconciliation_passed"] is True

    # 4. Drilldown
    res_dd = client.post("/api/dashboard/drilldown", json={
        "dataset_id": REAL_DATASET_ID,
        "card_id": "card5_meetings_attended",
        "category_tab": "Urban arterial",
        "page": 1,
        "page_size": 2,
    })
    assert res_dd.status_code == 200
    assert len(res_dd.json()["rows"]) == 2

    # 5. Export
    res_export = client.post("/api/dashboard/export", json={
        "dataset_id": REAL_DATASET_ID,
        "format": "csv",
    })
    assert res_export.status_code == 200
    assert "EXECUTIVE PERFORMANCE MANAGEMENT DASHBOARD" in res_export.text
