from datetime import datetime, timezone
from typing import Any, Dict, List
import logging

logger = logging.getLogger("mkpath.verification.leakage")

class TemporalLeakageReport:
    def __init__(self, status: str, risk_level: str, flagged_features: List[Dict[str, Any]], evidence: List[str], recommendations: List[str]):
        self.status = status
        self.risk_level = risk_level
        self.flagged_features = flagged_features
        self.evidence = evidence
        self.recommendations = recommendations

    def to_dict(self):
        return {
            "status": self.status,
            "risk_level": self.risk_level,
            "flagged_features": self.flagged_features,
            "evidence": self.evidence,
            "recommendations": self.recommendations,
            "generated_at": datetime.now(timezone.utc).isoformat()
        }

def check_temporal_leakage(features: List[Dict[str, Any]], target_time: str, prediction_time: str) -> TemporalLeakageReport:
    """
    Check if any feature is available after prediction time.
    `features` should be a list of dicts with keys: feature_name, source_table, event_time, available_time, transformation, source_column.
    """
    flagged = []
    evidence = []
    
    # Deterministic check: available_time <= prediction_time
    for f in features:
        feature_name = f.get("feature_name", "unknown")
        available_time = f.get("available_time")
        
        if not available_time:
            continue
            
        if available_time > prediction_time:
            f["leakage_risk"] = "HIGH"
            f["reason"] = f"available_time ({available_time}) > prediction_time ({prediction_time})"
            flagged.append(f)
            evidence.append(f"Feature {feature_name} from table {f.get('source_table')} has available_time {available_time} which is after prediction_time {prediction_time}.")

    status = "FAIL" if flagged else "PASS"
    risk_level = "HIGH" if flagged else "LOW"
    recommendations = ["Remove HIGH risk features or adjust prediction_time."] if flagged else ["No temporal leakage detected."]
    
    return TemporalLeakageReport(status, risk_level, flagged, evidence, recommendations)
