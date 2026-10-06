from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional
import pandas as pd
import numpy as np

logger = logging.getLogger("mkpath.verification.explainability")

class ExplainabilityReport:
    def __init__(self, global_importance: Dict[str, float], impact_summary: str):
        self.global_importance = global_importance
        self.impact_summary = impact_summary

    def to_dict(self):
        return {
            "global_importance": self.global_importance,
            "impact_summary": self.impact_summary,
            "generated_at": datetime.now(timezone.utc).isoformat()
        }

def run_shap_explainability(model: Any, X: pd.DataFrame) -> Optional[ExplainabilityReport]:
    """
    Run SHAP explainability on a model.
    """
    try:
        import shap
        
        # Use TreeExplainer for tree models, LinearExplainer for linear, or KernelExplainer
        # Mocking for generic case: we assume tree model for this test
        explainer = shap.Explainer(model)
        shap_values = explainer(X)
        
        # Calculate mean absolute SHAP values for global importance
        vals = np.abs(shap_values.values).mean(0)
        feature_importance = pd.DataFrame(list(zip(X.columns, vals)), columns=['col_name', 'feature_importance_vals'])
        feature_importance.sort_values(by=['feature_importance_vals'], ascending=False, inplace=True)
        
        global_imp = dict(zip(feature_importance['col_name'], feature_importance['feature_importance_vals']))
        
        top_feature = feature_importance.iloc[0]['col_name']
        summary = f"The model's predictions are primarily driven by '{top_feature}', followed by other features shown in the importance map."
        
        return ExplainabilityReport(global_importance=global_imp, impact_summary=summary)
    except ImportError:
        logger.warning("SHAP not installed. Skipping explainability.")
        return None
    except Exception as e:
        logger.warning(f"SHAP explainability failed: {e}")
        return None
