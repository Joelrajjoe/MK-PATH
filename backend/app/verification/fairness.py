from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional
import pandas as pd

logger = logging.getLogger("mkpath.verification.fairness")

class FairnessReport:
    def __init__(self, sensitive_attribute: str, metrics: Dict[str, Any], disparity_exceeds_threshold: bool, threshold: float):
        self.sensitive_attribute = sensitive_attribute
        self.metrics = metrics
        self.disparity_exceeds_threshold = disparity_exceeds_threshold
        self.threshold = threshold

    def to_dict(self):
        return {
            "sensitive_attribute": self.sensitive_attribute,
            "metrics": self.metrics,
            "disparity_exceeds_threshold": self.disparity_exceeds_threshold,
            "threshold": self.threshold,
            "generated_at": datetime.now(timezone.utc).isoformat()
        }

def run_fairness_analysis(df: pd.DataFrame, target: str, prediction: str, sensitive_attribute: Optional[str], threshold: float = 0.2) -> Optional[FairnessReport]:
    """
    Run fairness analysis for a given sensitive attribute.
    Only run when a meaningful protected/group attribute exists.
    Example metrics: selection rate, TPR, FPR.
    """
    if not sensitive_attribute or sensitive_attribute not in df.columns:
        logger.info("No sensitive attribute provided or found. Skipping fairness analysis.")
        return None
        
    try:
        from sklearn.metrics import confusion_matrix
        
        groups = df[sensitive_attribute].unique()
        metrics_by_group = {}
        
        for g in groups:
            group_df = df[df[sensitive_attribute] == g]
            y_true = group_df[target]
            y_pred = group_df[prediction]
            
            if len(y_true) == 0:
                continue
                
            tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
            
            selection_rate = (tp + fp) / len(y_true)
            tpr = tp / (tp + fn) if (tp + fn) > 0 else 0
            fpr = fp / (fp + tn) if (fp + tn) > 0 else 0
            
            metrics_by_group[str(g)] = {
                "selection_rate": selection_rate,
                "tpr": tpr,
                "fpr": fpr,
                "count": len(y_true)
            }
            
        # Check for disparity
        # Example disparity check: ratio of min selection rate to max selection rate
        rates = [m["selection_rate"] for m in metrics_by_group.values() if m["selection_rate"] > 0]
        if len(rates) >= 2:
            disparity = 1.0 - (min(rates) / max(rates))
        else:
            disparity = 0.0
            
        exceeds = disparity > threshold
        
        return FairnessReport(
            sensitive_attribute=sensitive_attribute,
            metrics=metrics_by_group,
            disparity_exceeds_threshold=exceeds,
            threshold=threshold
        )
        
    except Exception as e:
        logger.warning(f"Fairness analysis failed: {e}")
        return None
