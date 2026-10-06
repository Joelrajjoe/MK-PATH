import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_project_crud():
    with TestClient(app) as client:
        # 1. Create project
        payload = {
            "name": "Test Remediated Project",
            "description": "Integration testing for project API",
            "businessGoal": "Predict churn with zero mock data"
        }
        response = client.post("/api/projects", json=payload)
        if response.status_code == 503:
            pytest.skip("MongoDB Atlas not reachable in test environment")

        assert response.status_code == 201
        data = response.json()
        assert "project_id" in data or "id" in data
        pid = data.get("project_id") or data.get("id")
        assert data["name"] == payload["name"]
        assert data["status"] == "active"

        # 2. Get project
        get_res = client.get(f"/api/projects/{pid}")
        assert get_res.status_code == 200
        assert get_res.json()["name"] == payload["name"]

        # 3. List projects
        list_res = client.get("/api/projects")
        assert list_res.status_code == 200
        items = list_res.json()
        assert any(p.get("project_id") == pid or p.get("id") == pid for p in items)
