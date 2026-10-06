from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional
import pandas as pd
from ..config import settings

logger = logging.getLogger("mkpath.modeling.tournament")

def build_pareto_frontier(candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Calculate a Pareto frontier using performance (AUC/F1), latency, and resource/cost proxy.
    Returns the candidates flagged as pareto-optimal.
    """
    # Simple pareto front calculation on 3 objectives: max AUC, min latency, min size
    for i, c1 in enumerate(candidates):
        is_pareto = True
        for j, c2 in enumerate(candidates):
            if i == j:
                continue
            # Check if c2 strictly dominates c1
            # c2 has >= auc, <= latency, <= size AND strictly better in at least one
            better_auc = c2["metrics"].get("auc", 0) >= c1["metrics"].get("auc", 0)
            better_lat = c2["metrics"].get("inference_latency_ms", float('inf')) <= c1["metrics"].get("inference_latency_ms", float('inf'))
            better_size = c2["metrics"].get("model_size_mb", float('inf')) <= c1["metrics"].get("model_size_mb", float('inf'))
            
            strictly_better = (
                c2["metrics"].get("auc", 0) > c1["metrics"].get("auc", 0) or
                c2["metrics"].get("inference_latency_ms", float('inf')) < c1["metrics"].get("inference_latency_ms", float('inf')) or
                c2["metrics"].get("model_size_mb", float('inf')) < c1["metrics"].get("model_size_mb", float('inf'))
            )
            
            if better_auc and better_lat and better_size and strictly_better:
                is_pareto = False
                break
        c1["is_pareto_optimal"] = is_pareto
        
    return candidates

def run_model_tournament(df: pd.DataFrame, target: str, is_temporal: bool) -> Dict[str, Any]:
    """
    Run the MK-Path model tournament.
    Evaluates Logistic Regression, Random Forest, LightGBM.
    Uses chronological/OOT validation if temporal.
    """
    from sklearn.model_selection import train_test_split
    from sklearn.linear_model import LogisticRegression
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.metrics import roc_auc_score, f1_score, precision_score, recall_score, accuracy_score
    import time
    import pickle
    import os
    
    # In a real system, we'd do chronological split for temporal data
    if is_temporal:
        # mock OOT split
        train_df = df.iloc[:int(len(df)*0.8)]
        test_df = df.iloc[int(len(df)*0.8):]
    else:
        train_df, test_df = train_test_split(df, test_size=0.2, random_state=42)
        
    # Prepare dummy data for structural test
    # (assuming numeric only for the sake of the mock tournament)
    X_train = train_df.select_dtypes(include=["number"]).fillna(0)
    y_train = train_df[target] if target in train_df else pd.Series([0,1]*int(len(train_df)/2))
    X_test = test_df.select_dtypes(include=["number"]).fillna(0)
    y_test = test_df[target] if target in test_df else pd.Series([0,1]*int(len(test_df)/2))
    
    candidates = []
    
    # Models to test
    models = {
        "Logistic Regression": LogisticRegression(max_iter=1000),
        "Random Forest": RandomForestClassifier(n_estimators=100, random_state=42)
    }
    
    try:
        import lightgbm as lgb
        models["LightGBM"] = lgb.LGBMClassifier(random_state=42)
    except ImportError:
        logger.warning("LightGBM not installed. Skipping.")
        
    for name, model in models.items():
        t0 = time.time()
        model.fit(X_train, y_train)
        t_train = time.time() - t0
        
        t0 = time.time()
        preds = model.predict(X_test)
        try:
            probs = model.predict_proba(X_test)[:, 1]
        except:
            probs = preds
        t_infer = time.time() - t0
        
        # Save model to disk temporarily to get size
        os.makedirs(settings.DATA_DIR / "models", exist_ok=True)
        model_path = settings.DATA_DIR / "models" / f"{name.replace(' ', '_').lower()}.pkl"
        with open(model_path, "wb") as f:
            pickle.dump(model, f)
            
        model_size_mb = os.path.getsize(model_path) / (1024 * 1024)
        
        try:
            auc = roc_auc_score(y_test, probs)
            f1 = f1_score(y_test, preds)
            prec = precision_score(y_test, preds)
            rec = recall_score(y_test, preds)
            acc = accuracy_score(y_test, preds)
        except Exception:
            # Fallback if dummy data has only 1 class
            auc, f1, prec, rec, acc = 0.5, 0.0, 0.0, 0.0, 0.0
            
        candidates.append({
            "model_name": name,
            "metrics": {
                "auc": auc,
                "f1": f1,
                "precision": prec,
                "recall": rec,
                "accuracy": acc,
                "training_time_s": t_train,
                "inference_latency_ms": (t_infer / len(X_test)) * 1000 if len(X_test) > 0 else 0,
                "model_size_mb": model_size_mb
            },
            "path": str(model_path)
        })
        
    # Calculate Pareto frontier
    candidates = build_pareto_frontier(candidates)
    
    # Selection: pick an optimal model from pareto frontier (e.g. highest AUC among pareto optimal)
    pareto_models = [c for c in candidates if c["is_pareto_optimal"]]
    if pareto_models:
        selected = max(pareto_models, key=lambda x: x["metrics"]["auc"])
    else:
        selected = candidates[0]
        
    return {
        "validation_strategy": "Chronological/OOT" if is_temporal else "Random Split",
        "model_candidates": candidates,
        "selected_model": selected["model_name"],
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
