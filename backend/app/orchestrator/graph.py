import logging
import json
from typing import Any, Dict, List
import pandas as pd

from langgraph.graph import END, START, StateGraph

from .state import MKPathState
from ..audit import record_audit
from ..repo import get_dataset
from ..profiling.profiler import build_quality_report, profile_summary
from ..semantic import service as semantic_service
from ..analysis import analyst
from ..verification.engine import run_verification_gates
from ..modeling import tournament
from ..engineering import ml_engineer
from ..ingestion import registry

logger = logging.getLogger("mkpath.orchestrator")


async def node_ingest(state: MKPathState) -> Dict[str, Any]:
    logger.info("Running INGEST")
    project_id = state.get("project_id", "")
    dataset_ids = state.get("dataset_ids", [])
    dataset_id = state.get("dataset_id") or (dataset_ids[0] if dataset_ids else "")

    if not dataset_id and project_id:
        from .. import repo
        ds_list = await repo.list_datasets(limit=5)
        if ds_list:
            dataset_id = ds_list[0].get("dataset_id", "")

    await record_audit("INGEST_START", project_id=project_id, dataset_id=dataset_id, run_id=state.get("run_id"), status="running")

    if not dataset_id:
        return {"status": "FAILED", "errors": ["No dataset_id provided in state."]}

    dataset_doc = await get_dataset(dataset_id)
    if not dataset_doc:
        return {"status": "FAILED", "errors": [f"Dataset '{dataset_id}' not found in database."]}

    schema = dataset_doc.get("schema", {})
    return {
        "dataset_id": dataset_id,
        "schema": schema,
        "status": "PROFILE"
    }


async def node_profile(state: MKPathState) -> Dict[str, Any]:
    logger.info("Running PROFILE")
    project_id = state.get("project_id", "")
    dataset_id = state.get("dataset_id") or (state.get("dataset_ids", [""])[0] if state.get("dataset_ids") else "")
    await record_audit("PROFILE_START", project_id=project_id, dataset_id=dataset_id, run_id=state.get("run_id"), status="running")

    dataset_doc = await get_dataset(dataset_id)
    if not dataset_doc:
        return {"dataset_id": dataset_id, "status": "FAILED", "errors": [f"Dataset '{dataset_id}' not found."]}

    profile = dataset_doc.get("profile")
    if not profile:
        try:
            report = build_quality_report(dataset_doc)
            profile = profile_summary(report)
        except Exception as exc:
            logger.error(f"Failed profiling in orchestrator: {exc}")
            profile = {"quality_score": 0.0, "issues": [str(exc)]}

    return {"dataset_id": dataset_id, "profile": profile, "status": "SEMANTIC_ANALYSIS"}


async def node_semantic_analysis(state: MKPathState) -> Dict[str, Any]:
    logger.info("Running SEMANTIC_ANALYSIS")
    project_id = state.get("project_id", "")
    dataset_id = state.get("dataset_id") or (state.get("dataset_ids", [""])[0] if state.get("dataset_ids") else "")
    business_goal = state.get("business_goal", "")

    await record_audit("SEMANTIC_ANALYSIS", project_id=project_id, dataset_id=dataset_id, run_id=state.get("run_id"), status="running")

    dataset_doc = await get_dataset(dataset_id)
    ctx = await semantic_service.get_latest_context(dataset_id)
    if not ctx and dataset_doc:
        try:
            ctx = await semantic_service.build_and_store(dataset_doc, business_goal)
        except Exception as exc:
            logger.warning(f"Semantic context creation in graph failed: {exc}")

    ambiguities = []
    if ctx:
        ambiguities = [a for a in ctx.get("ambiguities", []) if a.get("status") == "open"]

    return {
        "dataset_id": dataset_id,
        "semantic_context": ctx or {},
        "ambiguities": ambiguities,
        "status": "AMBIGUITY_CHECK"
    }


def check_ambiguity(state: MKPathState) -> str:
    ambiguities = state.get("ambiguities", [])
    user_decisions = state.get("user_decisions", [])
    # Unresolved blocking ambiguities trigger Human Breakpoint
    unresolved = [a for a in ambiguities if a.get("severity") == "blocking" and a.get("status") == "open"]
    if unresolved and len(unresolved) > len(user_decisions):
        return "HUMAN_BREAKPOINT"
    return "ANALYSIS_PLANNING"


async def node_human_breakpoint(state: MKPathState) -> Dict[str, Any]:
    logger.info("Running HUMAN_BREAKPOINT")
    dataset_id = state.get("dataset_id") or (state.get("dataset_ids", [""])[0] if state.get("dataset_ids") else "")
    await record_audit("HUMAN_BREAKPOINT", project_id=state.get("project_id"), dataset_id=dataset_id, run_id=state.get("run_id"), status="paused")
    return {"dataset_id": dataset_id, "status": "PAUSED_FOR_INPUT"}


async def node_analysis_planning(state: MKPathState) -> Dict[str, Any]:
    logger.info("Running ANALYSIS_PLANNING")
    dataset_id = state.get("dataset_id") or (state.get("dataset_ids", [""])[0] if state.get("dataset_ids") else "")
    await record_audit("ANALYSIS_PLANNING", project_id=state.get("project_id"), dataset_id=dataset_id, run_id=state.get("run_id"), status="running")

    bg = state.get("business_goal", "")
    schema = state.get("schema", {})
    profile = state.get("profile", {})
    semantic_ctx = state.get("semantic_context", {})

    plan = analyst.generate_plan(bg, schema, profile, semantic_ctx)
    return {"dataset_id": dataset_id, "analysis_plan": plan, "status": "DATA_ANALYST"}


async def node_data_analyst(state: MKPathState) -> Dict[str, Any]:
    logger.info("Running DATA_ANALYST")
    dataset_id = state.get("dataset_id") or (state.get("dataset_ids", [""])[0] if state.get("dataset_ids") else "")
    dataset_doc = await get_dataset(dataset_id)
    table_name = dataset_doc.get("table_name", "dataset") if dataset_doc else "dataset"
    normalized_path = dataset_doc.get("normalized_path") if dataset_doc else None

    await record_audit("DATA_ANALYST_START", project_id=state.get("project_id"), dataset_id=dataset_id, run_id=state.get("run_id"), status="running")

    plan = state.get("analysis_plan", {})
    results = analyst.execute_plan(plan, {
        "dataset_id": dataset_id,
        "table_name": table_name,
        "normalized_path": normalized_path
    })

    return {"dataset_id": dataset_id, "analysis_results": results, "status": "DATA_SCIENTIST"}


async def node_data_scientist(state: MKPathState) -> Dict[str, Any]:
    logger.info("Running DATA_SCIENTIST")
    dataset_id = state.get("dataset_id") or (state.get("dataset_ids", [""])[0] if state.get("dataset_ids") else "")
    return {"dataset_id": dataset_id, "status": "VERIFICATION"}


async def node_verification(state: MKPathState) -> Dict[str, Any]:
    logger.info("Running VERIFICATION")
    project_id = state.get("project_id", "project_1")
    run_id = state.get("run_id", "run_1")
    dataset_id = state.get("dataset_id") or (state.get("dataset_ids", [""])[0] if state.get("dataset_ids") else "")

    await record_audit("VERIFICATION_START", project_id=project_id, dataset_id=dataset_id, run_id=run_id, status="running")

    profile = state.get("profile", {})
    report = run_verification_gates(project_id, run_id, {
        "data_quality_score": profile.get("quality_score", 100.0),
        "temporal_leakage_risk": "LOW"
    })

    return {
        "dataset_id": dataset_id,
        "status": "MODEL_TOURNAMENT",
        "verification_results": report.model_dump()
    }


async def node_model_tournament(state: MKPathState) -> Dict[str, Any]:
    logger.info("Running MODEL_TOURNAMENT")
    dataset_id = state.get("dataset_id") or (state.get("dataset_ids", [""])[0] if state.get("dataset_ids") else "")
    dataset_doc = await get_dataset(dataset_id)
    normalized_path = dataset_doc.get("normalized_path") if dataset_doc else None
    semantic_ctx = state.get("semantic_context", {})

    # Determine target column from user decision or semantic context or analysis plan
    target = None
    user_decisions = state.get("user_decisions", [])
    if user_decisions:
        target = user_decisions[-1].get("choice") or user_decisions[-1].get("selected_target")

    if not target and semantic_ctx and "targets" in semantic_ctx and semantic_ctx["targets"]:
        target = semantic_ctx["targets"][0].get("name")

    if not target:
        concepts = semantic_ctx.get("concepts", []) if semantic_ctx else []
        for c in concepts:
            if c.get("type") == "target":
                target = c.get("name")
                break

    if not target:
        plan = state.get("analysis_plan", {})
        if plan and "metrics" in plan and plan["metrics"]:
            target = plan["metrics"][0]

    # Load actual data from DuckDB / registered view
    try:
        registry.ensure_view(dataset_id, normalized_path)
        conn = registry.get_conn()
        v_name = registry.view_name(dataset_id)
        df = conn.execute(f'SELECT * FROM "{v_name}"').df()
    except Exception as exc:
        logger.warning(f"Could not load view for dataset {dataset_id}: {exc}")
        df = pd.DataFrame()

    if df.empty or not target:
        res = {
            "status": "HUMAN_REVIEW_REQUIRED",
            "error": "INSUFFICIENT_TARGET_INFORMATION",
            "message": f"Target column '{target}' unavailable or dataset empty."
        }
        return {"dataset_id": dataset_id, "selected_model": res, "status": "ML_ENGINEER"}

    res = tournament.run_model_tournament(df, target, is_temporal=False)
    selected = res.get("selected_model", {}) if res.get("status") == "SUCCESS" else res

    return {
        "dataset_id": dataset_id,
        "model_candidates": res.get("model_candidates", []),
        "selected_model": selected,
        "status": "ML_ENGINEER"
    }


async def node_ml_engineer(state: MKPathState) -> Dict[str, Any]:
    logger.info("Running ML_ENGINEER")
    project_id = state.get("project_id", "project_1")
    run_id = state.get("run_id", "run_1")

    verif_results = state.get("verification_results", {})
    if not verif_results:
        verif_results = {"deployment_status": "BLOCKED"}

    model_info = state.get("selected_model", {})
    model_features = model_info.get("feature_names", [])

    feature_schema = {}
    if isinstance(schema, list):
        for col in schema:
            c_name = col.get("name")
            if not model_features or c_name in model_features:
                feature_schema[c_name] = col.get("type", "float")
    elif isinstance(schema, dict):
        for k, v in schema.items():
            if not model_features or k in model_features:
                feature_schema[k] = v

    artifact_meta = ml_engineer.generate_deployment_artifacts(
        project_id, run_id, verif_results, model_info, feature_schema
    )

    return {
        "status": "ARTIFACT_GENERATION",
        "artifacts": [artifact_meta]
    }


async def node_artifact_generation(state: MKPathState) -> Dict[str, Any]:
    logger.info("Running ARTIFACT_GENERATION")
    return {"status": "AUDIT"}


async def node_audit(state: MKPathState) -> Dict[str, Any]:
    logger.info("Running AUDIT")
    await record_audit("WORKFLOW_COMPLETED", project_id=state.get("project_id"), dataset_id=state.get("dataset_id"), run_id=state.get("run_id"), status="ok")
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

    workflow.add_edge("HUMAN_BREAKPOINT", END)
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
    return build_graph().compile(checkpointer=memory, interrupt_before=["HUMAN_BREAKPOINT"])
