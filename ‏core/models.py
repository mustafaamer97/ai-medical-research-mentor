from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List, Optional
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


# ──────────────────────────────────────────────
# Sub-models
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
# Task Model
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
    schema_version: str = Field(default="1.0.0")
    saved_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"frozen": False}
