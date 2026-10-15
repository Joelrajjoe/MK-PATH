"""Service layer for Fault-Injection Benchmark for Verification Gates (FIB-VG).

Coordinates:
- Authorized benchmark execution workflows
- Isolated execution of scenario catalog
- Deterministic metric aggregation and release gate decision evaluation
- MongoDB Atlas persistence with write confirmation and readback verification
- Benchmark run comparison and audit trail management
"""
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .catalog import SCENARIO_CATALOG, list_scenarios
from .engine import BenchmarkExecutionEngine
from .metrics import calculate_benchmark_metrics
from .models import (
    BenchmarkAggregateMetrics,
    BenchmarkReleaseStatus,
    BenchmarkRunRecord,
    ExecutionStatus,
    FaultCategory,
    ReleaseGateDecision,
    ScenarioExecutionResult,
    Severity,
)
from .policy import DEFAULT_RELEASE_POLICY, POLICIES, evaluate_release_decision
from ..audit import record_audit
from ..database import db_manager

logger = logging.getLogger("mkpath.benchmark.service")


def _serialize_obj(val: Any) -> Any:
    """Helper to ensure all objects are BSON-safe for MongoDB Atlas."""
    if hasattr(val, "model_dump"):
        return _serialize_obj(val.model_dump())
    if isinstance(val, dict):
        return {k: _serialize_obj(v) for k, v in val.items()}
    if isinstance(val, (list, tuple)):
        return [_serialize_obj(v) for v in val]
    if hasattr(val, "value"):  # Enum
        return val.value
    return val


class BenchmarkService:
    """Orchestrates benchmark runs, persistence, and audit logging."""

    def __init__(self):
        self.engine = BenchmarkExecutionEngine()

    async def execute_benchmark_run(
        self,
        project_id: str,
        scenario_ids: Optional[List[str]] = None,
        category: Optional[FaultCategory] = None,
        policy_id: str = "FIB-RELEASE-POLICY-v1.0",
        dataset_fingerprint: Optional[str] = None,
        created_by: str = "automated_benchmark_system",
    ) -> BenchmarkRunRecord:
        """Execute a full or filtered benchmark evaluation run."""
        run_id = f"fib_run_{uuid.uuid4().hex[:12]}"
        started_at = datetime.now(timezone.utc).isoformat()

        # 1. Resolve eligible scenarios
        all_specs = list(SCENARIO_CATALOG.values())
        if scenario_ids:
            specs_to_run = [s for s in all_specs if s.scenario_id in scenario_ids]
        elif category:
            specs_to_run = [s for s in all_specs if s.category == category]
        else:
            specs_to_run = all_specs

        total_registered = len(SCENARIO_CATALOG)

        # 2. Execute scenarios sequentially in isolation
        scenario_results: List[ScenarioExecutionResult] = []
        for spec in specs_to_run:
            res = self.engine.execute_scenario(spec, project_id=project_id, run_id=run_id)
            scenario_results.append(res)

        completed_at = datetime.now(timezone.utc).isoformat()

        # 3. Calculate deterministic metrics
        metrics = calculate_benchmark_metrics(scenario_results, total_registered=total_registered)

        # 4. Evaluate release policy
        policy = POLICIES.get(policy_id, DEFAULT_RELEASE_POLICY)
        gate_decision = evaluate_release_decision(metrics, policy)

        # 5. Determine overall run execution status
        if metrics.error_scenarios > 0:
            overall_exec_status = ExecutionStatus.ERROR
        elif metrics.failed_scenarios > 0 or gate_decision.overall_status == BenchmarkReleaseStatus.RELEASE_BLOCKED:
            overall_exec_status = ExecutionStatus.FAIL
        else:
            overall_exec_status = ExecutionStatus.PASS

        # 6. Construct complete run record
        run_record = BenchmarkRunRecord(
            run_id=run_id,
            project_id=project_id,
            benchmark_version="1.0.0",
            scenario_catalog_version="FIB-CATALOG-v1.0",
            policy_id=policy.policy_id,
            started_at=started_at,
            completed_at=completed_at,
            execution_status=overall_exec_status,
            persistence_status="PENDING",
            environment_fingerprint={
                "engine": "MK-Path FIB-VG Execution Engine v1.0",
                "scratch_storage": "E:/MKPATH/data/_benchmark_isolated",
                "isolation_guarantee": "Strict in-memory/temp copy isolation; zero production mutation",
            },
            dataset_fingerprint=dataset_fingerprint,
            created_by=created_by,
            scenario_results=scenario_results,
            aggregate_metrics=metrics,
            gate_decision=gate_decision,
            audit_integrity_status="VALID",
        )

        # 7. Persist to MongoDB Atlas with confirmation
        persistence_ok = await self._persist_run_record(run_record)
        run_record.persistence_status = "CONFIRMED" if persistence_ok else "UNCONFIRMED"

        # 8. Record audit event
        await record_audit(
            "FIB_BENCHMARK_EXECUTED",
            project_id=project_id,
            run_id=run_id,
            status="ok" if overall_exec_status == ExecutionStatus.PASS else "blocked",
            details={
                "run_id": run_id,
                "total_executed": len(scenario_results),
                "passed": metrics.passed_scenarios,
                "failed": metrics.failed_scenarios,
                "critical_escapes": metrics.critical_faults_passed,
                "detection_rate_pct": metrics.detection_rate_pct,
                "false_block_rate_pct": metrics.false_block_rate_pct,
                "release_status": gate_decision.overall_status.value,
                "persistence_status": run_record.persistence_status,
            },
        )

        return run_record

    async def _persist_run_record(self, record: BenchmarkRunRecord) -> bool:
        """Persist benchmark run and scenario results to MongoDB Atlas."""
        db = db_manager.get_database()
        if db is None:
            logger.warning("MongoDB Atlas unavailable; run %s persistence unconfirmed.", record.run_id)
            return False

        try:
            runs_coll = db["fib_vg_runs"]
            scenarios_coll = db["fib_vg_scenario_results"]

            raw_doc = _serialize_obj(record)
            # Store summary run envelope
            await runs_coll.replace_one({"run_id": record.run_id}, raw_doc, upsert=True)

            # Store scenario level documents for granular queryability
            scenario_docs = [_serialize_obj(r) for r in record.scenario_results]
            for s_doc in scenario_docs:
                s_doc["run_id"] = record.run_id
                s_doc["project_id"] = record.project_id
                await scenarios_coll.replace_one(
                    {"run_id": record.run_id, "scenario_id": s_doc["scenario_id"]},
                    s_doc,
                    upsert=True,
                )

            # Readback verification
            persisted = await runs_coll.find_one({"run_id": record.run_id})
            if not persisted:
                logger.error("Readback verification failed for run %s", record.run_id)
                return False

            return True
        except Exception as exc:
            logger.error("Failed to persist benchmark run %s: %s", record.run_id, exc)
            return False

    async def get_benchmark_run(self, run_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a persisted benchmark run from MongoDB Atlas."""
        db = db_manager.get_database()
        if db is None:
            return None
        coll = db["fib_vg_runs"]
        return await coll.find_one({"run_id": run_id}, {"_id": 0})

    async def list_benchmark_runs(
        self,
        project_id: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """List historical benchmark runs for a project."""
        db = db_manager.get_database()
        if db is None:
            return []
        coll = db["fib_vg_runs"]
        query = {"project_id": project_id} if project_id else {}
        cursor = coll.find(query, {"_id": 0}).sort("started_at", -1).skip(offset).limit(limit)
        return [doc async for doc in cursor]

    async def get_scenario_results(
        self,
        run_id: str,
        category: Optional[FaultCategory] = None,
    ) -> List[Dict[str, Any]]:
        """Retrieve granular scenario results for a benchmark run."""
        db = db_manager.get_database()
        if db is None:
            return []
        coll = db["fib_vg_scenario_results"]
        query: Dict[str, Any] = {"run_id": run_id}
        if category:
            query["category"] = category.value
        cursor = coll.find(query, {"_id": 0}).sort("scenario_id", 1)
        return [doc async for doc in cursor]

    async def compare_runs(self, run_id_a: str, run_id_b: str) -> Dict[str, Any]:
        """Compare two benchmark runs to evaluate regression or improvement."""
        run_a = await self.get_benchmark_run(run_id_a)
        run_b = await self.get_benchmark_run(run_id_b)
        if not run_a or not run_b:
            raise KeyError("One or both benchmark runs not found.")

        m_a = run_a.get("aggregate_metrics", {})
        m_b = run_b.get("aggregate_metrics", {})

        return {
            "run_id_a": run_id_a,
            "run_id_b": run_id_b,
            "comparison": {
                "detection_rate_pct": {
                    "run_a": m_a.get("detection_rate_pct"),
                    "run_b": m_b.get("detection_rate_pct"),
                    "delta": round((m_b.get("detection_rate_pct") or 0) - (m_a.get("detection_rate_pct") or 0), 2),
                },
                "critical_escapes": {
                    "run_a": m_a.get("critical_faults_passed"),
                    "run_b": m_b.get("critical_faults_passed"),
                    "delta": (m_b.get("critical_faults_passed") or 0) - (m_a.get("critical_faults_passed") or 0),
                },
                "false_block_rate_pct": {
                    "run_a": m_a.get("false_block_rate_pct"),
                    "run_b": m_b.get("false_block_rate_pct"),
                    "delta": round((m_b.get("false_block_rate_pct") or 0) - (m_a.get("false_block_rate_pct") or 0), 2),
                },
                "release_status": {
                    "run_a": run_a.get("gate_decision", {}).get("overall_status"),
                    "run_b": run_b.get("gate_decision", {}).get("overall_status"),
                },
            },
        }


benchmark_service = BenchmarkService()
