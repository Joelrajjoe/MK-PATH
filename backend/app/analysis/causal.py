from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional
import pandas as pd

logger = logging.getLogger("mkpath.analysis.causal")

class CausalReport:
    def __init__(self, treatment: str, outcome: str, effect_estimate: float, assumptions: List[str], refutation_results: Dict[str, Any]):
        self.treatment = treatment
        self.outcome = outcome
        self.effect_estimate = effect_estimate
        self.assumptions = assumptions
        self.refutation_results = refutation_results

    def to_dict(self):
        return {
            "treatment": self.treatment,
            "outcome": self.outcome,
            "effect_estimate": self.effect_estimate,
            "assumptions": self.assumptions,
            "refutation_results": self.refutation_results,
            "caveat": "Estimated treatment effect is reported under the stated assumptions. This system does not automatically claim definitive causality.",
            "generated_at": datetime.now(timezone.utc).isoformat()
        }

def run_causal_analysis(df: pd.DataFrame, treatment: str, outcome: str, confounders: List[str]) -> Optional[CausalReport]:
    """
    Run causal analysis using DoWhy if applicable.
    Workflow: Business Question -> Treatment -> Outcome -> Confounders -> Causal Graph -> Identification -> Estimation -> Refutation
    """
    try:
        import dowhy
        from dowhy import CausalModel
        
        # 1. Causal Graph & Model Setup
        model = CausalModel(
            data=df,
            treatment=treatment,
            outcome=outcome,
            common_causes=confounders,
            instruments=[]
        )
        
        # 2. Identification
        identified_estimand = model.identify_effect(proceed_when_unidentifiable=True)
        
        # 3. Estimation
        estimate = model.estimate_effect(
            identified_estimand,
            method_name="backdoor.linear_regression",
            test_significance=True
        )
        
        # 4. Refutation
        refute_results = model.refute_estimate(
            identified_estimand, 
            estimate, 
            method_name="random_common_cause"
        )
        
        assumptions = [
            f"Unconfoundedness: No unmeasured confounders outside of {confounders}.",
            "Linearity: The relationship between treatment and outcome is modeled linearly.",
            "Positivity: All units have a non-zero probability of receiving treatment."
        ]
        
        return CausalReport(
            treatment=treatment,
            outcome=outcome,
            effect_estimate=float(estimate.value),
            assumptions=assumptions,
            refutation_results={
                "method": "random_common_cause",
                "estimated_effect": float(estimate.value),
                "new_effect": float(refute_results.new_effect)
            }
        )
    except ImportError:
        logger.warning("DoWhy not installed. Skipping causal analysis.")
        return None
    except Exception as e:
        logger.warning(f"Causal analysis failed: {e}")
        return None
