from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional
from pydantic import BaseModel

logger = logging.getLogger("mkpath.verification.engine")

class GateResult(BaseModel):
    gate_id: str
    status: str  # PASS, FAIL, WARNING, HUMAN_REVIEW
    severity: str
    evidence: List[str]
    metrics: Dict[str, Any]
    threshold: Optional[float]
    reason: str
    recommendation: str
    timestamp: str

class VerificationSummary(BaseModel):
    overall_status: str
    passed_gates: int
    failed_gates: int
    warning_gates: int
    human_review_gates: int
    results: List[GateResult]

class DeploymentReadinessReport(BaseModel):
    project_id: str
    run_id: str
    deployment_status: str  # READY, BLOCKED
    summary: VerificationSummary
    generated_at: str

def run_verification_gates(project_id: str, run_id: str, context: Dict[str, Any]) -> DeploymentReadinessReport:
    """
    Run the central MK-Path Verification Engine.
    Executes mandatory deterministic gates.
    """
    results: List[GateResult] = []
    
    # 1. Data Quality Gate
    dq_score = context.get("data_quality_score", 100)
    dq_status = "PASS" if dq_score >= 80 else "FAIL"
    results.append(GateResult(
        gate_id="data_quality",
        status=dq_status,
        severity="HIGH",
        evidence=[f"Quality Score: {dq_score}"],
        metrics={"score": dq_score},
        threshold=80.0,
        reason="Score is below threshold" if dq_status == "FAIL" else "Score is acceptable",
        recommendation="Heal data before modeling." if dq_status == "FAIL" else "Proceed",
        timestamp=datetime.now(timezone.utc).isoformat()
    ))
    
    # 2. Semantic Validity Gate
    # 3. Temporal Leakage Gate
    temporal_risk = context.get("temporal_leakage_risk", "LOW")
    temp_status = "FAIL" if temporal_risk == "HIGH" else "PASS"
    results.append(GateResult(
        gate_id="temporal_leakage",
        status=temp_status,
        severity="CRITICAL",
        evidence=["Temporal leakage intercepted"] if temp_status == "FAIL" else ["No temporal leakage"],
        metrics={"risk": temporal_risk},
        threshold=None,
        reason="feature unavailable at prediction time" if temp_status == "FAIL" else "Clean",
        recommendation="Remove feature" if temp_status == "FAIL" else "Proceed",
        timestamp=datetime.now(timezone.utc).isoformat()
    ))

    # 4. Plan-Multiverse Stability Gate (PMSG)
    pmsg_status = context.get("pmsg_status")
    pmsg_metrics = context.get("pmsg_metrics", {})
    pmsg_reason = context.get("pmsg_reason")
    if pmsg_status in ("PASS", "WARNING", "FAIL", "HUMAN_REVIEW"):
        gate_pmsg_status = pmsg_status
        evidence_list = [
            f"Stability Gate: {pmsg_status}",
            f"Persistence: {pmsg_metrics.get('top_category_persistence', 'N/A')}",
            f"Spearman Rho: {pmsg_metrics.get('spearman_rank_correlation', 'N/A')}",
            f"Reversal Rate: {pmsg_metrics.get('conclusion_reversal_rate', 'N/A')}",
        ]
        reason_txt = pmsg_reason or ("All predefined stability conditions passed" if pmsg_status == "PASS" else "Sensitivity or reversal detected across analytical variants")
        rec_txt = "Proceed with deployment." if pmsg_status == "PASS" else ("Examine sensitive variants before high-stakes deployment." if pmsg_status == "WARNING" else "Resolve analytical instability before deployment.")
    else:
        gate_pmsg_status = "WARNING"
        evidence_list = ["No PMSG run executed yet for this project finding"]
        reason_txt = "Analytical stability has not yet been demonstrated across alternative specifications"
        rec_txt = "Execute the Plan-Multiverse Stability Gate before production deployment."

    results.append(GateResult(
        gate_id="plan_multiverse_stability",
        status=gate_pmsg_status,
        severity="CRITICAL",
        evidence=evidence_list,
        metrics=pmsg_metrics,
        threshold=0.80,
        reason=reason_txt,
        recommendation=rec_txt,
        timestamp=datetime.now(timezone.utc).isoformat()
    ))

    # 5. Causal Validation Gate
    # 6. Explainability Gate
    # 7. Fairness Gate
    # 8. Artifact Validation Gate

    # Deployment logic
    failed_gates = [g for g in results if g.status == "FAIL"]
    deployment_status = "BLOCKED" if failed_gates else "READY"
    
    summary = VerificationSummary(
        overall_status="BLOCKED" if failed_gates else "READY",
        passed_gates=len([g for g in results if g.status == "PASS"]),
        failed_gates=len(failed_gates),
        warning_gates=len([g for g in results if g.status == "WARNING"]),
        human_review_gates=len([g for g in results if g.status == "HUMAN_REVIEW"]),
        results=results
    )
    
    return DeploymentReadinessReport(
        project_id=project_id,
        run_id=run_id,
        deployment_status=deployment_status,
        summary=summary,
        generated_at=datetime.now(timezone.utc).isoformat()
    )
