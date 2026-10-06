"""Shared fixtures for MK-Path Phase 4/5 tests.

Tests run against the real FastAPI app and real MongoDB Atlas (as required:
no mocked database responses). Every document created by a test is deleted
during teardown so the shared database stays clean.
"""
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app

SESSION_START = datetime.now(timezone.utc)


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def _cleanup_test_data():
    """Wipe every dataset + audit document produced during this test."""
    yield
    try:
        from pymongo import MongoClient

        cli = MongoClient(settings.MONGODB_URI, serverSelectionTimeoutMS=5000)
        db = cli[settings.MONGODB_DATABASE]
        db.datasets.delete_many(
            {"created_at": {"$gte": SESSION_START}}
        )
        db.audit_events.delete_many(
            {"created_at": {"$gte": SESSION_START}}
        )
        db.ontology.delete_many(
            {"created_at": {"$gte": SESSION_START}}
        )
        db.clarification_questions.delete_many(
            {"created_at": {"$gte": SESSION_START}}
        )
        cli.close()
    except Exception:
        pass  # cleanup is best-effort; never hides the real test result


@pytest.fixture()
def upload_fn(client):
    """POST a file to /api/datasets/upload and return the Response."""

    def _upload(name: str, content: bytes, sheet_name=None, mime="application/octet-stream"):
        data = {}
        if sheet_name is not None:
            data["sheet_name"] = sheet_name
        return client.post(
            "/api/datasets/upload",
            files={"file": (name, content, mime)},
            data=data,
        )

    return _upload


@pytest.fixture()
def csv_dataset(upload_fn):
    """A small known-good CSV dataset: returns (response_json, raw_csv)."""
    raw = (
        b"id,name,score\n"
        b"1,alpha,10.5\n"
        b"2,beta,20.0\n"
        b"3,gamma,30.5\n"
    )
    resp = upload_fn("people.csv", raw, mime="text/csv")
    assert resp.status_code == 201, resp.text
    return resp.json(), raw
