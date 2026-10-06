"""Phase 6 tests - semantic knowledge layer.

No real LLM is used: GEMINI_API_KEY is unset in the test environment, so the
NullProvider runs deterministic-only (this is itself a required behavior).
A ScriptedProvider unit test proves LLM proposals stay non-final.
"""
import json
from pathlib import Path

import pytest

from app.config import settings
from app.semantic.builder import build_context
from app.semantic.llm import NullProvider
from app.semantic.models import ConceptSource, ConceptStatus

ORDERS_CSV = (
    b"order_id,region,total_value,status,order_date,target_churn\n"
    b"1,East,100.5,4,2024-01-02,0\n"
    b"2,West,250.0,1,2024-01-03,1\n"
    b"3,East,75.25,4,2024-01-04,0\n"
    b"4,North,,2,2024-01-05,1\n"
    b"5,South,60.0,3,2024-01-06,0\n"
)

TWO_TARGETS_CSV = (
    b"churn,label,total_value\n"
    b"0,1,10\n"
    b"1,0,20\n"
    b"0,0,30\n"
    b"1,1,40\n"
)

NO_TARGET_CSV = (
    b"a,b,region\n"
    b"1,x,10\n"
    b"2,y,20\n"
    b"3,z,30\n"
    b"4,x,40\n"
)

STATUS_MAPPING = "4=cancelled;1=active;2=test order;3=fraud hold"


def _ingest_and_profile(client, upload_fn, name, content):
    resp = upload_fn(name, content, mime="text/csv")
    assert resp.status_code == 201, resp.text
    ds_id = resp.json()["datasets"][0]["dataset_id"]
    prof = client.post(f"/api/datasets/{ds_id}/profile")
    assert prof.status_code == 201, prof.text
    return ds_id


def _mongo():
    from pymongo import MongoClient

    cli = MongoClient(settings.MONGODB_URI, serverSelectionTimeoutMS=5000)
    return cli[settings.MONGODB_DATABASE]


# ---------------------------------------------------------------------------
# Core flow: coded-column ambiguity interrupts, user decision resolves
# ---------------------------------------------------------------------------

def test_coded_column_interrupts_and_user_decision_resolves(client, upload_fn):
    ds_id = _ingest_and_profile(client, upload_fn, "orders_sem.csv", ORDERS_CSV)

    # Build semantic context with a business goal
    resp = client.post(
        f"/api/datasets/{ds_id}/semantic",
        json={"business_goal": "predict order cancellation"},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()

    # The status column (4 distinct coded values) must interrupt the workflow
    assert isinstance(body["llm_available"], bool)
    assert len(body["questions"]) == 1
    q = body["questions"][0]
    assert q["kind"] == "VALUE_MAPPING"
    assert q["severity"] == "blocking"
    assert q["allows_free_text"] is True

    # clarification question persisted in MongoDB
    mdb = _mongo()
    qdoc = mdb.clarification_questions.find_one({"question_id": q["question_id"]}, {"_id": 0})
    assert qdoc is not None
    assert qdoc["status"] == "open"
    assert qdoc["dataset_id"] == ds_id
    # ontology document persisted with all required SemanticContext fields
    ctx_doc = mdb.ontology.find_one({"dataset_id": ds_id}, {"_id": 0})
    assert ctx_doc is not None
    for field in (
        "dataset_id", "business_goal", "column_definitions", "business_terms",
        "metrics", "relationships", "ambiguities", "user_decisions", "confidence",
    ):
        assert field in ctx_doc, f"SemanticContext missing {field}"
    assert ctx_doc["business_goal"] == "predict order cancellation"

    # concept coverage: all structural concept types present
    ctypes = {c["type"] for c in ctx_doc["concepts"]}
    for required in ("dataset", "table", "column", "metric", "dimension",
                     "target", "feature", "event", "business_term", "definition"):
        assert required in ctypes, f"concept type {required} missing"

    # relationships exist (e.g. target -> dataset, glossary terms)
    preds = {r["predicate"] for r in ctx_doc["relationships"]}
    assert "is_target_of" in preds
    assert "timestamps" in preds

    # GET semantic returns the stored context
    got = client.get(f"/api/datasets/{ds_id}/semantic")
    assert got.status_code == 200
    assert got.json()["context_id"] == ctx_doc["context_id"]

    # GET ambiguities
    ambs = client.get(f"/api/datasets/{ds_id}/semantic/ambiguities")
    assert ambs.status_code == 200
    assert ambs.json()["workflow_status"] == "interrupted"
    assert len(ambs.json()["ambiguities"]) == 1

    # clarifications listing
    cl = client.get("/api/clarifications", params={"dataset_id": ds_id})
    assert cl.status_code == 200
    assert cl.json()["total"] == 1

    # resolving the question applies the user decision and resumes the workflow
    res = client.post(
        f"/api/clarifications/{q['question_id']}/resolve",
        json={"choice": STATUS_MAPPING, "note": "confirmed with domain owner"},
    )
    assert res.status_code == 200, res.text
    rbody = res.json()
    assert rbody["workflow_status"] == "ready"
    assert rbody["confidence"] == 1.0  # goal present, zero open ambiguities
    assert rbody["open_ambiguities"] == 0

    # decision is recorded on the context (user_decisions)
    got2 = client.get(f"/api/datasets/{ds_id}/semantic").json()
    assert got2["version"] == 2
    assert len(got2["user_decisions"]) == 1
    assert got2["user_decisions"][0]["choice"] == STATUS_MAPPING
    status_def = next(c for c in got2["column_definitions"] if c["name"] == "status")
    assert status_def["business_meaning"] == STATUS_MAPPING
    assert status_def["meaning_source"] == "user_decision"
    assert status_def["status"] == "resolved"

    # question marked resolved
    q2 = mdb.clarification_questions.find_one({"question_id": q["question_id"]}, {"_id": 0})
    assert q2["status"] == "resolved"
    assert q2["answer"]["choice"] == STATUS_MAPPING

    # rebuild after resolution: no duplicate question, workflow stays ready
    resp2 = client.post(
        f"/api/datasets/{ds_id}/semantic",
        json={"business_goal": "predict order cancellation"},
    )
    assert resp2.status_code == 201
    assert resp2.json()["questions"] == []
    assert resp2.json()["workflow_status"] == "ready"


def test_no_business_goal_penalty(upload_fn, client):
    ds_id = _ingest_and_profile(client, upload_fn, "orders_nog.csv", ORDERS_CSV)
    resp = client.post(f"/api/datasets/{ds_id}/semantic")  # no body
    assert resp.status_code == 201
    body = resp.json()
    # 1 blocking (0.35) + missing goal (0.15) -> 0.5
    assert body["confidence"] == 0.5
    assert body["workflow_status"] == "interrupted"


def test_llm_unavailable_warning_recorded(upload_fn, client, monkeypatch):
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "")
    from app.semantic import llm
    monkeypatch.setattr(llm, "_provider", None)
    ds_id = _ingest_and_profile(client, upload_fn, "orders_llm.csv", ORDERS_CSV)
    resp = client.post(f"/api/datasets/{ds_id}/semantic", json={"business_goal": "g"})
    body = resp.json()
    assert body["llm_available"] is False
    ctx = client.get(f"/api/datasets/{ds_id}/semantic").json()
    assert any("LLM is not configured" in w for w in ctx["warnings"])
    # no concept may pretend to be LLM-sourced
    assert all(c["source"] != "llm_proposed" for c in ctx["concepts"])


# ---------------------------------------------------------------------------
# Target selection ambiguity
# ---------------------------------------------------------------------------

def test_two_target_candidates_require_decision(client, upload_fn):
    ds_id = _ingest_and_profile(client, upload_fn, "two_targets.csv", TWO_TARGETS_CSV)
    resp = client.post(f"/api/datasets/{ds_id}/semantic", json={"business_goal": "churn model"})
    assert resp.status_code == 201
    body = resp.json()
    assert body["workflow_status"] == "interrupted"
    assert body["confidence"] == 0.65
    assert len(body["questions"]) == 1
    q = body["questions"][0]
    assert q["kind"] == "TARGET_SELECTION"
    labels = {o["label"] for o in q["options"]}
    assert labels == {"churn", "label"}

    res = client.post(
        f"/api/clarifications/{q['question_id']}/resolve", json={"choice": "churn"}
    )
    assert res.status_code == 200
    assert res.json()["workflow_status"] == "ready"

    ctx = client.get(f"/api/datasets/{ds_id}/semantic").json()
    tstates = {t["name"]: t["status"] for t in ctx["targets"]}
    assert tstates["churn"] == "confirmed"
    assert tstates["label"] == "rejected"
    chosen = next(t for t in ctx["targets"] if t["name"] == "churn")
    assert chosen["finalized_by"] == "user_decision"


def test_no_target_detected_offers_numeric_options(client, upload_fn):
    ds_id = _ingest_and_profile(client, upload_fn, "no_target.csv", NO_TARGET_CSV)
    resp = client.post(f"/api/datasets/{ds_id}/semantic", json={"business_goal": "forecast"})
    assert resp.status_code == 201
    body = resp.json()
    assert body["workflow_status"] == "interrupted"
    q = body["questions"][0]
    assert q["kind"] == "TARGET_SELECTION"
    # numeric columns are offered as candidate targets (b is a string column)
    assert {o["label"] for o in q["options"]} == {"a", "region"}

    res = client.post(
        f"/api/clarifications/{q['question_id']}/resolve", json={"choice": "a"}
    )
    assert res.status_code == 200
    assert res.json()["workflow_status"] == "ready"
    ctx = client.get(f"/api/datasets/{ds_id}/semantic").json()
    confirmed = [t for t in ctx["targets"] if t["status"] == "confirmed"]
    assert [t["name"] for t in confirmed] == ["a"]


def test_target_choice_must_be_a_real_column(client, upload_fn):
    ds_id = _ingest_and_profile(client, upload_fn, "no_target2.csv", NO_TARGET_CSV)
    resp = client.post(f"/api/datasets/{ds_id}/semantic", json={"business_goal": "forecast"})
    q = resp.json()["questions"][0]
    res = client.post(
        f"/api/clarifications/{q['question_id']}/resolve",
        json={"choice": "not_a_column"},
    )
    assert res.status_code == 422
    assert "not a column" in res.json()["detail"]


# ---------------------------------------------------------------------------
# Error paths
# ---------------------------------------------------------------------------

def test_semantic_unknown_dataset_404(client):
    fake = "0" * 32
    assert client.post(f"/api/datasets/{fake}/semantic", json={}).status_code == 404
    assert client.get(f"/api/datasets/{fake}/semantic").status_code == 404


def test_semantic_before_build_404(upload_fn, client):
    ds_id = _ingest_and_profile(client, upload_fn, "nobuild.csv", ORDERS_CSV)
    got = client.get(f"/api/datasets/{ds_id}/semantic")
    assert got.status_code == 404
    assert got.json()["detail"]["code"] == "NO_SEMANTIC_CONTEXT"


def test_double_resolve_409_and_unknown_404(client, upload_fn):
    ds_id = _ingest_and_profile(client, upload_fn, "double.csv", ORDERS_CSV)
    resp = client.post(f"/api/datasets/{ds_id}/semantic", json={"business_goal": "g"})
    q = resp.json()["questions"][0]
    r1 = client.post(
        f"/api/clarifications/{q['question_id']}/resolve", json={"choice": STATUS_MAPPING}
    )
    assert r1.status_code == 200
    r2 = client.post(
        f"/api/clarifications/{q['question_id']}/resolve", json={"choice": STATUS_MAPPING}
    )
    assert r2.status_code == 409
    r3 = client.post("/api/clarifications/deadbeef/resolve", json={"choice": "x"})
    assert r3.status_code == 404


# ---------------------------------------------------------------------------
# Confidence formula (documented penalties)
# ---------------------------------------------------------------------------

def test_confidence_formula_two_blockings_no_goal(client, upload_fn):
    ds_id = _ingest_and_profile(client, upload_fn, "two_block.csv", ORDERS_CSV)
    # ORDERS has 1 blocking (status). Craft 2 blockings by also having two
    # targets: rename target column so both churn-style columns exist.
    # Instead, verify the no-goal + 1-blocking case here and the 2-blocking
    # case with a dedicated fixture below.
    resp = client.post(f"/api/datasets/{ds_id}/semantic")  # no goal
    assert resp.json()["confidence"] == 0.5


def test_confidence_formula_two_blockings_with_goal(upload_fn, client):
    csv = (
        b"churn,label,total_value,status\n"
        b"0,1,10,4\n"
        b"1,0,20,1\n"
        b"0,0,30,4\n"
        b"1,1,40,2\n"
    )
    ds_id = _ingest_and_profile(client, upload_fn, "twoblock.csv", csv)
    resp = client.post(f"/api/datasets/{ds_id}/semantic", json={"business_goal": "g"})
    body = resp.json()
    # 2 blocking ambiguities (TARGET_SELECTION + VALUE_MAPPING): 1 - 0.7 = 0.3
    assert body["confidence"] == 0.3
    assert body["workflow_status"] == "interrupted"
    assert len(body["questions"]) == 2
    # resolve both -> ready
    for q in body["questions"]:
        choice = "churn" if q["kind"] == "TARGET_SELECTION" else "4=cancelled;1=active;2=test;3=fraud"
        r = client.post(f"/api/clarifications/{q['question_id']}/resolve", json={"choice": choice})
        assert r.status_code == 200
    final = client.get(f"/api/datasets/{ds_id}/semantic").json()
    assert final["workflow_status"] == "ready"
    assert final["confidence"] == 1.0


# ---------------------------------------------------------------------------
# LLM proposals (scripted provider) can never finalize semantics
# ---------------------------------------------------------------------------

class ScriptedProvider:
    """Test double: returns canned proposals (as a real LLM provider would)."""

    name = "gemini"

    def propose_column_interpretations(self, *, column, dtype, values, business_goal):
        if column == "status":
            return [
                {"label": "order_status", "description": "4=cancelled, 1=active", "confidence": 0.55},
                {"label": "fraud_hold", "description": "4 could be a fraud hold", "confidence": 0.35},
            ]
        return None

    def propose_ambiguities(self, *, context_summary):
        return [
            {"subject": "amount", "question": "Is amount gross or net of tax?"}
        ]


def test_scripted_llm_proposals_stay_non_final():
    from app.ingestion.parsers import parse_csv
    import tempfile
    from pathlib import Path

    p = Path(tempfile.gettempdir()) / "sem_orders.csv"
    p.write_bytes(ORDERS_CSV)
    table = parse_csv(p, "orders")
    dataset = {
        "dataset_id": "a" * 32,
        "original_filename": "orders.csv",
        "source_format": "csv",
        "table_name": "orders",
        "normalized_path": table.normalized_path,
        "schema": table.schema,
        "upload_id": "b" * 32,
    }
    context, drafts = build_context(
        dataset=dataset,
        profile=None,
        business_goal="predict cancellations",
        provider=ScriptedProvider(),
    )
    ctx = context.model_dump()
    # LLM proposals are attached to the VALUE_MAPPING ambiguity as needs_review
    amb = next(a for a in ctx["ambiguities"] if a["kind"] == "VALUE_MAPPING")
    assert amb["status"] == "open"
    assert amb["severity"] == "blocking"
    labels = {o["label"] for o in amb["options"]}
    assert {"order_status", "fraud_hold"} <= labels
    assert all(o["source"] == "llm_proposed" for o in amb["options"])
    # proposals recorded on the column definition, status stays unresolved
    cd = next(c for c in ctx["column_definitions"] if c["name"] == "status")
    assert len(cd["proposals"]) == 2
    assert cd["status"] == "unresolved"
    assert cd["business_meaning"] is None
    # an explicit needs_review concept exists; NOTHING is finalized by the LLM
    interp = next(
        c for c in ctx["concepts"] if c["name"] == "interpretation:status"
    )
    assert interp["status"] == "needs_review"
    assert interp["source"] == "llm_proposed"
    assert all(c["finalized_by"] != "llm" for c in ctx["concepts"])
    # LLM advisory ambiguity present but must not clear the blocking one
    assert any(a["kind"] == "LLM_PROPOSED" and a["severity"] == "advisory" for a in ctx["ambiguities"])
    assert context.workflow_status == "interrupted"
    assert len(drafts) == 1  # only blocking ambiguities create questions
