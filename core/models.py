"""
Canonical domain models for AI Research Co-Pilot.

ResearchProject is the single source of truth for a research project.

All other models either:
  - belong to ResearchProject
  - derive from ResearchProject
  - represent an external record associated with ResearchProject
  - represent an auditable action performed on ResearchProject

NO-INVENTION PRINCIPLE:
  If information is missing, it is represented as None or absent.
  The system never silently fills in population details, interventions,
  outcomes, criteria, sample sizes, or any scientific content.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from research_copilot.core.enums import (
    ProjectState,
    StudyDesignType,
    TaskPriority,
    TaskStatus,
)


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------

def _now_utc() -> datetime:
    """Return current UTC time. Centralised so tests can monkeypatch if needed."""
    return datetime.now(timezone.utc)


def _new_uuid() -> str:
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# Research Question
# ---------------------------------------------------------------------------

class ResearchQuestion(BaseModel):
    """
    The canonical representation of the research question.

    There is no other question field on ResearchProject.
    """
    question_text: str = Field(
        ...,
        description="The full text of the research question.",
    )
    background: Optional[str] = Field(
        default=None,
        description="Optional background context for the question.",
    )

    @field_validator("question_text")
    @classmethod
    def question_text_must_be_meaningful(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("question_text must not be empty.")
        if len(stripped) < 10:
            raise ValueError(
                f"question_text is too short ({len(stripped)} chars). "
                "A research question must be at least 10 characters."
            )
        return stripped


# ---------------------------------------------------------------------------
# Study Design
# ---------------------------------------------------------------------------

class StudyDesign(BaseModel):
    """
    The canonical study design selection.

    Uses StudyDesignType exclusively — no competing enum elsewhere.
    """
    design_type: StudyDesignType = Field(
        ...,
        description="The selected study design.",
    )
    rationale: Optional[str] = Field(
        default=None,
        description="Optional rationale for choosing this design.",
    )


# ---------------------------------------------------------------------------
# Population
# ---------------------------------------------------------------------------

class Population(BaseModel):
    """
    Description of the target population.

    The system does NOT invent population details.
    """
    description: str = Field(
        ...,
        description="Description of the study population.",
    )
    setting: Optional[str] = Field(
        default=None,
        description="Optional setting (e.g. primary care, hospital, community).",
    )

    @field_validator("description")
    @classmethod
    def description_must_not_be_empty(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("Population description must not be empty.")
        return stripped


# ---------------------------------------------------------------------------
# Exposure
# ---------------------------------------------------------------------------

class Exposure(BaseModel):
    """
    The exposure of interest in observational designs.

    The system does NOT invent exposure details.
    """
    description: str = Field(
        ...,
        description="Description of the exposure.",
    )
    measurement_method: Optional[str] = Field(
        default=None,
        description="Optional method used to measure or define the exposure.",
    )

    @field_validator("description")
    @classmethod
    def description_must_not_be_empty(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("Exposure description must not be empty.")
        return stripped


# ---------------------------------------------------------------------------
# Intervention
# ---------------------------------------------------------------------------

class Intervention(BaseModel):
    """
    The intervention in experimental/interventional designs.

    The system does NOT invent intervention details.
    """
    description: str = Field(
        ...,
        description="Description of the intervention.",
    )
    dosage_or_protocol: Optional[str] = Field(
        default=None,
        description="Optional dosage or protocol specification.",
    )

    @field_validator("description")
    @classmethod
    def description_must_not_be_empty(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("Intervention description must not be empty.")
        return stripped


# ---------------------------------------------------------------------------
# Comparator
# ---------------------------------------------------------------------------

class Comparator(BaseModel):
    """
    The comparator (control) in comparative study designs.

    The system does NOT invent comparator details.
    """
    description: str = Field(
        ...,
        description="Description of the comparator.",
    )

    @field_validator("description")
    @classmethod
    def description_must_not_be_empty(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("Comparator description must not be empty.")
        return stripped


# ---------------------------------------------------------------------------
# Outcome
# ---------------------------------------------------------------------------

class Outcome(BaseModel):
    """
    A single measurable outcome.

    is_primary explicitly distinguishes the primary outcome
    from secondary outcomes. The system does NOT invent outcomes.
    """
    name: str = Field(
        ...,
        description="Short name for the outcome.",
    )
    description: str = Field(
        ...,
        description="Full description of the outcome.",
    )
    measurement_method: Optional[str] = Field(
        default=None,
        description="Optional method used to measure this outcome.",
    )
    time_point: Optional[str] = Field(
        default=None,
        description="Optional time point at which the outcome is measured.",
    )
    is_primary: bool = Field(
        default=False,
        description="True if this is the primary outcome; False for secondary.",
    )

    @field_validator("name")
    @classmethod
    def name_must_not_be_empty(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("Outcome name must not be empty.")
        return stripped

    @field_validator("description")
    @classmethod
    def description_must_not_be_empty(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("Outcome description must not be empty.")
        return stripped


# ---------------------------------------------------------------------------
# Inclusion / Exclusion Criteria
# ---------------------------------------------------------------------------

class InclusionCriteria(BaseModel):
    """
    Researcher-defined inclusion criteria.

    Empty strings and whitespace-only entries are silently removed.
    The system does NOT invent criteria.
    """
    criteria: List[str] = Field(
        default_factory=list,
        description="List of inclusion criteria.",
    )

    @field_validator("criteria", mode="before")
    @classmethod
    def clean_criteria(cls, v: List[str]) -> List[str]:
        if not isinstance(v, list):
            raise ValueError("criteria must be a list of strings.")
        cleaned = [item.strip() for item in v if isinstance(item, str)]
        return [item for item in cleaned if item]


class ExclusionCriteria(BaseModel):
    """
    Researcher-defined exclusion criteria.

    Empty strings and whitespace-only entries are silently removed.
    The system does NOT invent criteria.
    """
    criteria: List[str] = Field(
        default_factory=list,
        description="List of exclusion criteria.",
    )

    @field_validator("criteria", mode="before")
    @classmethod
    def clean_criteria(cls, v: List[str]) -> List[str]:
        if not isinstance(v, list):
            raise ValueError("criteria must be a list of strings.")
        cleaned = [item.strip() for item in v if isinstance(item, str)]
        return [item for item in cleaned if item]


# ---------------------------------------------------------------------------
# Sample Size Plan
# ---------------------------------------------------------------------------

class SampleSizePlan(BaseModel):
    """
    The canonical location for sample size planning.

    Sprint 1 does NOT calculate sample size.
    This model is the domain anchor for future sample-size engine integration.
    The system does NOT invent sample size figures.
    """
    planned_n: Optional[int] = Field(
        default=None,
        description="Planned total sample size (N).",
    )
    rationale: Optional[str] = Field(
        default=None,
        description="Rationale for the chosen sample size.",
    )
    notes: Optional[str] = Field(
        default=None,
        description="Additional notes on the sample size plan.",
    )

    @field_validator("planned_n")
    @classmethod
    def planned_n_must_be_positive(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v <= 0:
            raise ValueError("planned_n must be a positive integer.")
        return v


# ---------------------------------------------------------------------------
# Analysis Plan
# ---------------------------------------------------------------------------

class AnalysisPlan(BaseModel):
    """
    The canonical location for the statistical analysis plan.

    Sprint 1 does NOT implement statistical analysis.
    This model establishes the domain representation only.
    The system does NOT invent statistical methods.
    """
    primary_analysis_description: Optional[str] = Field(
        default=None,
        description="Description of the primary analysis approach.",
    )
    secondary_analyses: List[str] = Field(
        default_factory=list,
        description="List of secondary analysis descriptions.",
    )
    notes: Optional[str] = Field(
        default=None,
        description="Additional notes on the analysis plan.",
    )


# ---------------------------------------------------------------------------
# Research Task
# ---------------------------------------------------------------------------

class ResearchTask(BaseModel):
    """
    A task belonging to a ResearchProject.

    Tasks are auditable actions performed on or in service of the project.
    """
    id: str = Field(
        default_factory=_new_uuid,
        description="Unique identifier for this task.",
    )
    title: str = Field(
        ...,
        description="Short title of the task.",
    )
    description: str = Field(
        default="",
        description="Detailed description of the task.",
    )
    status: TaskStatus = Field(
        default=TaskStatus.TODO,
        description="Current status of the task.",
    )
    priority: TaskPriority = Field(
        default=TaskPriority.MEDIUM,
        description="Priority of the task.",
    )
    why: Optional[str] = Field(
        default=None,
        description="Rationale for why this task exists.",
    )
    dependencies: List[str] = Field(
        default_factory=list,
        description="List of task IDs that this task depends on.",
    )
    created_at: datetime = Field(
        default_factory=_now_utc,
        description="UTC timestamp when the task was created.",
    )
    completed_at: Optional[datetime] = Field(
        default=None,
        description="UTC timestamp when the task was completed, if applicable.",
    )

    @field_validator("title")
    @classmethod
    def title_must_not_be_empty(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("Task title must not be empty.")
        return stripped

    model_config = {"validate_assignment": True}


# ---------------------------------------------------------------------------
# ResearchProject — the single source of truth
# ---------------------------------------------------------------------------

class ResearchProject(BaseModel):
    """
    The canonical ResearchProject.

    This is the single source of truth for everything in a research project.

    All other models either belong to, derive from, or are associated with
    this object.

    Lifecycle:
        Tracked by `state` (ProjectState). There is no competing `status` field.

    No-Invention Principle:
        All fields that represent researcher-provided content are Optional.
        Missing information is represented as None, never filled with assumptions.
    """

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------
    id: str = Field(
        default_factory=_new_uuid,
        description="Stable unique identifier for this project.",
    )
    title: str = Field(
        ...,
        description="Human-readable project title.",
    )
    idea: str = Field(
        ...,
        description="The core research idea as articulated by the researcher.",
    )

    # ------------------------------------------------------------------
    # Timestamps
    # ------------------------------------------------------------------
    created_at: datetime = Field(
        default_factory=_now_utc,
        description="UTC timestamp when the project was created.",
    )
    updated_at: datetime = Field(
        default_factory=_now_utc,
        description="UTC timestamp of the last update.",
    )

    # ------------------------------------------------------------------
    # Lifecycle — exactly ONE canonical field
    # ------------------------------------------------------------------
    state: ProjectState = Field(
        default=ProjectState.IDEA,
        description="Current lifecycle state of the project.",
    )

    # ------------------------------------------------------------------
    # Research components — all Optional (no invention)
    # ------------------------------------------------------------------
    research_question: Optional[ResearchQuestion] = Field(
        default=None,
        description="The canonical research question.",
    )
    study_design: Optional[StudyDesign] = Field(
        default=None,
        description="The selected study design.",
    )
    population: Optional[Population] = Field(
        default=None,
        description="The target population.",
    )
    exposure: Optional[Exposure] = Field(
        default=None,
        description="The exposure of interest (observational studies).",
    )
    intervention: Optional[Intervention] = Field(
        default=None,
        description="The intervention (experimental studies).",
    )
    comparator: Optional[Comparator] = Field(
        default=None,
        description="The comparator / control.",
    )
    primary_outcome: Optional[Outcome] = Field(
        default=None,
        description="The single primary outcome.",
    )
    secondary_outcomes: List[Outcome] = Field(
        default_factory=list,
        description="Secondary outcomes.",
    )
    inclusion_criteria: InclusionCriteria = Field(
        default_factory=InclusionCriteria,
        description="Inclusion criteria for study participants.",
    )
    exclusion_criteria: ExclusionCriteria = Field(
        default_factory=ExclusionCriteria,
        description="Exclusion criteria for study participants.",
    )
    sample_size_plan: Optional[SampleSizePlan] = Field(
        default=None,
        description="Sample size plan.",
    )
    analysis_plan: Optional[AnalysisPlan] = Field(
        default=None,
        description="Statistical analysis plan.",
    )

    # ------------------------------------------------------------------
    # Tasks
    # ------------------------------------------------------------------
    tasks: List[ResearchTask] = Field(
        default_factory=list,
        description="Tasks associated with this project.",
    )

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------
    @field_validator("title")
    @classmethod
    def title_must_be_meaningful(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("Project title must not be empty.")
        if len(stripped) < 5:
            raise ValueError(
                f"Project title is too short ({len(stripped)} chars). "
                "Minimum is 5 characters."
            )
        return stripped

    @field_validator("idea")
    @classmethod
    def idea_must_be_meaningful(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("Project idea must not be empty.")
        if len(stripped) < 20:
            raise ValueError(
                f"Project idea is too short ({len(stripped)} chars). "
                "Minimum is 20 characters."
            )
        return stripped

    @model_validator(mode="after")
    def primary_outcome_is_primary(self) -> "ResearchProject":
        """
        Enforce that if a primary_outcome is provided,
        its is_primary flag is True.
        """
        if self.primary_outcome is not None and not self.primary_outcome.is_primary:
            raise ValueError(
                "primary_outcome.is_primary must be True. "
                "Use secondary_outcomes for non-primary outcomes."
            )
        return self

    model_config = {"validate_assignment": True}
