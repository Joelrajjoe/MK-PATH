from datetime import datetime, timezone
import importlib.util
import json
import logging
import os
import pickle
import shutil
from pathlib import Path
from typing import Any, Dict

import pandas as pd

logger = logging.getLogger("mkpath.engineering.ml_engineer")


def validate_artifact(artifact_dir: Path, feature_schema: Dict[str, str]) -> Dict[str, Any]:
    """
    Validation check for generated deployment artifact:
    1. Confirm files exist (model.pkl, api/main.py, api/schema.py).
    2. Load the model.pkl file.
    3. Execute a real inference test.
    4. Verify output structure.
    """
    model_file = artifact_dir / "model" / "model.pkl"
    api_main = artifact_dir / "api" / "main.py"
    api_schema = artifact_dir / "api" / "schema.py"

    if not model_file.exists():
        return {"status": "FAILED", "reason": "model/model.pkl is missing."}
    if not api_main.exists() or not api_schema.exists():
        return {"status": "FAILED", "reason": "API schema or main.py file is missing."}

    # Load model
    try:
        with open(model_file, "rb") as f:
            model = pickle.load(f)
    except Exception as exc:
        return {"status": "FAILED", "reason": f"Model failed to deserialize: {type(exc).__name__}: {exc}"}

    # Determine exact expected features from model
    expected_features = getattr(model, "feature_names_in_", None)
    if expected_features is not None:
        feature_names_to_test = list(expected_features)
    else:
        feature_names_to_test = list(feature_schema.keys())

    # Construct test record
    test_record = {}
    for f_name in feature_names_to_test:
        f_type = feature_schema.get(f_name, "float")
        if f_type in ["int", "integer"]:
            test_record[f_name] = 1
        elif f_type in ["float", "double", "number"]:
            test_record[f_name] = 1.0
        else:
            test_record[f_name] = 0.0

    if not test_record:
        test_record = {"feature_1": 1.0}

    # Test real inference
    try:
        test_df = pd.DataFrame([test_record])
        pred = model.predict(test_df)[0]
        prob = None
        if hasattr(model, "predict_proba"):
            try:
                prob_arr = model.predict_proba(test_df)
                if prob_arr.shape[1] > 1:
                    prob = float(prob_arr[0][1])
            except Exception:
                pass
        
        return {
            "status": "PASS",
            "test_prediction": str(pred),
            "test_probability": prob,
            "feature_count": len(test_record),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as exc:
        return {"status": "FAILED", "reason": f"Real test inference failed: {type(exc).__name__}: {exc}"}


def generate_deployment_artifacts(
    project_id: str,
    run_id: str,
    verification_report: Dict[str, Any],
    model_info: Dict[str, Any],
    feature_schema: Dict[str, str],
) -> Dict[str, Any]:
    """
    ML Engineer Agent generates real FastAPI deployment artifacts from the verified trained model.
    """
    artifact_dir = Path("E:/MK-PATH/artifacts") / project_id / run_id
    artifact_dir.mkdir(parents=True, exist_ok=True)

    if verification_report.get("deployment_status") != "READY":
        diag_path = artifact_dir / "DIAGNOSTIC_REPORT.md"
        with open(diag_path, "w", encoding="utf-8") as f:
            f.write(f"# Diagnostic Report for {project_id}\n\n")
            f.write("## Deployment Blocked\n")
            f.write("Mandatory verification gates failed. Artifact generation aborted.\n\n")
            f.write(json.dumps(verification_report, indent=2))
        return {
            "artifact_dir": str(artifact_dir),
            "status": "BLOCKED",
            "reason": "Verification report deployment_status != READY"
        }

    model_version = model_info.get("model_name", "v1.0.0")
    model_path_src = model_info.get("path", "")

    if not model_path_src or not os.path.exists(model_path_src):
        return {
            "artifact_dir": str(artifact_dir),
            "status": "FAILED",
            "reason": f"Source model file does not exist at '{model_path_src}'."
        }

    model_dir = artifact_dir / "model"
    model_dir.mkdir(exist_ok=True)
    shutil.copy(model_path_src, model_dir / "model.pkl")

    api_dir = artifact_dir / "api"
    model_features = model_info.get("feature_names", [])
    if model_features:
        feature_schema = {k: v for k, v in feature_schema.items() if k in model_features}

    # Generate schema.py based on feature_schema
    fields = []
    for f_name, f_type in feature_schema.items():
        if f_type in ["int", "integer"]:
            fields.append(f"{f_name}: int = 0")
        elif f_type in ["float", "double", "number"]:
            fields.append(f"{f_name}: float = 0.0")
        else:
            fields.append(f"{f_name}: str = ''")

    if not fields:
        fields = ["feature_1: float = 0.0"]

    schema_code = f"""from pydantic import BaseModel
from typing import Optional, Any

class InferenceRequest(BaseModel):
{chr(10).join('    ' + f for f in fields)}

class InferenceResponse(BaseModel):
    prediction: Any
    probability: Optional[float] = None
    model_version: str
    run_id: str
"""
    with open(api_dir / "schema.py", "w", encoding="utf-8") as f:
        f.write(schema_code)

    main_code = f"""from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Any, Optional
import pickle
import os
import pandas as pd
from .schema import InferenceRequest, InferenceResponse

app = FastAPI(title="MK-Path Verified Model API")

MODEL_VERSION = "{model_version}"
RUN_ID = "{run_id}"

model = None
MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "model", "model.pkl")

@app.on_event("startup")
def load_model():
    global model
    try:
        with open(MODEL_PATH, "rb") as f:
            model = pickle.load(f)
    except Exception as e:
        print(f"Failed to load model: {{e}}")
        model = None

@app.get("/health")
def health():
    if model is None:
        raise HTTPException(status_code=503, detail="Model loading failed")
    return {{"status": "healthy", "model_version": MODEL_VERSION}}

@app.get("/metadata")
def metadata():
    return {{"run_id": RUN_ID, "model_version": MODEL_VERSION, "features": {list(feature_schema.keys()) if feature_schema else ['feature_1']}}}

@app.get("/model-card")
def model_card():
    card_path = os.path.join(os.path.dirname(__file__), "..", "MODEL_CARD.md")
    if os.path.exists(card_path):
        with open(card_path, "r", encoding="utf-8") as f:
            return {{"model_card": f.read()}}
    return {{"model_card": "Not found"}}

@app.post("/predict", response_model=InferenceResponse)
def predict(req: InferenceRequest):
    if model is None:
        raise HTTPException(status_code=503, detail="Model loading failed")
    
    try:
        df = pd.DataFrame([req.model_dump()])
        pred = model.predict(df)[0]
        prob = None
        if hasattr(model, "predict_proba"):
            try:
                prob_arr = model.predict_proba(df)
                if prob_arr.shape[1] > 1:
                    prob = float(prob_arr[0][1])
            except Exception:
                prob = None
        
        return InferenceResponse(
            prediction=str(pred) if not isinstance(pred, (int, float)) else pred,
            probability=prob,
            model_version=MODEL_VERSION,
            run_id=RUN_ID
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
"""
    with open(api_dir / "main.py", "w", encoding="utf-8") as f:
        f.write(main_code)

    # 4. MODEL_CARD.md
    with open(artifact_dir / "MODEL_CARD.md", "w", encoding="utf-8") as f:
        f.write("# Model Card\n\n")
        f.write(f"Model ID: {model_version}\n")
        f.write(f"Run ID: {run_id}\n")
        f.write(f"Generated At: {datetime.now(timezone.utc).isoformat()}\n")
        f.write("Verification: PASS\n")

    # 5. README.md
    with open(artifact_dir / "README.md", "w", encoding="utf-8") as f:
        f.write("# Deployment Instructions\n")
        f.write("1. Start API: `uvicorn api.main:app --host 0.0.0.0 --port 8000`\n")

    # Perform Artifact Validation
    val_res = validate_artifact(artifact_dir, feature_schema)
    logger.info(f"Artifact validation for {project_id}/{run_id}: {val_res}")

    meta = {
        "artifact_dir": str(artifact_dir),
        "model_version": model_version,
        "run_id": run_id,
        "status": val_res["status"],
        "validation": val_res,
        "downloadable": (val_res["status"] == "PASS")
    }
    
    with open(artifact_dir / "metadata.json", "w", encoding="utf-8") as f:
        f.write(json.dumps(meta, indent=2))

    return meta
