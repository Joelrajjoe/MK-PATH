import logging
from typing import Any, Dict

from langgraph.graph import END, START, StateGraph

from .state import MKPathState
from ..audit import record_audit

logger = logging.getLogger("mkpath.orchestrator")

async def node_ingest(state: MKPathState) -> Dict[str, Any]:
    logger.info("Running INGEST")
    await record_audit("INGEST_START", project_id=state.get("project_id"), status="running")
    # Ingestion logic is typically decoupled via API, but graph tracks status.
    return {"status": "PROFILE"}

async def node_profile(state: MKPathState) -> Dict[str, Any]:
    logger.info("Running PROFILE")
    await record_audit("PROFILE_START", project_id=state.get("project_id"), status="running")
    return {"status": "SEMANTIC_ANALYSIS"}

async def node_semantic_analysis(state: MKPathState) -> Dict[str, Any]:
    logger.info("Running SEMANTIC_ANALYSIS")
    await record_audit("SEMANTIC_ANALYSIS", project_id=state.get("project_id"), status="running")
    # Determine if ambiguities exist
    ambiguities = state.get("ambiguities", [])
    if not ambiguities:
        # Mock detection: normally this comes from semantic layer
        ambiguities = []
    
    return {"status": "AMBIGUITY_CHECK", "ambiguities": ambiguities}

def check_ambiguity(state: MKPathState) -> str:
    ambiguities = state.get("ambiguities", [])
    if ambiguities and len(ambiguities) > len(state.get("user_decisions", [])):
        return "HUMAN_BREAKPOINT"
    return "ANALYSIS_PLANNING"

async def node_human_breakpoint(state: MKPathState) -> Dict[str, Any]:
    logger.info("Running HUMAN_BREAKPOINT")
    await record_audit("HUMAN_BREAKPOINT", project_id=state.get("project_id"), status="paused")
    # LangGraph will pause here since we can interrupt before or after.
    # Actually, we rely on LangGraph's interrupt features.
    return {"status": "PAUSED_FOR_INPUT"}

async def node_analysis_planning(state: MKPathState) -> Dict[str, Any]:
    logger.info("Running ANALYSIS_PLANNING")
    await record_audit("ANALYSIS_PLANNING", project_id=state.get("project_id"), status="running")
    return {"status": "DATA_ANALYST"}

async def node_data_analyst(state: MKPathState) -> Dict[str, Any]:
    logger.info("Running DATA_ANALYST")
    await record_audit("DATA_ANALYST_START", project_id=state.get("project_id"), status="running")
    
    # We would actually fetch the dataset schema, profile, etc.
    # For now we'll mock the execution call using the state
    from ..analysis.analyst import generate_plan, execute_plan
    
    # Mocking execution in state graph
    # If the state doesn't have an analysis_plan yet, we could generate one:
    # plan = generate_plan(state.get("business_goal"), state.get("schema"), state.get("profile"), state.get("semantic_context"))
    # results = execute_plan(plan, {"dataset_id": "mock_id", "table_name": "mock_table"})
    
    return {"status": "DATA_SCIENTIST"}

async def node_data_scientist(state: MKPathState) -> Dict[str, Any]:
    logger.info("Running DATA_SCIENTIST")
    return {"status": "VERIFICATION"}

async def node_verification(state: MKPathState) -> Dict[str, Any]:
    logger.info("Running VERIFICATION")
    await record_audit("VERIFICATION_START", project_id=state.get("project_id"), status="running")
    
    from ..verification.engine import run_verification_gates
    
    # Mocking execution with state
    report = run_verification_gates(state.get("project_id", "project_1"), state.get("run_id", "run_1"), {"temporal_leakage_risk": "LOW"})
    
    return {
        "status": "MODEL_TOURNAMENT",
        "verification_results": report.model_dump()
    }

async def node_model_tournament(state: MKPathState) -> Dict[str, Any]:
    logger.info("Running MODEL_TOURNAMENT")
    return {"status": "ML_ENGINEER"}

async def node_ml_engineer(state: MKPathState) -> Dict[str, Any]:
    logger.info("Running ML_ENGINEER")
    from ..engineering.ml_engineer import generate_deployment_artifacts
    
    # Generate artifacts based on verification results
    verif_results = state.get("verification_results", {})
    # If no verification results exist, default to BLOCKED
    if not verif_results:
        verif_results = {"deployment_status": "BLOCKED"}
        
    model_info = state.get("selected_model", {"model_name": "unknown"})
    feature_schema = state.get("schema", {"feature_1": "float"})
    path = generate_deployment_artifacts(state.get("project_id", "project_1"), state.get("run_id", "run_1"), verif_results, model_info, feature_schema)
    
    return {
        "status": "ARTIFACT_GENERATION",
        "artifacts": [{"path": path}]
    }

async def node_artifact_generation(state: MKPathState) -> Dict[str, Any]:
    logger.info("Running ARTIFACT_GENERATION")
    return {"status": "AUDIT"}

async def node_audit(state: MKPathState) -> Dict[str, Any]:
    logger.info("Running AUDIT")
    await record_audit("WORKFLOW_COMPLETED", project_id=state.get("project_id"), status="ok")
    return {"status": "COMPLETED"}


def build_graph() -> StateGraph:
    workflow = StateGraph(MKPathState)

    workflow.add_node("INGEST", node_ingest)
    workflow.add_node("PROFILE", node_profile)
    workflow.add_node("SEMANTIC_ANALYSIS", node_semantic_analysis)
    workflow.add_node("HUMAN_BREAKPOINT", node_human_breakpoint)
    workflow.add_node("ANALYSIS_PLANNING", node_analysis_planning)
    workflow.add_node("DATA_ANALYST", node_data_analyst)
    workflow.add_node("DATA_SCIENTIST", node_data_scientist)
    workflow.add_node("VERIFICATION", node_verification)
    workflow.add_node("MODEL_TOURNAMENT", node_model_tournament)
    workflow.add_node("ML_ENGINEER", node_ml_engineer)
    workflow.add_node("ARTIFACT_GENERATION", node_artifact_generation)
    workflow.add_node("AUDIT", node_audit)

    workflow.add_edge(START, "INGEST")
    workflow.add_edge("INGEST", "PROFILE")
    workflow.add_edge("PROFILE", "SEMANTIC_ANALYSIS")
    
    workflow.add_conditional_edges(
        "SEMANTIC_ANALYSIS",
        check_ambiguity,
        {
            "HUMAN_BREAKPOINT": "HUMAN_BREAKPOINT",
            "ANALYSIS_PLANNING": "ANALYSIS_PLANNING"
        }
    )

    # After human breakpoint, it resumes back to semantic analysis to re-check
    workflow.add_edge("HUMAN_BREAKPOINT", "SEMANTIC_ANALYSIS")
    
    workflow.add_edge("ANALYSIS_PLANNING", "DATA_ANALYST")
    workflow.add_edge("DATA_ANALYST", "DATA_SCIENTIST")
    workflow.add_edge("DATA_SCIENTIST", "VERIFICATION")
    workflow.add_edge("VERIFICATION", "MODEL_TOURNAMENT")
    workflow.add_edge("MODEL_TOURNAMENT", "ML_ENGINEER")
    workflow.add_edge("ML_ENGINEER", "ARTIFACT_GENERATION")
    workflow.add_edge("ARTIFACT_GENERATION", "AUDIT")
    workflow.add_edge("AUDIT", END)

    return workflow

def get_compiled_graph():
    from langgraph.checkpoint.memory import MemorySaver
    memory = MemorySaver()
    # Interrupt before HUMAN_BREAKPOINT to pause and wait for user
    return build_graph().compile(checkpointer=memory, interrupt_before=["HUMAN_BREAKPOINT"])
