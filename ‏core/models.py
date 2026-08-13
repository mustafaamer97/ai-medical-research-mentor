from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List, Literal, Optional
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator


# ──────────────────────────────────────────────
# Enumerations
# ──────────────────────────────────────────────

class StudyDesignType(str, Enum):
    CROSS_SECTIONAL = "Cross-sectional"
    COHORT = "Cohort"
    CASE_CONTROL = "Case-control"
    RCT = "Randomized controlled trial"
    DIAGNOSTIC = "Diagnostic study"
    OTHER = "Other"


class ResearchStateEnum(str, Enum):
    IDEA = "IDEA"
    QUESTION_DEFINED = "QUESTION_DEFINED"
    DESIGN_SELECTED = "DESIGN_SELECTED"
    PROTOCOL_READY = "PROTOCOL_READY"
    LITERATURE_SEARCH = "LITERATURE_SEARCH"
    SCREENING = "SCREENING"
    DATA_COLLECTION = "DATA_COLLECTION"
    DATA_READY = "DATA_READY"
    ANALYSIS_PLAN_LOCKED = "ANALYSIS_PLAN_LOCKED"
    ANALYSIS_COMPLETE = "ANALYSIS_COMPLETE"
    MANUSCRIPT_DRAFT = "MANUSCRIPT_DRAFT"
    AUDIT = "AUDIT"
    JOURNAL_SELECTION = "JOURNAL_SELECTION"
    READY_FOR_SUBMISSION = "READY_FOR_SUBMISSION"


class TaskStatus(str, Enum):
    TODO = "TODO"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    BLOCKED = "BLOCKED"


class TaskPriority(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class FrameworkCompleteness(str, Enum):
    COMPLETE = "COMPLETE"
    NEEDS_CLARIFICATION = "NEEDS_CLARIFICATION"
    INCOMPLETE = "INCOMPLETE"


class ScreeningDecisionEnum(str, Enum):
    PENDING = "PENDING"
    INCLUDE = "INCLUDE"
    EXCLUDE = "EXCLUDE"
    MAYBE = "MAYBE"


# ──────────────────────────────────────────────
# Sprint 1 Sub-models
# ──────────────────────────────────────────────

class ResearchQuestion(BaseModel):
    question_text: str = Field(..., min_length=10)
    background: Optional[str] = Field(default=None)

    model_config = {"frozen": False}


class Population(BaseModel):
    description: str = Field(..., min_length=3)
    setting: Optional[str] = Field(default=None)

    model_config = {"frozen": False}


class Exposure(BaseModel):
    description: str = Field(..., min_length=3)
    measurement_method: Optional[str] = Field(default=None)

    model_config = {"frozen": False}


class Intervention(BaseModel):
    description: str = Field(..., min_length=3)
    dosage_or_protocol: Optional[str] = Field(default=None)

    model_config = {"frozen": False}


class Comparator(BaseModel):
    description: str = Field(..., min_length=3)

    model_config = {"frozen": False}


class Outcome(BaseModel):
    name: str = Field(..., min_length=2)
    description: str = Field(..., min_length=3)
    measurement_method: Optional[str] = Field(default=None)
    time_point: Optional[str] = Field(default=None)
    is_primary: bool = Field(default=False)

    model_config = {"frozen": False}


class InclusionCriteria(BaseModel):
    criteria: List[str] = Field(default_factory=list)

    @field_validator("criteria")
    @classmethod
    def criteria_not_empty_strings(cls, v: List[str]) -> List[str]:
        return [c.strip() for c in v if c.strip()]

    model_config = {"frozen": False}


class ExclusionCriteria(BaseModel):
    criteria: List[str] = Field(default_factory=list)

    @field_validator("criteria")
    @classmethod
    def criteria_not_empty_strings(cls, v: List[str]) -> List[str]:
        return [c.strip() for c in v if c.strip()]

    model_config = {"frozen": False}


class SampleSizePlan(BaseModel):
    planned_n: Optional[int] = Field(default=None, gt=0)
    rationale: Optional[str] = Field(default=None)
    notes: Optional[str] = Field(default=None)

    model_config = {"frozen": False}


class AnalysisPlan(BaseModel):
    primary_analysis_description: Optional[str] = Field(default=None)
    secondary_analyses: List[str] = Field(default_factory=list)
    notes: Optional[str] = Field(default=None)

    model_config = {"frozen": False}


class StudyDesign(BaseModel):
    design_type: StudyDesignType
    rationale: Optional[str] = Field(default=None)

    model_config = {"frozen": False}


# ──────────────────────────────────────────────
# Sprint 2 Models
# ──────────────────────────────────────────────

class ResearchFramework(BaseModel):
    """
    Structured PICO/PECO research framework.

    PICO: Population, Intervention, Comparator, Outcome
    PECO: Population, Exposure, Comparator, Outcome

    Fields are plain strings. Does not duplicate the richer Sprint 1
    sub-models. Integrated with ResearchProject via research_framework field.
    """
    framework_type: Literal["PICO", "PECO"] = Field(
        ..., description="PICO for intervention studies, PECO for observational studies"
    )
    population: Optional[str] = Field(default=None, description="P — target population")
    intervention: Optional[str] = Field(default=None, description="I — intervention (PICO only)")
    exposure: Optional[str] = Field(default=None, description="E — exposure (PECO only)")
    comparator: Optional[str] = Field(default=None, description="C — comparator or control")
    outcome: Optional[str] = Field(default=None, description="O — primary outcome")
    time_frame: Optional[str] = Field(default=None, description="Follow-up or measurement time frame")
    rationale: Optional[str] = Field(default=None, description="Researcher rationale for framework choices")
    confidence_notes: Optional[str] = Field(default=None, description="Notes about uncertainty or missing information")

    model_config = {"frozen": False}

    def required_fields(self) -> List[str]:
        """Returns list of field names required for this framework type."""
        base = ["population", "comparator", "outcome"]
        if self.framework_type == "PICO":
            return base + ["intervention"]
        return base + ["exposure"]

    def missing_fields(self) -> List[str]:
        """Returns list of required field names that are not yet populated."""
        missing = []
        for field in self.required_fields():
            val = getattr(self, field, None)
            if not val or not str(val).strip():
                missing.append(field)
        return missing

    def is_complete(self) -> bool:
        """Returns True only when all required fields are populated."""
        return len(self.missing_fields()) == 0


class StudyDesignRecommendation(BaseModel):
    """
    Deterministic study design recommendation based on framework type.
    Always labelled as a suggestion — never authoritative.
    needs_expert_review is always True.
    """
    recommended_design: StudyDesignType
    alternative_designs: List[StudyDesignType] = Field(default_factory=list)
    rationale: str = Field(..., description="Why this design was suggested")
    limitations: List[str] = Field(default_factory=list)
    needs_expert_review: bool = Field(
        default=True,
        description="Always True — recommendation requires expert review",
    )

    model_config = {"frozen": False}


class FrameworkValidationResult(BaseModel):
    """Result of validating a ResearchFramework for completeness."""
    status: FrameworkCompleteness
    missing_fields: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    draft_question: Optional[str] = Field(
        default=None,
        description="Draft research question — only populated when status is COMPLETE",
    )
    completeness_score: int = Field(default=0, ge=0, le=100)

    model_config = {"frozen": False}


# ──────────────────────────────────────────────
# Sprint 3 Models
# ──────────────────────────────────────────────

class LiteratureSearchStrategy(BaseModel):
    """
    Deterministic literature search strategy built from a ResearchFramework.

    All terms come exclusively from researcher-provided data.
    No synonyms, MeSH terms, or medical concepts are invented.
    Boolean query is only generated when required elements are present.
    """
    id: str = Field(default_factory=lambda: str(uuid4()))
    framework_type: Literal["PICO", "PECO"]

    population_terms: List[str] = Field(
        default_factory=list,
        description="Search terms derived from population — researcher-provided only",
    )
    intervention_terms: List[str] = Field(
        default_factory=list,
        description="Search terms derived from intervention — PICO only",
    )
    exposure_terms: List[str] = Field(
        default_factory=list,
        description="Search terms derived from exposure — PECO only",
    )
    comparator_terms: List[str] = Field(
        default_factory=list,
        description="Search terms derived from comparator",
    )
    outcome_terms: List[str] = Field(
        default_factory=list,
        description="Search terms derived from outcome",
    )

    boolean_query: Optional[str] = Field(
        default=None,
        description="Structured Boolean query — only generated when required elements are present",
    )

    warnings: List[str] = Field(default_factory=list)
    missing_components: List[str] = Field(default_factory=list)
    ready_for_search: bool = Field(
        default=False,
        description="True only when population, primary IE element, and outcome are all present",
    )

    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"frozen": False}


class LiteratureRecord(BaseModel):
    """
    Structured model for a literature record retrieved from an external source.

    IMPORTANT: This model is a data structure only.
    No fake or synthetic records are ever created by this application.
    Records are populated only from actual external retrieval (future sprint).
    """
    id: str = Field(default_factory=lambda: str(uuid4()))
    title: Optional[str] = Field(default=None)
    authors: List[str] = Field(default_factory=list)
    journal: Optional[str] = Field(default=None)
    publication_date: Optional[str] = Field(
        default=None,
        description="Publication date as provided by the source",
    )
    abstract: Optional[str] = Field(default=None)
    doi: Optional[str] = Field(default=None)
    pmid: Optional[str] = Field(default=None)
    source: Optional[str] = Field(
        default=None,
        description="Source database (e.g., PubMed, Embase) — populated on retrieval only",
    )
    url: Optional[str] = Field(default=None)
    retrieved_at: Optional[datetime] = Field(default=None)

    model_config = {"frozen": False}


class ScreeningDecision(BaseModel):
    """
    Researcher-made screening decision for a single literature record.

    Screening decisions are made by the researcher, not automatically by the system.
    """
    record_id: str = Field(...)
    decision: ScreeningDecisionEnum = Field(default=ScreeningDecisionEnum.PENDING)
    reason: Optional[str] = Field(default=None)
    notes: Optional[str] = Field(default=None)
    decided_at: Optional[datetime] = Field(default=None)

    model_config = {"frozen": False}


# ──────────────────────────────────────────────
# Task Model (Sprint 1 — unchanged)
# ──────────────────────────────────────────────

class ResearchTask(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    title: str = Field(..., min_length=3)
    description: str = Field(..., min_length=3)
    status: TaskStatus = Field(default=TaskStatus.TODO)
    priority: TaskPriority = Field(default=TaskPriority.MEDIUM)
    why: str = Field(...)
    dependencies: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = Field(default=None)

    model_config = {"frozen": False}


# ──────────────────────────────────────────────
# Research Project
# ──────────────────────────────────────────────

class ResearchProject(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    title: str = Field(..., min_length=3)
    idea: str = Field(..., min_length=10)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Sprint 1 fields
    research_question: Optional[ResearchQuestion] = Field(default=None)
    study_design: Optional[StudyDesign] = Field(default=None)
    population: Optional[Population] = Field(default=None)
    exposure: Optional[Exposure] = Field(default=None)
    intervention: Optional[Intervention] = Field(default=None)
    comparator: Optional[Comparator] = Field(default=None)
    primary_outcome: Optional[Outcome] = Field(default=None)
    secondary_outcomes: List[Outcome] = Field(default_factory=list)
    inclusion_criteria: InclusionCriteria = Field(default_factory=InclusionCriteria)
    exclusion_criteria: ExclusionCriteria = Field(default_factory=ExclusionCriteria)
    sample_size_plan: Optional[SampleSizePlan] = Field(default=None)
    analysis_plan: Optional[AnalysisPlan] = Field(default=None)

    # Sprint 2 fields
    research_framework: Optional[ResearchFramework] = Field(default=None)

    # Sprint 3 fields
    literature_search_strategy: Optional[LiteratureSearchStrategy] = Field(default=None)
    literature_records: List[LiteratureRecord] = Field(default_factory=list)
    screening_decisions: List[ScreeningDecision] = Field(default_factory=list)

    state: ResearchStateEnum = Field(default=ResearchStateEnum.IDEA)
    tasks: List[ResearchTask] = Field(default_factory=list)

    model_config = {"frozen": False}

    def touch(self) -> None:
        self.updated_at = datetime.utcnow()


# ──────────────────────────────────────────────
# Research State wrapper
# ──────────────────────────────────────────────

class ResearchState(BaseModel):
    project: Optional[ResearchProject] = Field(default=None)
    schema_version: str = Field(default="1.2.0")
    saved_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"frozen": False}
