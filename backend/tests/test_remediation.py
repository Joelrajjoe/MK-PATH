import os
import shutil
import pytest
import pandas as pd
from pathlib import Path
from fastapi.testclient import TestClient

from app.main import app
from app import repo
from app.config import settings
from app.modeling import tournament
from app.engineering import ml_engineer
from app.healing import engine as healing_engine
from app.orchestrator.graph import get_compiled_graph

client = TestClient(app)

def test_real_time_integration_remediation():
    with TestClient(app) as client:
        # 1. Project API Real Test
        proj_payload = {
            "name": "E2E Real Data Project",
            "description": "Testing remediated real-time pipeline",
            "businessGoal": "Predict customer churn"
        }
        res = client.post("/api/projects", json=proj_payload)
        if res.status_code == 503:
            pytest.skip("MongoDB Atlas not reachable")

        assert res.status_code == 201, res.text
        p_data = res.json()
        project_id = p_data["id"]
        assert p_data["name"] == proj_payload["name"]

        # Retrieve Project
        p_get = client.get(f"/api/projects/{project_id}")
        assert p_get.status_code == 200
        assert p_get.json()["name"] == proj_payload["name"]

        # 2. Real Dataset Ingestion
        csv_content = (
            b"customer_id,age,income,tenure,churn\n"
            b"101,25,50000.0,12,0\n"
            b"102,45,120000.0,36,0\n"
            b"103,35,75000.0,24,1\n"
            b"104,50,90000.0,48,0\n"
            b"105,23,30000.0,6,1\n"
            b"106,40,85000.0,30,0\n"
            b"107,29,60000.0,18,1\n"
            b"108,60,150000.0,60,0\n"
            b"109,31,65000.0,15,1\n"
            b"110,48,110000.0,42,0\n"
        )
        up_res = client.post(
            "/api/datasets/upload",
            files={"file": ("churn_data.csv", csv_content, "text/csv")}
        )
        assert up_res.status_code == 201, up_res.text
        dataset_id = up_res.json()["datasets"][0]["dataset_id"]

        # 3. Real Profiling
        prof_res = client.post(f"/api/datasets/{dataset_id}/profile")
        assert prof_res.status_code == 201, prof_res.text
        prof_data = prof_res.json()["summary"]
        r_cnt = prof_data.get("row_count") or prof_data.get("rows")
        c_cnt = prof_data.get("column_count") or prof_data.get("columns")
        assert r_cnt == 10
        assert c_cnt == 5

        # 4. Real Semantic Context
        sem_res = client.post(
            f"/api/datasets/{dataset_id}/semantic",
            json={"business_goal": "Predict customer churn"}
        )
        assert sem_res.status_code == 201, sem_res.text
        sem_data = sem_res.json()
        assert "confidence" in sem_data or "concepts" in sem_data

        # 5. Real Model Tournament on Dataset Columns
        df = pd.DataFrame({
            "age": [25, 45, 35, 50, 23, 40, 29, 60, 31, 48],
            "income": [50000, 120000, 75000, 90000, 30000, 85000, 60000, 150000, 65000, 110000],
            "tenure": [12, 36, 24, 48, 6, 30, 18, 60, 15, 42],
            "churn": [0, 0, 1, 0, 1, 0, 1, 0, 1, 0]
        })
        tourn_res = tournament.run_model_tournament(df, target="churn", is_temporal=False)
        assert tourn_res["status"] == "SUCCESS"
        assert len(tourn_res["model_candidates"]) >= 2
        selected_model = tourn_res["selected_model"]
        assert selected_model["metrics"]["accuracy"] > 0.0

        # 6. Real Artifact Generation & Inference Validation
        verif_report = {
            "deployment_status": "READY",
            "summary": "All mandatory verification gates passed."
        }
        feature_schema = {"age": "int", "income": "float", "tenure": "int"}
        run_id = "test_run_remediation"
        
        art_meta = ml_engineer.generate_deployment_artifacts(
            project_id, run_id, verif_report, selected_model, feature_schema
        )
        assert art_meta["status"] == "PASS"
        assert art_meta["downloadable"] is True
        assert "test_prediction" in art_meta["validation"]

        # 7. Real Healing Engine
        df_missing = df.copy()
        df_missing.loc[0, "income"] = None
        df_missing.loc[2, "age"] = None
        plan = healing_engine.generate_healing_plan(dataset_id, {"columns": [{"name": "income", "null_count": 1}, {"name": "age", "null_count": 1}]})
        heal_event = healing_engine.apply_healing(df_missing, plan, dataset_id)
        assert heal_event.status == "COMPLETED"
        assert heal_event.quality_report.after_score >= heal_event.quality_report.before_score
