from typing import Any, Dict, List, Optional, TypedDict

class MKPathState(TypedDict, total=False):
    project_id: str
    user_id: str
    run_id: str
    dataset_id: str
    dataset_ids: List[str]
    business_goal: str
    schema: Dict[str, Any]
    profile: Dict[str, Any]
    semantic_context: Dict[str, Any]
    ambiguities: List[Dict[str, Any]]
    user_decisions: List[Dict[str, Any]]
    analysis_plan: Dict[str, Any]
    analysis_results: Dict[str, Any]
    temporal_report: Dict[str, Any]
    causal_report: Dict[str, Any]
    model_candidates: List[Dict[str, Any]]
    selected_model: Dict[str, Any]
    verification_results: Dict[str, Any]
    artifacts: List[Dict[str, Any]]
    audit_events: List[Dict[str, Any]]
    status: str
    errors: List[str]
