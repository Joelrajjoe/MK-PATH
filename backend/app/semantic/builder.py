"""Deterministic semantic context builder (Phase 6).

Everything in this module is deterministic (spec section 7): structural roles
come from the Phase 5 profile / schema, ambiguities from explicit rules, and
the confidence from a documented formula. The LLM (if configured) may only ADD
proposals, which are stored as source="llm_proposed" / status="needs_review"
and can never finalize business semantics.

Confidence formula (documented, reproducible):
    confidence = max(0, 1
                     - 0.35 * open_blocking_ambiguities
                     - 0.15 * open_advisory_ambiguities
                     - 0.15 * (1 if business_goal missing else 0))
    workflow_status = "interrupted" if confidence < SEMANTIC_CONFIDENCE_THRESHOLD
                      else "ready"

With the default threshold (0.7), a single open blocking ambiguity (0.65) always
interrupts the workflow and creates a clarification question.
"""
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

import duckdb

from ..config import settings
from .llm import NullProvider
from .models import (
    Ambiguity,
    AmbiguityOption,
    ColumnDefinition,
    Concept,
    ConceptSource,
    ConceptStatus,
    ConceptType,
    Evidence,
    Relationship,
    SemanticContext,
    UserDecision,
)

logger = logging.getLogger("mkpath.semantic")

# Documented penalties (see module docstring)
BLOCKING_PENALTY = 0.35
ADVISORY_PENALTY = 0.15
NO_GOAL_PENALTY = 0.15

# Coded business columns (spec example: "status" with multiple meanings)
CODED_COLUMN_RE = re.compile(
    r"(^|_)(status|state|stage|type|code|flag|category|priority|level|class)(_|$)",
    re.IGNORECASE,
)
TARGET_NAME_RE = re.compile(
    r"(^|_)(target|label|class|churn|outcome|response|result|y)(_|$)",
    re.IGNORECASE,
)
# Tiny deterministic business glossary (extendable via user decisions later)
BUSINESS_GLOSSARY: Dict[str, str] = {
    "revenue": "Total monetary value recognized from sales activity.",
    "sales": "Completed sales transactions or their monetary value.",
    "amount": "A monetary or numeric quantity associated with a record.",
    "price": "The unit monetary value of an item or service.",
    "cost": "The monetary expense incurred for an item or activity.",
    "quantity": "Count of units involved in a transaction.",
    "customer": "A person or organization purchasing or using a service.",
    "order": "A commercial request for goods or services.",
    "product": "A good or service offered by the business.",
    "region": "A geographic grouping used for segmentation.",
    "date": "A calendar reference used to place records in time.",
    "status": "The lifecycle or processing state of a record.",
}

MAX_VALUE_MAPPING_QUESTIONS = 3


def _tok(name: str) -> List[str]:
    return [t for t in re.split(r"[_\-\s]+", name.lower()) if t]


def _sample_values(normalized_path: str, column: str, limit: int = 15) -> List[str]:
    """Deterministic value sample via DuckDB (never the LLM)."""
    if not normalized_path:
        return []
    try:
        conn = duckdb.connect(database=":memory:")
        col = '"' + column.replace('"', '""') + '"'
        path = normalized_path.replace("'", "''")
        rows = conn.execute(
            f"SELECT DISTINCT CAST({col} AS VARCHAR) FROM read_parquet('{path}') "
            f"WHERE {col} IS NOT NULL LIMIT {int(limit)}"
        ).fetchall()
        conn.close()
        return [r[0] for r in rows]
    except Exception as exc:
        logger.warning("Value sampling failed: %s", type(exc).__name__)
        return []


def _role_lists(profile: Optional[Dict[str, Any]]) -> Dict[str, List[str]]:
    """Roles from the Phase 5 profile when available (empty otherwise)."""
    if not profile:
        return {}
    roles = profile.get("roles") or {}
    return {
        "potential_targets": list(roles.get("potential_targets", [])),
        "potential_ids": list(roles.get("potential_ids", [])),
        "numeric": list(roles.get("numeric_columns", [])),
        "categorical": list(roles.get("categorical_columns", [])),
        "text": list(roles.get("text_columns", [])),
        "boolean": list(roles.get("boolean_columns", [])),
        "datetime": list(roles.get("datetime_columns", [])),
        "date_detected": list(roles.get("date_time_detected", [])),
    }


def build_context(
    *,
    dataset: Dict[str, Any],
    profile: Optional[Dict[str, Any]],
    business_goal: Optional[str],
    provider: Any = None,
    previous: Optional[Dict[str, Any]] = None,
    existing_open_signatures: Optional[Dict[str, str]] = None,
) -> Tuple[SemanticContext, List[Dict[str, Any]]]:
    """Build (or rebuild) a SemanticContext. Pure + synchronous.

    Returns (context, question_drafts) where question_drafts are dicts ready to
    be persisted into clarification_questions by the service layer.
    `previous` (latest stored context for this dataset, if any) is used to carry
    over resolved ambiguities and user decisions across versions.
    `existing_open_signatures` maps ambiguity signatures to still-open question
    ids, so an open question is linked instead of being asked twice.
    """
    existing_open_signatures = existing_open_signatures or {}
    provider = provider or NullProvider()
    dataset_id = dataset["dataset_id"]
    schema: List[Dict[str, Any]] = dataset.get("schema", [])
    warnings: List[str] = []

    if profile is None:
        warnings.append(
            "No quality profile found; semantics derived from schema types only. "
            "Run POST /api/datasets/{id}/profile for richer roles."
        )

    roles = _role_lists(profile)
    name_to_schema = {c["name"]: c for c in schema}

    # --- carry-over from previous version ---
    previous_decisions: List[UserDecision] = []
    resolved_ambiguities: Dict[str, Ambiguity] = {}
    resolved_meanings: Dict[str, str] = {}
    confirmed_targets: List[str] = []
    if previous:
        for dec in previous.get("user_decisions", []):
            previous_decisions.append(UserDecision(**dec))
        for amb in previous.get("ambiguities", []):
            if amb.get("status") == "resolved":
                resolved_ambiguities[f"{amb['kind']}:{amb['subject']}"] = Ambiguity(**amb)
        for cd in previous.get("column_definitions", []):
            if cd.get("business_meaning"):
                resolved_meanings[cd["name"]] = cd["business_meaning"]
        for t in previous.get("targets", []):
            if t.get("status") == "confirmed" and t.get("name"):
                confirmed_targets.append(t["name"])

    # --- column definitions + concepts ---
    concepts: List[Concept] = []
    relationships: List[Relationship] = []
    business_terms: List[Concept] = []
    metrics: List[Concept] = []
    dimensions: List[Concept] = []
    targets: List[Concept] = []
    features: List[Concept] = []
    events: List[Concept] = []
    column_definitions: List[ColumnDefinition] = []

    def _ev(kind: str, detail: str, ref: Optional[str] = None) -> Evidence:
        return Evidence(kind=kind, detail=detail, reference=ref)

    ds_concept = Concept(
        type=ConceptType.DATASET,
        name=dataset.get("original_filename") or dataset_id,
        dataset_id=dataset_id,
        description=f"Dataset {dataset_id} ({dataset.get('source_format')}).",
        confidence=1.0,
        status=ConceptStatus.CONFIRMED,
        finalized_by="deterministic_evidence",
        evidence=[_ev("schema", "uploaded and ingested", dataset.get("upload_id"))],
    )
    concepts.append(ds_concept)
    table_concept = Concept(
        type=ConceptType.TABLE,
        name=dataset.get("table_name") or "table",
        dataset_id=dataset_id,
        description=f"Table {dataset.get('table_name')} registered in DuckDB.",
        confidence=1.0,
        status=ConceptStatus.CONFIRMED,
        finalized_by="deterministic_evidence",
        evidence=[_ev("schema", "duckdb registration")],
    )
    concepts.append(table_concept)
    relationships.append(
        Relationship(
            subject=table_concept.name,
            predicate="has_column",
            object=ds_concept.name,
            confidence=1.0,
            evidence=[_ev("schema", "schema")],
        )
    )

    for col in schema:
        name = col["name"]
        dtype = col.get("type", "unknown")
        prof_col = None
        for entry in (profile or {}).get("schema", []):
            if entry.get("name") == name:
                prof_col = entry
                break

        role_candidates: List[str] = []
        if name in roles.get("numeric", []):
            role_candidates += ["metric", "feature"]
        if name in roles.get("categorical", []):
            role_candidates += ["dimension"]
        if name in roles.get("text", []):
            role_candidates += ["dimension"]
        if name in roles.get("boolean", []):
            role_candidates += ["feature", "dimension"]
        if name in roles.get("datetime", []):
            role_candidates += ["event_time"]
        if name in roles.get("potential_ids", []):
            role_candidates += ["identifier"]
        if name in roles.get("potential_targets", []):
            role_candidates += ["target"]
        elif TARGET_NAME_RE.search(name):
            # Name-based target detection works even without a profile.
            role_candidates += ["target"]
        if not role_candidates and profile is None:
            # fallback: type-based only
            low = dtype.lower()
            if "int" in low or "float" in low or "double" in low:
                role_candidates += ["metric", "feature"]
            elif "timestamp" in low or "date" in low:
                role_candidates += ["event_time"]
            else:
                role_candidates += ["dimension"]

        col_concept = Concept(
            type=ConceptType.COLUMN,
            name=name,
            dataset_id=dataset_id,
            description=f"Column {name} ({dtype}).",
            confidence=0.9,
            status=ConceptStatus.CONFIRMED,
            finalized_by="deterministic_evidence",
            subject_column=name,
            evidence=[_ev("schema", f"type={dtype}")],
        )
        concepts.append(col_concept)
        relationships.append(
            Relationship(
                subject=table_concept.name,
                predicate="has_column",
                object=name,
                confidence=1.0,
                evidence=[_ev("schema", "schema")],
            )
        )

        col_def = ColumnDefinition(
            name=name,
            dtype=dtype,
            nullable=bool(col.get("nullable", True)),
            missing_pct=float(prof_col.get("missing_pct", 0.0)) if prof_col else 0.0,
            unique_count=prof_col.get("unique_count") if prof_col else None,
            role_candidates=role_candidates,
        )

        # business term glossary (deterministic)
        for tok in _tok(name):
            if tok in BUSINESS_GLOSSARY:
                term = Concept(
                    type=ConceptType.BUSINESS_TERM,
                    name=tok,
                    dataset_id=dataset_id,
                    description=BUSINESS_GLOSSARY[tok],
                    confidence=0.6,
                    status=ConceptStatus.CANDIDATE,
                    subject_column=name,
                    evidence=[_ev("name_pattern", f"column name token {tok!r}")],
                )
                business_terms.append(term)
                concepts.append(term)
                relationships.append(
                    Relationship(
                        subject=tok,
                        predicate="glossary_for",
                        object=name,
                        confidence=0.6,
                        evidence=[_ev("name_pattern", "glossary match")],
                    )
                )
                concepts.append(
                    Concept(
                        type=ConceptType.DEFINITION,
                        name=f"definition:{tok}",
                        dataset_id=dataset_id,
                        description=BUSINESS_GLOSSARY[tok],
                        confidence=0.6,
                        status=ConceptStatus.CANDIDATE,
                        subject_column=name,
                        evidence=[_ev("name_pattern", "glossary definition")],
                    )
                )
                break

        if "metric" in role_candidates:
            metrics.append(
                Concept(
                    type=ConceptType.METRIC,
                    name=name,
                    dataset_id=dataset_id,
                    description=f"Numeric measure candidate in column {name}.",
                    confidence=0.6,
                    status=ConceptStatus.CANDIDATE,
                    subject_column=name,
                    evidence=[_ev("profiler_role", "numeric column")],
                )
            )
        if "dimension" in role_candidates:
            dimensions.append(
                Concept(
                    type=ConceptType.DIMENSION,
                    name=name,
                    dataset_id=dataset_id,
                    description=f"Grouping/segmentation candidate in column {name}.",
                    confidence=0.65,
                    status=ConceptStatus.CANDIDATE,
                    subject_column=name,
                    evidence=[_ev("profiler_role", "low-cardinality categorical")],
                )
            )
        if "feature" in role_candidates:
            features.append(
                Concept(
                    type=ConceptType.FEATURE,
                    name=name,
                    dataset_id=dataset_id,
                    description=f"Usable model input candidate in column {name}.",
                    confidence=0.6,
                    status=ConceptStatus.CANDIDATE,
                    subject_column=name,
                    evidence=[_ev("profiler_role", "feature role")],
                )
            )
        if "event_time" in role_candidates:
            ev = Concept(
                type=ConceptType.EVENT,
                name=name,
                dataset_id=dataset_id,
                description=f"Event-time column {name} (detected date/time).",
                confidence=0.7,
                status=ConceptStatus.CONFIRMED,
                finalized_by="deterministic_evidence",
                subject_column=name,
                evidence=[_ev("profiler_role", "date/time detection")],
            )
            events.append(ev)
            concepts.append(ev)
            relationships.append(
                Relationship(
                    subject=name,
                    predicate="timestamps",
                    object=ds_concept.name,
                    confidence=0.7,
                    evidence=[_ev("profiler_role", "date/time detection")],
                )
            )
        if "target" in role_candidates:
            name_matched = bool(TARGET_NAME_RE.search(name))
            targets.append(
                Concept(
                    type=ConceptType.TARGET,
                    name=name,
                    dataset_id=dataset_id,
                    description=(
                        f"Target candidate in column {name}"
                        + (" (name matches target semantics)." if name_matched else ".")
                    ),
                    confidence=0.75 if name_matched else 0.6,
                    status=(
                        ConceptStatus.CONFIRMED if name_matched else ConceptStatus.CANDIDATE
                    ),
                    finalized_by="deterministic_evidence" if name_matched else None,
                    subject_column=name,
                    evidence=[_ev("profiler_role", "potential target")],
                )
            )

        # carry over a user-confirmed business meaning
        if name in resolved_meanings:
            col_def.business_meaning = resolved_meanings[name]
            col_def.meaning_source = "user_decision"
            col_def.status = "resolved"
        column_definitions.append(col_def)

    # If MULTIPLE name-matched target candidates exist, none may stay
    # "confirmed": choosing among them is business semantics and requires a
    # user decision (TARGET_SELECTION ambiguity is raised below).
    name_matched_targets = [
        t
        for t in targets
        if t.status == ConceptStatus.CONFIRMED and t.finalized_by == "deterministic_evidence"
    ]
    if len(name_matched_targets) > 1:
        for t in name_matched_targets:
            t.status = ConceptStatus.CANDIDATE
            t.finalized_by = None
            t.confidence = 0.6

    # user-confirmed targets from previous versions stay confirmed
    for tname in confirmed_targets:
        if not any(t.name == tname for t in targets):
            targets.append(
                Concept(
                    type=ConceptType.TARGET,
                    name=tname,
                    dataset_id=dataset_id,
                    description=f"Target confirmed by user decision: {tname}.",
                    confidence=0.95,
                    status=ConceptStatus.CONFIRMED,
                    finalized_by="user_decision",
                    subject_column=tname,
                    evidence=[_ev("user_decision", "carried over")],
                )
            )

    for c in metrics + dimensions + features:
        concepts.append(c)
    for t in targets:
        if t not in concepts:
            concepts.append(t)
            relationships.append(
                Relationship(
                    subject=t.name,
                    predicate="is_target_of",
                    object=ds_concept.name,
                    confidence=t.confidence,
                    evidence=t.evidence,
                )
            )

    # --- ambiguity detection (deterministic rules) ---
    ambiguities: List[Ambiguity] = []
    question_drafts: List[Dict[str, Any]] = []

    def _add_question(amb: Ambiguity) -> None:
        sig = f"{amb.kind}:{amb.subject}"
        if sig in existing_open_signatures:
            # A question for this exact ambiguity is already open - link it,
            # never ask the same question twice.
            amb.question_id = existing_open_signatures[sig]
            return
        question_drafts.append(
            {
                "question_id": None,  # stamped by the service layer
                "dataset_id": dataset_id,
                "context_version": None,
                "ambiguity_id": amb.id,
                "ambiguity_signature": sig,
                "kind": amb.kind,
                "severity": amb.severity,
                "question": amb.question,
                "options": [o.model_dump() for o in amb.options],
                "allows_free_text": amb.allows_free_text,
                "status": "open",
            }
        )

    # 1) TARGET_SELECTION
    target_names = [t.name for t in targets if t.status != ConceptStatus.REJECTED]
    sig_t = "TARGET_SELECTION:dataset"
    if sig_t not in resolved_ambiguities and (
        len(target_names) == 0 or len(target_names) >= 2
    ):
        if len(target_names) == 0:
            question = (
                "No target column could be identified for this dataset. Which "
                "column (if any) is the modeling target?"
            )
            option_pool = [c.name for c in column_definitions if "metric" in c.role_candidates]
            options = [
                AmbiguityOption(
                    label=n, description="numeric column proposed by profiling", confidence=0.5
                )
                for n in option_pool[:8]
            ]
        else:
            question = (
                f"Multiple target candidates were detected: {target_names}. "
                "Which column is the actual modeling target?"
            )
            options = [
                AmbiguityOption(
                    label=n,
                    description=next(
                        (t.description for t in targets if t.name == n), ""
                    ),
                    confidence=next(
                        (t.confidence for t in targets if t.name == n), 0.6
                    ),
                    source=ConceptSource.DETERMINISTIC,
                )
                for n in target_names
            ]
        amb = Ambiguity(
            dataset_id=dataset_id,
            kind="TARGET_SELECTION",
            subject="dataset",
            question=question,
            options=options,
            allows_free_text=True,
            severity="blocking",
        )
        ambiguities.append(amb)
        _add_question(amb)
    elif sig_t in resolved_ambiguities:
        amb = resolved_ambiguities[sig_t].model_copy(deep=True)
        ambiguities.append(amb)

    # 2) VALUE_MAPPING for coded columns (spec example: status = 4 meanings)
    coded_questions = 0
    for col_def in column_definitions:
        if col_def.status == "resolved":
            continue  # user already provided the mapping
        name = col_def.name
        if not CODED_COLUMN_RE.search(name):
            continue
        values = _sample_values(dataset.get("normalized_path", ""), name, limit=13)
        distinct = (
            col_def.unique_count if col_def.unique_count is not None else len(values)
        )
        if not (2 <= distinct <= 12):
            continue
        col_def.sample_values = values[:15]
        sig = f"VALUE_MAPPING:{name}"
        if sig in resolved_ambiguities:
            ambiguities.append(resolved_ambiguities[sig].model_copy(deep=True))
            continue
        if coded_questions >= MAX_VALUE_MAPPING_QUESTIONS:
            warnings.append(
                f"Column '{name}' looks like a coded business column but the "
                f"question cap ({MAX_VALUE_MAPPING_QUESTIONS}) was reached; it was "
                "left unresolved on purpose."
            )
            continue
        coded_questions += 1
        amb = Ambiguity(
            dataset_id=dataset_id,
            kind="VALUE_MAPPING",
            subject=name,
            question=(
                f"Column '{name}' carries coded business meaning that must not be "
                f"guessed. Provide the meaning of its values (observed: {values})."
            ),
            options=[],  # populated below with LLM proposals (needs_review)
            allows_free_text=True,
            severity="blocking",
        )
        ambiguities.append(amb)
        _add_question(amb)

    # --- LLM proposals (never final; best effort) ---
    llm_available = provider.name != "null"
    if llm_available:
        interpreted = 0
        for amb in ambiguities:
            if amb.kind != "VALUE_MAPPING" or amb.status != "open" or amb.options:
                continue
            if interpreted >= settings.SEMANTIC_MAX_LLM_COLUMNS:
                break
            interpreted += 1
            proposals = provider.propose_column_interpretations(
                column=amb.subject,
                dtype=next(
                    (c.dtype for c in column_definitions if c.name == amb.subject), "unknown"
                ),
                values=next(
                    (c.sample_values for c in column_definitions if c.name == amb.subject), []
                ),
                business_goal=business_goal,
            )
            if proposals:
                for p in proposals:
                    amb.options.append(
                        AmbiguityOption(
                            label=p["label"],
                            description=p.get("description", ""),
                            confidence=p.get("confidence"),
                            source=ConceptSource.LLM_PROPOSED,
                        )
                    )
                for cd in column_definitions:
                    if cd.name == amb.subject:
                        cd.proposals = proposals
                # record as a needs_review concept so the proposal trail exists
                concepts.append(
                    Concept(
                        type=ConceptType.COLUMN,
                        name=f"interpretation:{amb.subject}",
                        dataset_id=dataset_id,
                        description="LLM-proposed interpretations (need human review).",
                        source=ConceptSource.LLM_PROPOSED,
                        status=ConceptStatus.NEEDS_REVIEW,
                        confidence=0.4,
                        subject_column=amb.subject,
                        evidence=[_ev("llm", "proposals attached to ambiguity")],
                    )
                )
            else:
                warnings.append(
                    f"LLM was unavailable or returned nothing for column "
                    f"'{amb.subject}'; the mapping must be provided manually."
                )
        extra = provider.propose_ambiguities(
            context_summary={
                "columns": [c.name for c in column_definitions],
                "business_goal": business_goal,
                "roles": {k: v for k, v in roles.items()},
            }
        )
        for a in extra:
            ambiguities.append(
                Ambiguity(
                    dataset_id=dataset_id,
                    kind="LLM_PROPOSED",
                    subject=a.get("subject", "dataset"),
                    question=a.get("question", ""),
                    severity="advisory",
                )
            )
    else:
        warnings.append(
            "LLM is not configured (GEMINI_API_KEY missing): running "
            "deterministic-only. Business interpretations must come from user "
            "decisions; none were invented."
        )
        for amb in ambiguities:
            if amb.kind == "VALUE_MAPPING" and amb.status == "open" and not amb.options:
                amb.options.append(
                    AmbiguityOption(
                        label="Provide mapping manually",
                        description="Free-text value mapping, e.g. 4=cancelled;1=active",
                        source=ConceptSource.DETERMINISTIC,
                    )
                )

    # --- confidence + workflow status ---
    open_block = sum(
        1 for a in ambiguities if a.status == "open" and a.severity == "blocking"
    )
    open_adv = sum(
        1 for a in ambiguities if a.status == "open" and a.severity == "advisory"
    )
    confidence = max(
        0.0,
        1.0
        - BLOCKING_PENALTY * open_block
        - ADVISORY_PENALTY * open_adv
        - (NO_GOAL_PENALTY if not business_goal else 0.0),
    )
    confidence = round(confidence, 2)
    threshold = settings.SEMANTIC_CONFIDENCE_THRESHOLD
    workflow_status = "interrupted" if confidence < threshold else "ready"

    # stamp question drafts with their ambiguity linkage + version
    version = int((previous or {}).get("version", 0)) + 1
    for q in question_drafts:
        q["context_version"] = version

    context = SemanticContext(
        dataset_id=dataset_id,
        version=version,
        business_goal=business_goal,
        confidence=confidence,
        workflow_status=workflow_status,
        llm_available=llm_available,
        concepts=concepts,
        column_definitions=column_definitions,
        business_terms=business_terms,
        metrics=metrics,
        dimensions=dimensions,
        targets=targets,
        features=features,
        events=events,
        relationships=relationships,
        ambiguities=ambiguities,
        user_decisions=previous_decisions,
        warnings=warnings,
    )
    return context, question_drafts
