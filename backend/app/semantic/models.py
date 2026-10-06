"""Semantic knowledge layer models (Phase 6).

Core principle (spec section 11 / Phase 6): business semantics are never
silently finalized. Every business interpretation carries an explicit source
and status; ONLY a UserDecision can set status="confirmed" with
finalized_by="user_decision". The LLM can merely propose (needs_review).
"""
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


def new_id() -> str:
    return uuid.uuid4().hex


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ConceptType(str, Enum):
    """All 13 concept types required by the Phase 6 specification."""
    DATASET = "dataset"
    TABLE = "table"
    COLUMN = "column"
    METRIC = "metric"
    DIMENSION = "dimension"
    TARGET = "target"
    FEATURE = "feature"
    EVENT = "event"
    BUSINESS_TERM = "business_term"
    DEFINITION = "definition"
    RELATIONSHIP = "relationship"
    AMBIGUITY = "ambiguity"
    USER_DECISION = "user_decision"


class ConceptSource(str, Enum):
    DETERMINISTIC = "deterministic"      # computed from data/schema/profile
    LLM_PROPOSED = "llm_proposed"        # LLM interpretation - never final
    USER_DECISION = "user_decision"      # confirmed by an explicit human answer


class ConceptStatus(str, Enum):
    CANDIDATE = "candidate"              # plausible, not yet final
    NEEDS_REVIEW = "needs_review"        # LLM proposal awaiting human review
    CONFIRMED = "confirmed"              # finalized (deterministic evidence or user)
    REJECTED = "rejected"                # explicitly discarded by user decision


class Evidence(BaseModel):
    kind: str                      # schema | profiler_role | name_pattern | sample_values | llm | user_decision
    detail: str = ""
    reference: Optional[str] = None  # e.g. profile statistics path or question id


class Concept(BaseModel):
    id: str = Field(default_factory=new_id)
    type: ConceptType
    name: str
    dataset_id: str
    description: str = ""
    source: ConceptSource = ConceptSource.DETERMINISTIC
    status: ConceptStatus = ConceptStatus.CANDIDATE
    confidence: float = 0.5
    finalized_by: Optional[str] = None  # "deterministic_evidence" | "user_decision"
    subject_column: Optional[str] = None  # column this concept is about (if any)
    evidence: List[Evidence] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utcnow)


class Relationship(BaseModel):
    id: str = Field(default_factory=new_id)
    subject: str                 # concept name (e.g. column or term)
    predicate: str               # measures | describes | is_target_of | timestamps | glossary_for | has_column
    object: str                  # concept name (usually the dataset or table)
    confidence: float = 0.6
    evidence: List[Evidence] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utcnow)


class AmbiguityOption(BaseModel):
    label: str
    description: str = ""
    confidence: Optional[float] = None
    source: ConceptSource = ConceptSource.DETERMINISTIC


class Ambiguity(BaseModel):
    """An explicitly represented, unresolved business-semantics question."""
    id: str = Field(default_factory=new_id)
    dataset_id: str
    kind: str                    # TARGET_SELECTION | VALUE_MAPPING | LLM_PROPOSED
    subject: str                 # column name or dataset identifier
    question: str
    options: List[AmbiguityOption] = Field(default_factory=list)
    allows_free_text: bool = False   # VALUE_MAPPING mappings are free text
    severity: str = "blocking"       # blocking | advisory
    status: str = "open"             # open | resolved
    resolved_option: Optional[str] = None
    resolved_by_decision: Optional[str] = None
    question_id: Optional[str] = None
    created_at: datetime = Field(default_factory=utcnow)


class UserDecision(BaseModel):
    id: str = Field(default_factory=new_id)
    dataset_id: str
    ambiguity_id: str
    question_id: Optional[str] = None
    kind: str
    subject: str
    choice: str
    note: Optional[str] = None
    decided_at: datetime = Field(default_factory=utcnow)


class ColumnDefinition(BaseModel):
    name: str
    dtype: str
    nullable: bool = True
    missing_pct: float = 0.0
    unique_count: Optional[int] = None
    role_candidates: List[str] = Field(default_factory=list)  # profiler roles
    sample_values: List[str] = Field(default_factory=list)
    business_meaning: Optional[str] = None        # ONLY set by a UserDecision
    meaning_source: Optional[str] = None          # user_decision | None
    status: str = "unresolved"                    # unresolved | resolved
    proposals: List[Dict[str, Any]] = Field(default_factory=list)  # LLM or none


class SemanticContext(BaseModel):
    """Full semantic snapshot for one dataset build (versioned)."""
    context_id: str = Field(default_factory=new_id)
    dataset_id: str
    version: int = 1
    business_goal: Optional[str] = None
    confidence: float = 0.0
    workflow_status: str = "interrupted"          # ready | interrupted
    llm_available: bool = False
    concepts: List[Concept] = Field(default_factory=list)
    column_definitions: List[ColumnDefinition] = Field(default_factory=list)
    business_terms: List[Concept] = Field(default_factory=list)
    metrics: List[Concept] = Field(default_factory=list)
    dimensions: List[Concept] = Field(default_factory=list)
    targets: List[Concept] = Field(default_factory=list)
    features: List[Concept] = Field(default_factory=list)
    events: List[Concept] = Field(default_factory=list)
    relationships: List[Relationship] = Field(default_factory=list)
    ambiguities: List[Ambiguity] = Field(default_factory=list)
    user_decisions: List[UserDecision] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utcnow)
