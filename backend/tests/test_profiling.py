"""Phase 5 tests - deterministic zero-LLM profiling.

Expected quality scores are hand-computed from the documented formula in
app/profiling/profiler.py (not copied from a previous run):

Fixture DIRTY (6 rows x 7 cols):
  missing cells 3/42 = 0.0714        -> -40*0.0714 = -2.856
  duplicate rows 1/6 = 0.1667        -> -20*0.1667 = -3.334
  constant columns: flag             -> -10*1      = -10
  high issues: future_score leakage  -> -10*1      = -10
  medium issues: 3 missing + 1 const + 1 dup = 5
                                      -> -min(10,25)= -10
  score = 100 - 36.19 = 63.8 -> grade D

Fixture CLEAN (4 rows x 2 cols): only leakage high issue (x perfectly
correlates with target y) -> 100 - 10 = 90.0 -> grade A
"""
import json
from pathlib import Path

import pytest

DIRTY_CSV = (
    b"age,score,flag,category,signup_date,future_score,target\n"
    b"30,85.5,1,A,2024-01-01,1,1\n"
    b"30,85.5,1,A,2024-01-01,1,1\n"
    b"40,90.0,1,B,2024-01-03,0,0\n"
    b"25,,1,B,,1,1\n"
    b",85.5,1,A,2024-01-05,1,1\n"
    b"30,85.5,1,A,2024-01-06,0,0\n"
)

CLEAN_CSV = (
    b"x,y\n"
    b"1,2\n"
    b"2,4\n"
    b"3,6\n"
    b"4,8\n"
)


def _ingest(upload_fn, name, content):
    resp = upload_fn(name, content, mime="text/csv")
    assert resp.status_code == 201, resp.text
    return resp.json()["datasets"][0]["dataset_id"]


def test_quality_before_profile_is_controlled_404(upload_fn, client):
    ds_id = _ingest(upload_fn, "nop.csv", CLEAN_CSV)
    resp = client.get(f"/api/datasets/{ds_id}/quality")
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "NOT_PROFILED"
    g = client.get(f"/api/datasets/{ds_id}/profile")
    assert g.status_code == 404


def test_profile_dirty_dataset_exact_score(upload_fn, client):
    ds_id = _ingest(upload_fn, "dirty.csv", DIRTY_CSV)

    resp = client.post(f"/api/datasets/{ds_id}/profile")
    assert resp.status_code == 201, resp.text
    summary = resp.json()["summary"]

    # --- hand-computed expectations ---
    assert summary["quality_score"] == 63.8
    assert summary["quality_grade"] == "D"
    assert summary["duplicate_rows"] == 1
    assert summary["overall_missing_ratio"] == 0.0714

    # raw report stored on E:
    report_path = Path(summary["report_path"])
    assert report_path.exists()
    assert "profiles" in str(report_path)

    report = client.get(f"/api/datasets/{ds_id}/profile").json()

    # required DataQualityReport fields (spec)
    for key in (
        "quality_score", "quality_grade", "issues", "warnings",
        "statistics", "schema", "recommendations",
    ):
        assert key in report, f"missing DataQualityReport field: {key}"
    assert report["quality_score"] == 63.8
    assert report["quality_grade"] == "D"

    # zero-LLM provenance marker
    assert report["engine"].startswith("deterministic:")

    # statistics: rows/cols/duplicates
    stats = report["statistics"]
    assert stats["row_count"] == 6
    assert stats["column_count"] == 7
    assert stats["duplicate_rows"] == 1
    assert stats["duplicate_ratio"] == 0.1667

    # schema entries with missing/unique/cardinality
    by_name = {c["name"]: c for c in report["schema"]}
    assert len(by_name) == 7
    assert by_name["age"]["missing_count"] == 1
    assert by_name["age"]["missing_pct"] == 16.67
    assert by_name["score"]["missing_count"] == 1
    assert by_name["signup_date"]["missing_count"] == 1
    assert by_name["flag"]["constant"] is True
    assert by_name["category"]["unique_count"] == 2
    assert 0 < by_name["category"]["cardinality_ratio"] < 1

    # numeric statistics + quantiles + min/max/mean/median/std
    age = stats["numeric"]["age"]
    assert age["min"] == 25.0
    assert age["max"] == 40.0
    assert age["mean"] == 31.0
    assert age["median"] == 30.0
    assert age["count"] == 5
    assert age["q1"] is not None and age["q3"] is not None
    assert age["std"] == pytest.approx(5.4772, abs=0.001)

    # outlier indicators
    assert age["outliers_present"] is True  # 25 and 40 outside IQR bounds
    assert age["outliers_low"] == 1 and age["outliers_high"] == 1
    assert stats["numeric"]["flag"]["outliers_present"] is False

    # roles
    roles = report["roles"]
    assert "category" in roles["categorical_columns"]
    assert "age" in roles["numeric_columns"]
    assert "signup_date" in roles["datetime_columns"]  # name + parse detection
    assert "flag" in roles["constant_columns"]
    assert roles["potential_ids"] == []  # no unique row key in fixture
    assert "target" in roles["potential_targets"]  # name pattern
    assert "future_score" in roles["leakage_candidates"]

    # correlation summary: perfect target correlation reported
    assert any(
        c["columns"] == ["future_score", "target"] and c["pearson"] == 1.0
        for c in stats["correlations"]
    ), stats["correlations"]

    # issues carry severity; leakage is high severity
    codes = {(i["code"], i["severity"]) for i in report["issues"]}
    assert ("POTENTIAL_LEAKAGE", "high") in codes
    assert ("DUPLICATE_ROWS", "medium") in codes
    assert ("CONSTANT_COLUMN", "medium") in codes
    assert sum(1 for i in report["issues"] if i["code"] == "MISSING_VALUES") == 3
    assert ("OUTLIERS_PRESENT", "low") in codes

    # date detection warning surfaced
    assert any("date/time" in w for w in report["warnings"])

    # recommendations are concrete
    assert any("duplicate" in r.lower() for r in report["recommendations"])
    assert any("unique identifier" in r.lower() for r in report["recommendations"])

    # quality endpoint returns the stored summary
    q = client.get(f"/api/datasets/{ds_id}/quality")
    assert q.status_code == 200
    assert q.json()["quality_score"] == 63.8
    assert q.json()["quality_grade"] == "D"
    assert q.json()["issues_by_severity"]["high"] == 1
    assert q.json()["issues_by_severity"]["medium"] == 5

    # profile summary persisted on the dataset document in Mongo
    doc = client.get(f"/api/datasets/{ds_id}").json()
    assert doc["profile"]["quality_score"] == 63.8
    assert doc["profile"]["report_path"] == summary["report_path"]


def test_profile_clean_dataset_scores_higher(upload_fn, client):
    dirty_id = _ingest(upload_fn, "d2.csv", DIRTY_CSV)
    clean_id = _ingest(upload_fn, "clean.csv", CLEAN_CSV)

    clean = client.post(f"/api/datasets/{clean_id}/profile").json()["summary"]
    dirty = client.post(f"/api/datasets/{dirty_id}/profile").json()["summary"]

    assert clean["quality_score"] == 90.0  # 100 - 10 (leakage high issue)
    assert clean["quality_grade"] == "A"
    assert clean["quality_score"] > dirty["quality_score"]

    report = client.get(f"/api/datasets/{clean_id}/profile").json()
    assert report["statistics"]["row_count"] == 4
    assert report["statistics"]["duplicate_rows"] == 0
    assert report["statistics"]["overall_missing_ratio"] == 0.0
    assert "x" in report["roles"]["potential_ids"]  # x is unique per row
    assert "y" in report["roles"]["potential_targets"]  # name pattern
    assert "x" in report["roles"]["leakage_candidates"]  # corr(x,y) = 1.0


def test_profile_deterministic_across_runs(upload_fn, client):
    ds_id = _ingest(upload_fn, "det.csv", DIRTY_CSV)
    first = client.post(f"/api/datasets/{ds_id}/profile").json()["summary"]
    second = client.post(f"/api/datasets/{ds_id}/profile").json()["summary"]

    assert first["quality_score"] == second["quality_score"]
    assert first["quality_grade"] == second["quality_grade"]
    assert first["issues_by_severity"] == second["issues_by_severity"]

    r1 = client.get(f"/api/datasets/{ds_id}/profile").json()
    r2 = client.get(f"/api/datasets/{ds_id}/profile").json()
    assert r1["statistics"] == r2["statistics"]
    assert r1["issues"] == r2["issues"]
    assert r1["schema"] == r2["schema"]


def test_grade_thresholds_match_score(upload_fn, client):
    ds_id = _ingest(upload_fn, "grade.csv", DIRTY_CSV)
    report = client.post(f"/api/datasets/{ds_id}/profile").json()["summary"]
    score = report["quality_score"]
    grade = report["quality_grade"]
    expected = "A" if score >= 90 else "B" if score >= 80 else "C" if score >= 70 else "D" if score >= 60 else "F"
    assert grade == expected


def test_profile_empty_dataset_reports_issue(upload_fn, client):
    ds_id = _ingest(upload_fn, "headeronly.csv", b"a,b,c\n")
    resp = client.post(f"/api/datasets/{ds_id}/profile")
    assert resp.status_code == 201, resp.text
    report = client.get(f"/api/datasets/{ds_id}/profile").json()
    codes = [i["code"] for i in report["issues"]]
    assert "EMPTY_DATASET" in codes
    assert report["statistics"]["row_count"] == 0


def test_profile_unknown_dataset_404(client):
    fake = "0" * 32
    assert client.post(f"/api/datasets/{fake}/profile").status_code == 404
    assert client.get(f"/api/datasets/{fake}/profile").status_code == 404
