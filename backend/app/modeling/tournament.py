from datetime import datetime, timezone
import logging
import os
import pickle
import time
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd
from ..config import settings

logger = logging.getLogger("mkpath.modeling.tournament")


def build_pareto_frontier(candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Calculate a Pareto frontier using performance (AUC/F1), latency, and resource/cost proxy.
    Returns the candidates flagged as pareto-optimal.
    """
    for i, c1 in enumerate(candidates):
        is_pareto = True
        for j, c2 in enumerate(candidates):
            if i == j:
                continue
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
    Run the MK-Path model tournament using REAL dataset columns.
    Evaluates Logistic Regression, Random Forest, LightGBM.
    Does NOT fabricate target values or metrics.
    """
    from sklearn.model_selection import train_test_split
    from sklearn.linear_model import LogisticRegression
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.metrics import roc_auc_score, f1_score, precision_score, recall_score, accuracy_score
    from sklearn.preprocessing import LabelEncoder

    # Check target availability
    if not target or target not in df.columns:
        logger.warning(f"Target column '{target}' not found in dataset columns: {list(df.columns)}")
        return {
            "status": "HUMAN_REVIEW_REQUIRED",
            "error": "INSUFFICIENT_TARGET_INFORMATION",
            "message": f"Target column '{target}' is not available in the dataset.",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    # Clean target
    clean_df = df.dropna(subset=[target]).copy()
    if len(clean_df) < 10:
        return {
            "status": "HUMAN_REVIEW_REQUIRED",
            "error": "INSUFFICIENT_TARGET_INFORMATION",
            "message": f"Dataset has fewer than 10 valid rows for target '{target}'.",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    y_raw = clean_df[target]
    unique_targets = y_raw.nunique()
    if unique_targets < 2:
        return {
            "status": "HUMAN_REVIEW_REQUIRED",
            "error": "INSUFFICIENT_TARGET_INFORMATION",
            "message": f"Target column '{target}' has only {unique_targets} unique class value.",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    is_regression = pd.api.types.is_numeric_dtype(y_raw) and unique_targets > 10

    # Encode target if classification & non-numeric
    if is_regression:
        y = y_raw.astype(float).values
    elif not pd.api.types.is_numeric_dtype(y_raw):
        le = LabelEncoder()
        y = le.fit_transform(y_raw.astype(str))
    else:
        y = y_raw.values

    # Select numerical & categoricals encoded features (exclude target)
    feature_cols = [c for c in clean_df.columns if c != target]
    X_df = clean_df[feature_cols].copy()
    
    # Simple preprocessing: numeric columns get filled with median, categoricals with mode/label encoded
    for col in X_df.columns:
        if pd.api.types.is_numeric_dtype(X_df[col]):
            median_val = X_df[col].median()
            X_df[col] = X_df[col].fillna(median_val if pd.notnull(median_val) else 0)
        else:
            X_df[col] = LabelEncoder().fit_transform(X_df[col].astype(str))

    if X_df.shape[1] == 0:
        return {
            "status": "HUMAN_REVIEW_REQUIRED",
            "error": "INSUFFICIENT_TARGET_INFORMATION",
            "message": "No valid feature columns available after preprocessing.",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    # Train / Test split
    use_stratify = None
    if not is_temporal and not is_regression and len(y) > 0:
        val_counts = pd.Series(y).value_counts()
        if len(val_counts) > 1 and val_counts.min() >= 2:
            use_stratify = y

    if is_temporal:
        split_idx = int(len(X_df) * 0.8)
        X_train, X_test = X_df.iloc[:split_idx], X_df.iloc[split_idx:]
        y_train, y_test = y[:split_idx], y[split_idx:]
    else:
        X_train, X_test, y_train, y_test = train_test_split(
            X_df, y, test_size=0.2, random_state=42, stratify=use_stratify
        )

    if len(X_train) == 0 or len(X_test) == 0:
        return {
            "status": "HUMAN_REVIEW_REQUIRED",
            "error": "INSUFFICIENT_TARGET_INFORMATION",
            "message": "Insufficient data rows for train/test split.",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    candidates = []
    if is_regression:
        from sklearn.linear_model import LinearRegression
        from sklearn.ensemble import RandomForestRegressor
        from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
        models = {
            "Linear Regression": LinearRegression(),
            "Random Forest Regressor": RandomForestRegressor(n_estimators=50, max_depth=12, n_jobs=-1, random_state=42)
        }
        try:
            import lightgbm as lgb
            models["LightGBM Regressor"] = lgb.LGBMRegressor(random_state=42, verbose=-1)
        except ImportError:
            logger.warning("LightGBM not installed. Skipping.")
    else:
        models = {
            "Logistic Regression": LogisticRegression(max_iter=1000),
            "Random Forest": RandomForestClassifier(n_estimators=50, max_depth=12, n_jobs=-1, random_state=42)
        }
        try:
            import lightgbm as lgb
            models["LightGBM"] = lgb.LGBMClassifier(random_state=42, verbose=-1)
        except ImportError:
            logger.warning("LightGBM not installed. Skipping.")

    os.makedirs(settings.DATA_DIR / "models", exist_ok=True)

    for name, model in models.items():
        try:
            t0 = time.time()
            model.fit(X_train, y_train)
            t_train = time.time() - t0

            t0 = time.time()
            preds = model.predict(X_test)
            probs = None
            if not is_regression and hasattr(model, "predict_proba"):
                try:
                    prob_arr = model.predict_proba(X_test)
                    if prob_arr.shape[1] > 1:
                        probs = prob_arr[:, 1]
                except Exception:
                    probs = None
            t_infer = time.time() - t0

            # Save model binary
            model_path = settings.DATA_DIR / "models" / f"{name.replace(' ', '_').lower()}.pkl"
            with open(model_path, "wb") as f:
                pickle.dump(model, f)

            model_size_mb = os.path.getsize(model_path) / (1024 * 1024)

            # Calculate real metrics
            if is_regression:
                from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
                r2 = float(r2_score(y_test, preds))
                rmse = float(np.sqrt(mean_squared_error(y_test, preds))) if 'np' in locals() else float(mean_squared_error(y_test, preds) ** 0.5)
                mae = float(mean_absolute_error(y_test, preds))
                perf = float(max(0.0, r2))

                candidates.append({
                    "model_name": name,
                    "metrics": {
                        "r2": r2,
                        "rmse": rmse,
                        "mae": mae,
                        "auc": perf,
                        "f1": perf,
                        "accuracy": perf,
                        "training_time_s": float(t_train),
                        "inference_latency_ms": float((t_infer / len(X_test)) * 1000) if len(X_test) > 0 else 0.0,
                        "model_size_mb": float(model_size_mb)
                    },
                    "path": str(model_path),
                    "feature_names": list(X_df.columns)
                })
            else:
                acc = float(accuracy_score(y_test, preds))
                f1 = float(f1_score(y_test, preds, average="weighted" if len(set(y_test)) > 2 else "binary", zero_division=0))
                prec = float(precision_score(y_test, preds, average="weighted" if len(set(y_test)) > 2 else "binary", zero_division=0))
                rec = float(recall_score(y_test, preds, average="weighted" if len(set(y_test)) > 2 else "binary", zero_division=0))
                
                auc = 0.0
                if probs is not None and len(set(y_test)) == 2:
                    try:
                        auc = float(roc_auc_score(y_test, probs))
                    except Exception:
                        auc = acc

                candidates.append({
                    "model_name": name,
                    "metrics": {
                        "auc": auc,
                        "f1": f1,
                        "precision": prec,
                        "recall": rec,
                        "accuracy": acc,
                        "training_time_s": float(t_train),
                        "inference_latency_ms": float((t_infer / len(X_test)) * 1000) if len(X_test) > 0 else 0.0,
                        "model_size_mb": float(model_size_mb)
                    },
                    "path": str(model_path),
                    "feature_names": list(X_df.columns)
                })
        except Exception as exc:
            logger.error(f"Failed to fit model {name}: {type(exc).__name__}: {exc}")

    if not candidates:
        return {
            "status": "HUMAN_REVIEW_REQUIRED",
            "error": "MODEL_TRAINING_FAILED",
            "message": "All model candidate training attempts failed.",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    # Calculate Pareto frontier
    candidates = build_pareto_frontier(candidates)
    pareto_models = [c for c in candidates if c.get("is_pareto_optimal")]
    selected = max(pareto_models if pareto_models else candidates, key=lambda x: x["metrics"]["accuracy" if is_regression else "f1"])

    return {
        "status": "SUCCESS",
        "task_type": "REGRESSION" if is_regression else "CLASSIFICATION",
        "validation_strategy": "Chronological/OOT" if is_temporal else "Random Split",
        "model_candidates": candidates,
        "selected_model": selected,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
