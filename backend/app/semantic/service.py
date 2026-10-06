"""Semantic layer service (Phase 6): persistence + workflow orchestration.

Mongo usage:
- `ontology`: versioned SemanticContext documents (kind="semantic_context").
- `clarification_questions`: one open question per open blocking ambiguity;
  the same signature is never asked twice while a question is still open.
"""
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..audit import record_audit
from ..config import settings
from ..database import db_manager
from ..repo import MetadataUnavailable
from .builder import (
    ADVISORY_PENALTY,
    BLOCKING_PENALTY,
    NO_GOAL_PENALTY,
    build_context,
)
from .llm import get_provider
from .models import UserDecision, new_id

logger = logging.getLogger("mkpath.semantic.service")


def _require(collection: str):
    coll = db_manager.get_collection(collection)
    if coll is None:
        raise MetadataUnavailable("Metadata store unavailable; semantic layer requires MongoDB.")
    return coll


def profile_report_path(dataset_id: str) -> Path:
    return settings.DATA_DIR / "profiles" / f"{dataset_id}.json"


async def get_latest_context(dataset_id: str) -> Optional[Dict[str, Any]]:
    coll = _require("ontology")
    return await coll.find_one(
        {"kind": "semantic_context", "dataset_id": dataset_id},
        {"_id": 0},
        sort=[("version", -1)],
    )


async def _get_open_question_signatures(dataset_id: str) -> Dict[str, str]:
    """signature -> existing open question_id (never ask twice while open)."""
    coll = _require("clarification_questions")
    cursor = coll.find({"dataset_id": dataset_id, "status": "open"}, {"_id": 0})
    out: Dict[str, str] = {}
    async for q in cursor:
        sig = q.get("ambiguity_signature")
        if sig:
            out[sig] = q["question_id"]
    return out


async def build_and_store(
    dataset: Dict[str, Any],
    business_goal: Optional[str],
    provider: Any = None,
) -> Dict[str, Any]:
    """Build a SemanticContext for `dataset` and persist context + questions."""
    dataset_id = dataset["dataset_id"]

    profile: Optional[Dict[str, Any]] = None
    ppath = profile_report_path(dataset_id)
    if ppath.exists():
        try:
            profile = json.loads(ppath.read_text(encoding="utf-8"))
        except Exception as exc:
            logger.warning("Profile unreadable: %s", type(exc).__name__)
            profile = None

    previous = await get_latest_context(dataset_id)
    open_sigs = await _get_open_question_signatures(dataset_id)

    import asyncio

    loop = asyncio.get_running_loop()
    context, drafts = await loop.run_in_executor(
        None,
        lambda: build_context(
            dataset=dataset,
            profile=profile,
            business_goal=business_goal,
            provider=provider or get_provider(),
            previous=previous,
            existing_open_signatures=open_sigs,
        ),
    )

    ctx_doc = context.model_dump()

    # Stamp question ids and attach them to their ambiguities.
    question_docs: List[Dict[str, Any]] = []
    amb_by_id = {a["id"]: a for a in ctx_doc["ambiguities"]}
    for draft in drafts:
        qid = new_id()
        draft["question_id"] = qid
        amb = amb_by_id.get(draft["ambiguity_id"])
        if amb is not None:
            amb["question_id"] = qid
        question_docs.append(
            {
                "question_id": qid,
                "project_id": dataset.get("project_id"),
                "dataset_id": dataset_id,
                "context_version": ctx_doc["version"],
                "ambiguity_id": draft["ambiguity_id"],
                "ambiguity_signature": draft["ambiguity_signature"],
                "kind": draft["kind"],
                "severity": draft["severity"],
                "question": draft["question"],
                "evidence": draft.get("evidence", []),
                "options": draft["options"],
                "allows_free_text": draft["allows_free_text"],
                "status": "open",
                "created_at": datetime.now(timezone.utc),
            }
        )

    # Re-apply open-signature linkage (builder already skipped duplicates).
    ontology = _require("ontology")
    doc_to_insert = {**ctx_doc, "kind": "semantic_context"}
    doc_to_insert.pop("context_id", None)  # keep context_id only as a field
    doc_to_insert["context_id"] = ctx_doc["context_id"]
    await ontology.insert_one(doc_to_insert)
    if question_docs:
        await _require("clarification_questions").insert_many(
            [dict(q) for q in question_docs]
        )

    await record_audit(
        "semantic_context_built",
        status="ok",
        dataset_id=dataset_id,
        details={
            "version": ctx_doc["version"],
            "confidence": ctx_doc["confidence"],
            "workflow_status": ctx_doc["workflow_status"],
            "ambiguities_open": sum(
                1 for a in ctx_doc["ambiguities"] if a["status"] == "open"
            ),
        },
    )
    if ctx_doc["workflow_status"] == "interrupted":
        await record_audit(
            "semantic_interrupt",
            status="blocked",
            dataset_id=dataset_id,
            details={
                "confidence": ctx_doc["confidence"],
                "threshold": settings.SEMANTIC_CONFIDENCE_THRESHOLD,
                "questions": [q["question_id"] for q in question_docs],
            },
        )
    return {
        "dataset_id": dataset_id,
        "context_id": ctx_doc["context_id"],
        "version": ctx_doc["version"],
        "confidence": ctx_doc["confidence"],
        "threshold": settings.SEMANTIC_CONFIDENCE_THRESHOLD,
        "workflow_status": ctx_doc["workflow_status"],
        "llm_available": ctx_doc["llm_available"],
        "open_ambiguities": sum(1 for a in ctx_doc["ambiguities"] if a["status"] == "open"),
        "questions": [
            {
                "question_id": q["question_id"],
                "ambiguity_id": q["ambiguity_id"],
                "kind": q["kind"],
                "severity": q["severity"],
                "question": q["question"],
                "options": q["options"],
                "allows_free_text": q["allows_free_text"],
            }
            for q in question_docs
        ],
        "warnings": ctx_doc["warnings"],
    }


def _recompute(confidence_parts: Dict[str, Any]) -> tuple:
    ambigs = confidence_parts["ambiguities"]
    open_block = sum(1 for a in ambigs if a["status"] == "open" and a["severity"] == "blocking")
    open_adv = sum(1 for a in ambigs if a["status"] == "open" and a["severity"] == "advisory")
    confidence = max(
        0.0,
        1.0
        - BLOCKING_PENALTY * open_block
        - ADVISORY_PENALTY * open_adv
        - (NO_GOAL_PENALTY if not confidence_parts.get("business_goal") else 0.0),
    )
    confidence = round(confidence, 2)
    status = (
        "interrupted" if confidence < settings.SEMANTIC_CONFIDENCE_THRESHOLD else "ready"
    )
    return confidence, status


async def resolve_question(
    question_id: str, choice: str, note: Optional[str], answered_by: Optional[str] = "system_user"
) -> Dict[str, Any]:
    """Apply a user decision to a clarification question (workflow resume)."""
    qcoll = _require("clarification_questions")
    question = await qcoll.find_one({"question_id": question_id}, {"_id": 0})
    if question is None:
        raise LookupError("Clarification question not found.")
    if question.get("status") != "open":
        raise RuntimeError("Clarification question is already resolved.")

    dataset_id = question["dataset_id"]
    ctx_doc = await get_latest_context(dataset_id)
    if ctx_doc is None:
        raise LookupError("No semantic context exists for this dataset.")

    amb = next(
        (a for a in ctx_doc.get("ambiguities", []) if a["id"] == question["ambiguity_id"]),
        None,
    )
    if amb is None:
        raise LookupError("Ambiguity not present in the latest semantic context.")
    if amb.get("status") != "open":
        raise RuntimeError("Ambiguity is already resolved.")

    option_labels = [o["label"] for o in question.get("options", [])]
    if not question.get("allows_free_text") and option_labels and choice not in option_labels:
        raise ValueError(
            f"Invalid choice {choice!r}. Allowed options: {option_labels}"
        )
    if amb["kind"] == "TARGET_SELECTION":
        # A target choice must name a real column, even when free text is allowed.
        column_names = [cd["name"] for cd in ctx_doc.get("column_definitions", [])]
        if choice not in column_names:
            raise ValueError(
                f"Choice {choice!r} is not a column of this dataset. "
                f"Columns: {column_names}"
            )

    decision = UserDecision(
        dataset_id=dataset_id,
        ambiguity_id=amb["id"],
        question_id=question_id,
        kind=amb["kind"],
        subject=amb["subject"],
        choice=choice,
        note=note,
    )

    # Apply semantics: user decisions are the ONLY way business meaning finalizes.
    if amb["kind"] == "TARGET_SELECTION":
        if not any(t.get("name") == choice for t in ctx_doc.get("targets", [])):
            # The user named a column that was not a candidate: create the
            # target concept from the decision itself.
            ctx_doc.setdefault("targets", []).append(
                {
                    "id": new_id(),
                    "type": "target",
                    "name": choice,
                    "dataset_id": dataset_id,
                    "description": f"Target confirmed by user decision: {choice}.",
                    "source": "user_decision",
                    "status": "confirmed",
                    "confidence": 0.95,
                    "finalized_by": "user_decision",
                    "subject_column": choice,
                    "evidence": [
                        {
                            "kind": "user_decision",
                            "detail": f"confirmed via {question_id}",
                            "reference": question_id,
                        }
                    ],
                    "created_at": datetime.now(timezone.utc),
                }
            )
        for t in ctx_doc.get("targets", []):
            if t["name"] == choice:
                t["status"] = "confirmed"
                t["finalized_by"] = "user_decision"
                t["confidence"] = 0.95
                t["evidence"] = t.get("evidence", []) + [
                    {"kind": "user_decision", "detail": f"confirmed via {question_id}", "reference": question_id}
                ]
            elif t["status"] != "rejected":
                t["status"] = "rejected"
        for cd in ctx_doc.get("column_definitions", []):
            if cd["name"] == choice:
                cd["business_meaning"] = "modeling target (confirmed by user decision)"
                cd["meaning_source"] = "user_decision"
                cd["status"] = "resolved"
    elif amb["kind"] == "VALUE_MAPPING":
        for cd in ctx_doc.get("column_definitions", []):
            if cd["name"] == amb["subject"]:
                cd["business_meaning"] = choice
                cd["meaning_source"] = "user_decision"
                cd["status"] = "resolved"

    amb["status"] = "resolved"
    amb["resolved_option"] = choice
    amb["resolved_by_decision"] = decision.id

    ctx_doc.setdefault("user_decisions", []).append(decision.model_dump())
    confidence, status = _recompute(ctx_doc)
    ctx_doc["confidence"] = confidence
    ctx_doc["workflow_status"] = status
    ctx_doc["version"] = int(ctx_doc.get("version", 1)) + 1
    ctx_doc["context_id"] = new_id()
    ctx_doc["created_at"] = datetime.now(timezone.utc)

    ontology = _require("ontology")
    await ontology.insert_one({**ctx_doc, "kind": "semantic_context"})

    await qcoll.update_one(
        {"question_id": question_id},
        {
            "$set": {
                "status": "resolved",
                "answer": {"choice": choice, "note": note, "decision_id": decision.id},
                "answered_by": answered_by,
                "resolved_at": datetime.now(timezone.utc),
                "context_version": ctx_doc["version"],
            }
        },
    )

    from ..repo import insert_human_decision
    await insert_human_decision({
        "question_id": question_id,
        "project_id": question.get("project_id"),
        "dataset_id": dataset_id,
        "question": question.get("question"),
        "options": question.get("options", []),
        "evidence": question.get("evidence", []),
        "answer": choice,
        "answered_by": answered_by,
        "timestamp": datetime.now(timezone.utc)
    })

    await record_audit(
        "clarification_resolved",
        status="ok",
        dataset_id=dataset_id,
        details={"question_id": question_id, "choice": choice},
    )
    await record_audit(
        "user_decision_recorded",
        status="ok",
        dataset_id=dataset_id,
        details={
            "decision_id": decision.id,
            "kind": amb["kind"],
            "subject": amb["subject"],
            "choice": choice,
        },
    )
    if status == "ready":
        await record_audit(
            "semantic_ready",
            status="ok",
            dataset_id=dataset_id,
            details={"confidence": confidence, "version": ctx_doc["version"]},
        )

    return {
        "question_id": question_id,
        "dataset_id": dataset_id,
        "decision_id": decision.id,
        "choice": choice,
        "context_version": ctx_doc["version"],
        "confidence": confidence,
        "workflow_status": status,
        "open_ambiguities": sum(1 for a in ctx_doc["ambiguities"] if a["status"] == "open"),
    }
