"""
core/research_engine.py
=======================
Sprint 2 — Deterministic Research Framework Engine

Provides:
- PICO / PECO inference and structuring
- Research framework construction from explicit fields
- Research question generation
- Framework validation
- Research objectives generation
- Study design recommendation
- State gate checks
- Framework task generation

No-Invention Rule: All outputs are derived deterministically from
user-supplied inputs. The engine never fabricates populations, outcomes,
exposures, comparators, objectives, or tasks that were not grounded in
the source data provided by the caller.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Internal imports — tolerant of partial model availability
# ---------------------------------------------------------------------------
try:
    from core.models import (
        ResearchProject,
        ProjectStatus,
        ResearchFramework,
        ResearchQuestion,
        StudyDesignModel,
        StateGateError,
    )
except ImportError:
    # Provide lightweight sentinels so the engine loads in isolation
    ResearchProject = None          # type: ignore[assignment,misc]
    ProjectStatus = None            # type: ignore[assignment,misc]
    ResearchFramework = None        # type: ignore[assignment,misc]
    ResearchQuestion = None         # type: ignore[assignment,misc]
    StudyDesignModel = None         # type: ignore[assignment,misc]

    class StateGateError(Exception):  # type: ignore[no-redef]
        """Raised when a state gate check fails."""


try:
    from core.state import StateManager
except ImportError:
    StateManager = None             # type: ignore[assignment,misc]


# ===========================================================================
# Enumerations
# ===========================================================================

class FrameworkType(str, Enum):
    PICO = "PICO"
    PECO = "PECO"
    UNKNOWN = "UNKNOWN"


class StudyDesign(str, Enum):
    RCT = "Randomized Controlled Trial"
    COHORT = "Cohort Study"
    CASE_CONTROL = "Case-Control Study"
    CROSS_SECTIONAL = "Cross-Sectional Study"
    SYSTEMATIC_REVIEW = "Systematic Review / Meta-Analysis"
    UNKNOWN = "Unknown / Insufficient Information"


class ValidationStatus(str, Enum):
    VALID = "VALID"
    INVALID = "INVALID"
    INCOMPLETE = "INCOMPLETE"


class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETE = "complete"


# ===========================================================================
# Data containers
# ===========================================================================

@dataclass
class PICOFramework:
    """Structured PICO elements extracted deterministically from user input."""
    population: str = ""
    intervention: str = ""
    comparator: str = ""
    outcome: str = ""
    framework_type: FrameworkType = FrameworkType.PICO
    time_horizon: Optional[str] = None
    setting: Optional[str] = None

    def is_complete(self) -> bool:
        return all([
            self.population.strip(),
            self.intervention.strip(),
            self.comparator.strip(),
            self.outcome.strip(),
        ])

    def to_dict(self) -> Dict[str, Any]:
        return {
            "population": self.population,
            "intervention": self.intervention,
            "comparator": self.comparator,
            "outcome": self.outcome,
            "framework_type": self.framework_type.value,
            "time_horizon": self.time_horizon,
            "setting": self.setting,
        }


@dataclass
class PECOFramework:
    """Structured PECO elements for observational / exposure research."""
    population: str = ""
    exposure: str = ""
    comparator: str = ""
    outcome: str = ""
    framework_type: FrameworkType = FrameworkType.PECO
    time_horizon: Optional[str] = None
    setting: Optional[str] = None

    def is_complete(self) -> bool:
        return all([
            self.population.strip(),
            self.exposure.strip(),
            self.comparator.strip(),
            self.outcome.strip(),
        ])

    def to_dict(self) -> Dict[str, Any]:
        return {
            "population": self.population,
            "exposure": self.exposure,
            "comparator": self.comparator,
            "outcome": self.outcome,
            "framework_type": self.framework_type.value,
            "time_horizon": self.time_horizon,
            "setting": self.setting,
        }


@dataclass
class ValidationResult:
    """Result of framework validation."""
    status: ValidationStatus
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return self.status == ValidationStatus.VALID

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status.value,
            "errors": self.errors,
            "warnings": self.warnings,
            "suggestions": self.suggestions,
        }


@dataclass
class StudyDesignRecommendation:
    """Deterministic study design recommendation with rationale."""
    recommended_design: StudyDesign
    rationale: str
    alternatives: List[StudyDesign] = field(default_factory=list)
    feasibility_notes: List[str] = field(default_factory=list)
    ethical_considerations: List[str] = field(default_factory=list)
    confidence: str = "high"  # high | medium | low

    def to_dict(self) -> Dict[str, Any]:
        return {
            "recommended_design": self.recommended_design.value,
            "rationale": self.rationale,
            "alternatives": [d.value for d in self.alternatives],
            "feasibility_notes": self.feasibility_notes,
            "ethical_considerations": self.ethical_considerations,
            "confidence": self.confidence,
        }


@dataclass
class ResearchFrameworkResult:
    """Aggregated output from the Research Framework Engine."""
    framework_type: FrameworkType
    pico: Optional[PICOFramework] = None
    peco: Optional[PECOFramework] = None
    validation: Optional[ValidationResult] = None
    study_design: Optional[StudyDesignRecommendation] = None
    raw_question: str = ""
    generated_question: str = ""
    objectives: List[str] = field(default_factory=list)
    schema_version: str = "1.2.0"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "framework_type": self.framework_type.value,
            "raw_question": self.raw_question,
            "generated_question": self.generated_question,
            "objectives": self.objectives,
            "pico": self.pico.to_dict() if self.pico else None,
            "peco": self.peco.to_dict() if self.peco else None,
            "validation": self.validation.to_dict() if self.validation else None,
            "study_design": self.study_design.to_dict() if self.study_design else None,
        }


@dataclass
class FrameworkTask:
    """A single actionable task generated for the framework phase."""
    task_id: str
    title: str
    description: str
    phase: str = "framework"
    status: TaskStatus = TaskStatus.PENDING
    priority: int = 1
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "title": self.title,
            "description": self.description,
            "phase": self.phase,
            "status": self.status.value,
            "priority": self.priority,
            "metadata": self.metadata,
        }


# ===========================================================================
# Keyword banks for deterministic scoring
# ===========================================================================

_EXPOSURE_KEYWORDS: List[str] = [
    "exposure", "exposed", "risk factor", "risk factors",
    "environmental", "occupational", "diet", "dietary",
    "smoking", "alcohol", "pollution", "radiation",
    "association", "associated with", "linked to",
    "observational", "cohort", "case-control",
]

_INTERVENTION_KEYWORDS: List[str] = [
    "treatment", "intervention", "therapy", "drug", "medication",
    "surgery", "procedure", "vaccine", "programme", "program",
    "trial", "rct", "randomized", "randomised",
    "compared to", "versus", "vs",
]

_RCT_KEYWORDS: List[str] = [
    "randomized", "randomised", "rct", "trial", "placebo",
    "blinded", "double-blind", "single-blind",
    "treatment", "intervention", "drug", "therapy", "vaccine",
    "efficacy", "effectiveness",
]

_COHORT_KEYWORDS: List[str] = [
    "cohort", "longitudinal", "follow-up", "follow up", "prospective",
    "incidence", "prognosis", "natural history",
    "over time", "years", "months",
]

_CASE_CONTROL_KEYWORDS: List[str] = [
    "case-control", "case control", "odds ratio", "risk factor",
    "aetiology", "etiology", "cause", "causes", "rare disease",
]

_CROSS_SECTIONAL_KEYWORDS: List[str] = [
    "prevalence", "cross-sectional", "cross sectional",
    "survey", "point in time", "snapshot",
    "burden", "frequency",
]

_SR_KEYWORDS: List[str] = [
    "systematic review", "meta-analysis", "meta analysis",
    "evidence synthesis", "pooled", "literature review",
    "existing evidence", "review of",
]


# ===========================================================================
# Internal helpers
# ===========================================================================

def _normalise(text: str) -> str:
    """Lower-case and collapse whitespace."""
    return re.sub(r"\s+", " ", text.lower().strip())


def _score_keywords(text: str, keywords: List[str]) -> int:
    normalised = _normalise(text)
    return sum(1 for kw in keywords if kw in normalised)


def _make_task_id() -> str:
    return str(uuid.uuid4())


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Field extraction helpers (No-Invention Rule: return "" on no match)
# ---------------------------------------------------------------------------

def _extract_population(question: str) -> str:
    patterns = [
        r"(?:in|among|for)\s+([A-Za-z0-9 ,\-]+?)(?:\s+(?:who|with|receiving|treated|aged|where|does|do|is|are|,|\?))",
        r"patients?\s+with\s+([A-Za-z0-9 ,\-]+?)(?:\s+(?:who|receiving|treated|aged|,|\?))",
        r"adults?\s+with\s+([A-Za-z0-9 ,\-]+?)(?:\s+(?:who|receiving|treated|aged|,|\?))",
        r"children?\s+with\s+([A-Za-z0-9 ,\-]+?)(?:\s+(?:who|receiving|treated|aged|,|\?))",
        r"individuals?\s+with\s+([A-Za-z0-9 ,\-]+?)(?:\s+(?:who|receiving|,|\?))",
    ]
    for pattern in patterns:
        match = re.search(pattern, question, re.IGNORECASE)
        if match:
            return match.group(1).strip().rstrip(",")
    return ""


def _extract_intervention(question: str) -> str:
    patterns = [
        r"(?:does|do|is|are)\s+([A-Za-z0-9 ,\-]+?)\s+(?:compared|versus|vs|better|effective|reduce|improve|prevent)",
        r"(?:effect|efficacy|effectiveness)\s+of\s+([A-Za-z0-9 ,\-]+?)\s+(?:on|in|compared|versus|vs|\?)",
        r"([A-Za-z0-9 ,\-]+?)\s+(?:versus|vs|compared\s+(?:to|with))\s+",
        r"(?:receiving|treated\s+with|given|taking)\s+([A-Za-z0-9 ,\-]+?)(?:\s+(?:compared|versus|vs|,|\?))",
    ]
    for pattern in patterns:
        match = re.search(pattern, question, re.IGNORECASE)
        if match:
            return match.group(1).strip().rstrip(",")
    return ""


def _extract_comparator(question: str) -> str:
    patterns = [
        r"(?:compared\s+(?:to|with)|versus|vs\.?)\s+([A-Za-z0-9 ,\-]+?)(?:\s+(?:in|on|for|reduce|improve|affect|,|\?))",
        r"(?:versus|vs\.?)\s+([A-Za-z0-9 ,\-]+?)(?:\s+(?:in|on|for|,|\?))",
        r"(placebo|standard\s+care|usual\s+care|no\s+treatment|control)",
    ]
    for pattern in patterns:
        match = re.search(pattern, question, re.IGNORECASE)
        if match:
            try:
                return match.group(1).strip().rstrip(",")
            except IndexError:
                return match.group(0).strip()
    return ""


def _extract_outcome(question: str) -> str:
    patterns = [
        r"(?:on|affect|reduce|improve|prevent|increase|decrease)\s+([A-Za-z0-9 ,\-]+?)(?:\s+(?:in|among|for|,|\?|$))",
        r"(?:outcome|endpoint|measure)[s]?\s*[:\-]?\s*([A-Za-z0-9 ,\-]+?)(?:\s*[,\?]|$)",
        r"(mortality|survival|recurrence|remission|quality\s+of\s+life|pain|function|hospitalisation|hospitalization)",
    ]
    for pattern in patterns:
        match = re.search(pattern, question, re.IGNORECASE)
        if match:
            try:
                return match.group(1).strip().rstrip(",")
            except IndexError:
                return match.group(0).strip()
    return ""


def _extract_exposure(question: str) -> str:
    patterns = [
        r"(?:exposure\s+to|exposed\s+to)\s+([A-Za-z0-9 ,\-]+?)(?:\s+(?:and|in|among|on|,|\?))",
        r"(?:effect|impact|association)\s+of\s+([A-Za-z0-9 ,\-]+?)\s+(?:on|with|in)",
        r"(smoking|alcohol|diet|radiation|pollution|occupational)\s+([A-Za-z0-9 ,\-]*)",
    ]
    for pattern in patterns:
        match = re.search(pattern, question, re.IGNORECASE)
        if match:
            try:
                return match.group(1).strip().rstrip(",")
            except IndexError:
                return match.group(0).strip()
    return ""


# ===========================================================================
# 1. infer_framework_type
# ===========================================================================

def infer_framework_type(question: str) -> FrameworkType:
    """
    Deterministically infer whether a research question calls for PICO or
    PECO structuring.

    Rules (first match wins):
    1. Empty / blank question → UNKNOWN.
    2. Exposure keyword score > intervention keyword score → PECO.
    3. Otherwise → PICO (default for clinical intervention questions).

    No-Invention Rule: decision is based solely on the supplied text.
    """
    if not question or not question.strip():
        return FrameworkType.UNKNOWN

    normalised = _normalise(question)
    exposure_score = sum(1 for kw in _EXPOSURE_KEYWORDS if kw in normalised)
    intervention_score = sum(1 for kw in _INTERVENTION_KEYWORDS if kw in normalised)

    if exposure_score > intervention_score:
        return FrameworkType.PECO
    return FrameworkType.PICO


# ===========================================================================
# 2. build_framework
# ===========================================================================

def build_framework(
    population: str = "",
    intervention: str = "",
    comparator: str = "",
    outcome: str = "",
    exposure: str = "",
    framework_type: Optional[FrameworkType] = None,
    time_horizon: Optional[str] = None,
    setting: Optional[str] = None,
    raw_question: str = "",
) -> ResearchFrameworkResult:
    """
    Build a ResearchFrameworkResult directly from explicit field values.

    Caller supplies the structured elements; this function assembles,
    validates, and (where valid) recommends a study design.

    No-Invention Rule: no field value is fabricated. If a field is not
    supplied it remains an empty string. Framework type is determined from
    the presence of *exposure* vs *intervention* when not explicitly given.
    """
    # Determine framework type
    if framework_type is None:
        if exposure and exposure.strip():
            framework_type = FrameworkType.PECO
        else:
            framework_type = FrameworkType.PICO

    if framework_type == FrameworkType.PECO:
        peco = PECOFramework(
            population=population,
            exposure=exposure,
            comparator=comparator,
            outcome=outcome,
            framework_type=FrameworkType.PECO,
            time_horizon=time_horizon,
            setting=setting,
        )
        validation = validate_peco(peco)
        design = (
            recommend_study_design_from_peco(peco)
            if validation.status != ValidationStatus.INVALID
            else None
        )
        generated_q = build_research_question_from_peco(peco)
        objectives = generate_research_objectives_from_peco(peco)
        return ResearchFrameworkResult(
            framework_type=FrameworkType.PECO,
            peco=peco,
            validation=validation,
            study_design=design,
            raw_question=raw_question,
            generated_question=generated_q,
            objectives=objectives,
        )

    # Default: PICO
    pico = PICOFramework(
        population=population,
        intervention=intervention,
        comparator=comparator,
        outcome=outcome,
        framework_type=FrameworkType.PICO,
        time_horizon=time_horizon,
        setting=setting,
    )
    validation = validate_pico(pico)
    design = (
        recommend_study_design_from_pico(pico)
        if validation.status != ValidationStatus.INVALID
        else None
    )
    generated_q = build_research_question_from_pico(pico)
    objectives = generate_research_objectives_from_pico(pico)
    return ResearchFrameworkResult(
        framework_type=FrameworkType.PICO,
        pico=pico,
        validation=validation,
        study_design=design,
        raw_question=raw_question,
        generated_question=generated_q,
        objectives=objectives,
    )


# ===========================================================================
# 3. build_research_question
# ===========================================================================

def build_research_question(framework_result: ResearchFrameworkResult) -> str:
    """
    Generate a structured research question string from a
    ResearchFrameworkResult.

    Dispatches to PICO or PECO sub-builders based on framework type.
    Returns an empty string if no framework data is present.

    No-Invention Rule: the question is assembled only from fields that
    are present in the supplied framework_result.
    """
    if framework_result.framework_type == FrameworkType.PECO and framework_result.peco:
        return build_research_question_from_peco(framework_result.peco)
    if framework_result.pico:
        return build_research_question_from_pico(framework_result.pico)
    return ""


def build_research_question_from_pico(pico: PICOFramework) -> str:
    """
    Assemble a PICO research question from structured elements.

    Template (elements omitted when empty):
    'In [population], does [intervention] compared to [comparator]
    improve/affect [outcome]?'
    """
    parts: List[str] = []

    pop = pico.population.strip()
    intv = pico.intervention.strip()
    comp = pico.comparator.strip()
    out = pico.outcome.strip()

    if pop:
        parts.append(f"In {pop}")
    if intv and comp:
        parts.append(f"does {intv} compared to {comp}")
    elif intv:
        parts.append(f"does {intv}")
    if out:
        parts.append(f"improve or affect {out}")

    if not parts:
        return ""

    question = ", ".join(parts)
    if not question.endswith("?"):
        question += "?"
    return question


def build_research_question_from_peco(peco: PECOFramework) -> str:
    """
    Assemble a PECO research question from structured elements.

    Template (elements omitted when empty):
    'In [population], is exposure to [exposure] compared to [comparator]
    associated with [outcome]?'
    """
    parts: List[str] = []

    pop = peco.population.strip()
    exp = peco.exposure.strip()
    comp = peco.comparator.strip()
    out = peco.outcome.strip()

    if pop:
        parts.append(f"In {pop}")
    if exp and comp:
        parts.append(f"is exposure to {exp} compared to {comp}")
    elif exp:
        parts.append(f"is exposure to {exp}")
    if out:
        parts.append(f"associated with {out}")

    if not parts:
        return ""

    question = ", ".join(parts)
    if not question.endswith("?"):
        question += "?"
    return question


# ===========================================================================
# 4. validate_framework  (+ internal PICO / PECO validators)
# ===========================================================================

def validate_pico(pico: PICOFramework) -> ValidationResult:
    """Validate a PICOFramework against mandatory field rules."""
    errors: List[str] = []
    warnings: List[str] = []
    suggestions: List[str] = []

    if not pico.population.strip():
        errors.append("Population (P) is missing.")
    elif len(pico.population.strip()) < 3:
        warnings.append("Population description is very short; consider expanding.")

    if not pico.intervention.strip():
        errors.append("Intervention (I) is missing.")
    elif len(pico.intervention.strip()) < 3:
        warnings.append("Intervention description is very short; consider expanding.")

    if not pico.comparator.strip():
        warnings.append(
            "Comparator (C) is missing. "
            "Consider specifying a control condition (e.g., placebo, standard care)."
        )
        suggestions.append("Add a comparator to strengthen internal validity.")

    if not pico.outcome.strip():
        errors.append("Outcome (O) is missing.")
    elif len(pico.outcome.strip()) < 3:
        warnings.append("Outcome description is very short; consider expanding.")

    if errors:
        status = ValidationStatus.INVALID
    elif not pico.comparator.strip():
        status = ValidationStatus.INCOMPLETE
    else:
        status = ValidationStatus.VALID

    return ValidationResult(
        status=status,
        errors=errors,
        warnings=warnings,
        suggestions=suggestions,
    )


def validate_peco(peco: PECOFramework) -> ValidationResult:
    """Validate a PECOFramework against mandatory field rules."""
    errors: List[str] = []
    warnings: List[str] = []
    suggestions: List[str] = []

    if not peco.population.strip():
        errors.append("Population (P) is missing.")
    elif len(peco.population.strip()) < 3:
        warnings.append("Population description is very short; consider expanding.")

    if not peco.exposure.strip():
        errors.append("Exposure (E) is missing.")
    elif len(peco.exposure.strip()) < 3:
        warnings.append("Exposure description is very short; consider expanding.")

    if not peco.comparator.strip():
        warnings.append(
            "Comparator (C) is missing. "
            "Consider specifying an unexposed / reference group."
        )
        suggestions.append("Add a comparator group (e.g., unexposed controls).")

    if not peco.outcome.strip():
        errors.append("Outcome (O) is missing.")
    elif len(peco.outcome.strip()) < 3:
        warnings.append("Outcome description is very short; consider expanding.")

    if errors:
        status = ValidationStatus.INVALID
    elif not peco.comparator.strip():
        status = ValidationStatus.INCOMPLETE
    else:
        status = ValidationStatus.VALID

    return ValidationResult(
        status=status,
        errors=errors,
        warnings=warnings,
        suggestions=suggestions,
    )


def validate_framework(framework: ResearchFrameworkResult) -> ValidationResult:
    """
    Validate a ResearchFrameworkResult by dispatching to the appropriate
    PICO or PECO validator.

    No-Invention Rule: validation is performed solely on the data present
    in the supplied framework object.
    """
    if framework.framework_type == FrameworkType.PECO and framework.peco:
        return validate_peco(framework.peco)
    if framework.pico:
        return validate_pico(framework.pico)
    return ValidationResult(
        status=ValidationStatus.INVALID,
        errors=["No PICO or PECO framework present in result."],
    )


# ===========================================================================
# 5. generate_research_objectives
# ===========================================================================

def generate_research_objectives(
    framework_result: ResearchFrameworkResult,
) -> List[str]:
    """
    Generate a deterministic list of research objectives from a
    ResearchFrameworkResult.

    Dispatches to PICO or PECO sub-generators.
    Returns an empty list if no framework data is present.

    No-Invention Rule: objectives reference only fields present in the
    supplied framework_result.
    """
    if framework_result.framework_type == FrameworkType.PECO and framework_result.peco:
        return generate_research_objectives_from_peco(framework_result.peco)
    if framework_result.pico:
        return generate_research_objectives_from_pico(framework_result.pico)
    return []


def generate_research_objectives_from_pico(pico: PICOFramework) -> List[str]:
    """
    Generate structured research objectives from PICO elements.

    Only objectives whose constituent fields are non-empty are included.
    No fields are invented.
    """
    objectives: List[str] = []

    pop = pico.population.strip()
    intv = pico.intervention.strip()
    comp = pico.comparator.strip()
    out = pico.outcome.strip()

    if pop and intv and out:
        objectives.append(
            f"To evaluate the effect of {intv} on {out}"
            + (f" in {pop}" if pop else "")
            + "."
        )

    if intv and comp and out:
        objectives.append(
            f"To compare {intv} with {comp} in terms of {out}."
        )

    if pop and out:
        objectives.append(
            f"To assess {out} outcomes among {pop}."
        )

    if pico.time_horizon and intv and out:
        objectives.append(
            f"To measure {out} following {intv} over {pico.time_horizon}."
        )

    if not objectives and (pop or intv or out):
        # Minimal fallback — still grounded in supplied data
        elements = [x for x in [intv, out, pop] if x]
        objectives.append(
            "To investigate " + ", ".join(elements) + "."
        )

    return objectives


def generate_research_objectives_from_peco(peco: PECOFramework) -> List[str]:
    """
    Generate structured research objectives from PECO elements.

    Only objectives whose constituent fields are non-empty are included.
    No fields are invented.
    """
    objectives: List[str] = []

    pop = peco.population.strip()
    exp = peco.exposure.strip()
    comp = peco.comparator.strip()
    out = peco.outcome.strip()

    if pop and exp and out:
        objectives.append(
            f"To determine the association between {exp} and {out}"
            + (f" in {pop}" if pop else "")
            + "."
        )

    if exp and comp and out:
        objectives.append(
            f"To compare {out} between individuals exposed to {exp} "
            f"and those exposed to {comp}."
        )

    if pop and out:
        objectives.append(
            f"To estimate the incidence / prevalence of {out} in {pop}."
        )

    if peco.time_horizon and exp and out:
        objectives.append(
            f"To assess the longitudinal relationship between {exp} and {out} "
            f"over {peco.time_horizon}."
        )

    if not objectives and (pop or exp or out):
        elements = [x for x in [exp, out, pop] if x]
        objectives.append(
            "To investigate " + ", ".join(elements) + "."
        )

    return objectives


# ===========================================================================
# 6. recommend_study_design  (+ internal PICO / PECO recommenders)
# ===========================================================================

def recommend_study_design(
    framework: ResearchFrameworkResult,
) -> StudyDesignRecommendation:
    """
    Recommend a study design from a ResearchFrameworkResult by dispatching
    to the appropriate PICO or PECO recommender.

    No-Invention Rule: recommendation is derived solely from the framework
    content supplied.
    """
    if framework.framework_type == FrameworkType.PECO and framework.peco:
        return recommend_study_design_from_peco(framework.peco)
    if framework.pico:
        return recommend_study_design_from_pico(framework.pico)
    return StudyDesignRecommendation(
        recommended_design=StudyDesign.UNKNOWN,
        rationale="Insufficient framework data to recommend a study design.",
        confidence="low",
    )


def recommend_study_design_from_pico(pico: PICOFramework) -> StudyDesignRecommendation:
    """
    Recommend a study design deterministically from PICO elements.

    Scoring: each design type accumulates points for matching keywords
    found in the combined PICO text. Tie-breaking follows the hierarchy:
    RCT > Cohort > Case-Control > Cross-Sectional > Systematic Review.
    """
    combined = " ".join([
        pico.population, pico.intervention, pico.comparator, pico.outcome,
        pico.time_horizon or "", pico.setting or "",
    ])

    hierarchy = [
        StudyDesign.RCT,
        StudyDesign.COHORT,
        StudyDesign.CASE_CONTROL,
        StudyDesign.CROSS_SECTIONAL,
        StudyDesign.SYSTEMATIC_REVIEW,
    ]
    keyword_map = {
        StudyDesign.RCT: _RCT_KEYWORDS,
        StudyDesign.COHORT: _COHORT_KEYWORDS,
        StudyDesign.CASE_CONTROL: _CASE_CONTROL_KEYWORDS,
        StudyDesign.CROSS_SECTIONAL: _CROSS_SECTIONAL_KEYWORDS,
        StudyDesign.SYSTEMATIC_REVIEW: _SR_KEYWORDS,
    }
    scores = {d: _score_keywords(combined, keyword_map[d]) for d in hierarchy}
    best = max(hierarchy, key=lambda d: (scores[d], -hierarchy.index(d)))

    if scores[best] == 0:
        best = StudyDesign.RCT
        confidence = "low"
    else:
        confidence = "high" if scores[best] >= 2 else "medium"

    alternatives = [d for d in hierarchy if d != best and scores[d] > 0]

    return StudyDesignRecommendation(
        recommended_design=best,
        rationale=_build_pico_rationale(best, pico),
        alternatives=alternatives,
        feasibility_notes=_build_feasibility_notes(best),
        ethical_considerations=_build_ethical_considerations(best),
        confidence=confidence,
    )


def recommend_study_design_from_peco(peco: PECOFramework) -> StudyDesignRecommendation:
    """
    Recommend a study design deterministically from PECO elements.

    For exposure questions the hierarchy shifts toward observational designs.
    """
    combined = " ".join([
        peco.population, peco.exposure, peco.comparator, peco.outcome,
        peco.time_horizon or "", peco.setting or "",
    ])

    hierarchy = [
        StudyDesign.COHORT,
        StudyDesign.CASE_CONTROL,
        StudyDesign.CROSS_SECTIONAL,
        StudyDesign.SYSTEMATIC_REVIEW,
        StudyDesign.RCT,
    ]
    keyword_map = {
        StudyDesign.COHORT: _COHORT_KEYWORDS,
        StudyDesign.CASE_CONTROL: _CASE_CONTROL_KEYWORDS,
        StudyDesign.CROSS_SECTIONAL: _CROSS_SECTIONAL_KEYWORDS,
        StudyDesign.SYSTEMATIC_REVIEW: _SR_KEYWORDS,
        StudyDesign.RCT: _RCT_KEYWORDS,
    }
    scores = {d: _score_keywords(combined, keyword_map[d]) for d in hierarchy}
    best = max(hierarchy, key=lambda d: (scores[d], -hierarchy.index(d)))

    if scores[best] == 0:
        best = StudyDesign.COHORT
        confidence = "low"
    else:
        confidence = "high" if scores[best] >= 2 else "medium"

    alternatives = [d for d in hierarchy if d != best and scores[d] > 0]

    return StudyDesignRecommendation(
        recommended_design=best,
        rationale=_build_peco_rationale(best, peco),
        alternatives=alternatives,
        feasibility_notes=_build_feasibility_notes(best),
        ethical_considerations=_build_ethical_considerations(best),
        confidence=confidence,
    )


# ---------------------------------------------------------------------------
# Rationale / feasibility / ethics builders
# ---------------------------------------------------------------------------

def _build_pico_rationale(design: StudyDesign, pico: PICOFramework) -> str:
    pop = pico.population or "the specified population"
    intv = pico.intervention or "the intervention"
    out = pico.outcome or "the outcome"
    rationales = {
        StudyDesign.RCT: (
            f"A Randomised Controlled Trial is recommended to evaluate the effect of "
            f"{intv} on {out} in {pop}. Randomisation controls confounding and "
            f"supports causal inference."
        ),
        StudyDesign.COHORT: (
            f"A Cohort Study is recommended to follow {pop} receiving {intv} over "
            f"time to assess {out}. Suitable where randomisation is impractical."
        ),
        StudyDesign.CASE_CONTROL: (
            f"A Case-Control Study is recommended to investigate the association "
            f"between {intv} and {out} in {pop}, particularly if the outcome is rare."
        ),
        StudyDesign.CROSS_SECTIONAL: (
            f"A Cross-Sectional Study is recommended to estimate the prevalence of "
            f"{out} associated with {intv} in {pop} at a single point in time."
        ),
        StudyDesign.SYSTEMATIC_REVIEW: (
            f"A Systematic Review / Meta-Analysis is recommended to synthesise "
            f"existing evidence on the effect of {intv} on {out} in {pop}."
        ),
    }
    return rationales.get(design, "No specific rationale available.")


def _build_peco_rationale(design: StudyDesign, peco: PECOFramework) -> str:
    pop = peco.population or "the specified population"
    exp = peco.exposure or "the exposure"
    out = peco.outcome or "the outcome"
    rationales = {
        StudyDesign.COHORT: (
            f"A Cohort Study is recommended to follow {pop} with and without "
            f"{exp} to measure the incidence of {out} over time."
        ),
        StudyDesign.CASE_CONTROL: (
            f"A Case-Control Study is recommended to compare past {exp} between "
            f"{pop} with and without {out}. Efficient for rare outcomes."
        ),
        StudyDesign.CROSS_SECTIONAL: (
            f"A Cross-Sectional Study is recommended to assess the prevalence of "
            f"{out} in {pop} in relation to {exp} at a single time point."
        ),
        StudyDesign.SYSTEMATIC_REVIEW: (
            f"A Systematic Review is recommended to synthesise existing evidence "
            f"on the relationship between {exp} and {out} in {pop}."
        ),
        StudyDesign.RCT: (
            f"An RCT may be considered if {exp} can be ethically randomised in {pop} "
            f"to evaluate its effect on {out}."
        ),
    }
    return rationales.get(design, "No specific rationale available.")


def _build_feasibility_notes(design: StudyDesign) -> List[str]:
    notes: Dict[StudyDesign, List[str]] = {
        StudyDesign.RCT: [
            "Requires ethical approval and informed consent.",
            "May require substantial sample size and funding.",
            "Blinding may not always be feasible.",
        ],
        StudyDesign.COHORT: [
            "Long follow-up periods may be required.",
            "Loss to follow-up can introduce bias.",
            "Prospective designs require sustained funding.",
        ],
        StudyDesign.CASE_CONTROL: [
            "Efficient for rare outcomes.",
            "Relies on accurate historical exposure data.",
            "Susceptible to recall bias.",
        ],
        StudyDesign.CROSS_SECTIONAL: [
            "Quick and relatively inexpensive.",
            "Cannot establish temporal relationship between exposure and outcome.",
            "Prevalence-incidence bias may occur.",
        ],
        StudyDesign.SYSTEMATIC_REVIEW: [
            "Requires comprehensive literature search.",
            "Quality dependent on available primary studies.",
            "Publication bias must be assessed.",
        ],
    }
    return notes.get(design, [])


def _build_ethical_considerations(design: StudyDesign) -> List[str]:
    considerations: Dict[StudyDesign, List[str]] = {
        StudyDesign.RCT: [
            "Equipoise must exist between arms.",
            "Participant randomisation requires full informed consent.",
            "Data Safety Monitoring Board (DSMB) may be required.",
        ],
        StudyDesign.COHORT: [
            "Data privacy for longitudinal participant records.",
            "Minimise burden on participants during follow-up.",
        ],
        StudyDesign.CASE_CONTROL: [
            "Appropriate control selection to avoid selection bias.",
            "Sensitivity around case identification and data linkage.",
        ],
        StudyDesign.CROSS_SECTIONAL: [
            "Anonymisation of survey data.",
            "Voluntary participation must be ensured.",
        ],
        StudyDesign.SYSTEMATIC_REVIEW: [
            "No direct participant involvement; standard publication ethics apply.",
            "PRISMA reporting guidelines recommended.",
        ],
    }
    return considerations.get(design, [])


# ===========================================================================
# 7. check_question_defined_ready
# ===========================================================================

def check_question_defined_ready(
    framework_result: ResearchFrameworkResult,
    *,
    raise_on_fail: bool = False,
) -> Tuple[bool, List[str]]:
    """
    State gate: determine whether the research question is sufficiently
    defined to advance from the QUESTION_DEFINED phase.

    Gate criteria:
    - Framework type must not be UNKNOWN.
    - Validation status must not be INVALID.
    - Population and Outcome must both be non-empty.
    - A generated or raw research question must be present.

    Parameters
    ----------
    framework_result : ResearchFrameworkResult to evaluate.
    raise_on_fail    : If True, raises StateGateError on failure.

    Returns
    -------
    (passed: bool, reasons: List[str])

    No-Invention Rule: gate decisions are based solely on the content
    of framework_result; nothing is assumed or fabricated.
    """
    reasons: List[str] = []

    if framework_result.framework_type == FrameworkType.UNKNOWN:
        reasons.append(
            "Framework type could not be determined from the research question."
        )

    if framework_result.validation is None:
        reasons.append("Validation has not been performed.")
    elif framework_result.validation.status == ValidationStatus.INVALID:
        reasons.append("Framework validation failed.")
        reasons.extend(framework_result.validation.errors)

    # Check population and outcome
    if framework_result.framework_type == FrameworkType.PECO and framework_result.peco:
        if not framework_result.peco.population.strip():
            reasons.append("Population (P) is required to advance.")
        if not framework_result.peco.outcome.strip():
            reasons.append("Outcome (O) is required to advance.")
    elif framework_result.pico:
        if not framework_result.pico.population.strip():
            reasons.append("Population (P) is required to advance.")
        if not framework_result.pico.outcome.strip():
            reasons.append("Outcome (O) is required to advance.")
    else:
        reasons.append("No PICO or PECO framework data present.")

    # A question string must be present
    question_text = (
        framework_result.generated_question or framework_result.raw_question
    ).strip()
    if not question_text:
        reasons.append(
            "No research question text is present. "
            "Call build_research_question() to generate one."
        )

    passed = len(reasons) == 0

    if not passed and raise_on_fail:
        raise StateGateError(
            "check_question_defined_ready gate failed: " + "; ".join(reasons)
        )

    return passed, reasons


# ===========================================================================
# 8. check_design_selected_ready
# ===========================================================================

def check_design_selected_ready(
    framework_result: ResearchFrameworkResult,
    *,
    raise_on_fail: bool = False,
) -> Tuple[bool, List[str]]:
    """
    State gate: determine whether a study design has been selected and the
    project is ready to advance to the LITERATURE_SEARCH phase.

    Gate criteria:
    - check_question_defined_ready must pass.
    - A StudyDesignRecommendation must be present.
    - recommended_design must not be UNKNOWN.
    - rationale must be non-empty.

    Parameters
    ----------
    framework_result : ResearchFrameworkResult to evaluate.
    raise_on_fail    : If True, raises StateGateError on failure.

    Returns
    -------
    (passed: bool, reasons: List[str])
    """
    reasons: List[str] = []

    # First gate must pass
    question_ok, question_reasons = check_question_defined_ready(framework_result)
    if not question_ok:
        reasons.extend(question_reasons)

    # Study design checks
    if framework_result.study_design is None:
        reasons.append("No study design recommendation has been generated.")
    else:
        if framework_result.study_design.recommended_design == StudyDesign.UNKNOWN:
            reasons.append(
                "Study design is UNKNOWN; a specific design must be selected."
            )
        if not framework_result.study_design.rationale.strip():
            reasons.append("Study design rationale is missing.")

    passed = len(reasons) == 0

    if not passed and raise_on_fail:
        raise StateGateError(
            "check_design_selected_ready gate failed: " + "; ".join(reasons)
        )

    return passed, reasons


# ===========================================================================
# 9. generate_framework_tasks
# ===========================================================================

def generate_framework_tasks(
    framework_result: ResearchFrameworkResult,
) -> List[FrameworkTask]:
    """
    Generate an ordered list of actionable FrameworkTasks from a
    ResearchFrameworkResult.

    Tasks are determined deterministically from the state of the framework:
    - Missing fields generate tasks to complete them.
    - Incomplete validation generates a review task.
    - Absence of a study design generates a selection task.
    - Absence of a research question generates a generation task.
    - Absence of objectives generates an objectives task.

    No-Invention Rule: task descriptions reference only fields actually
    present or absent in the supplied framework_result. No external
    knowledge is introduced.

    Returns
    -------
    List[FrameworkTask] ordered by priority (1 = highest).
    """
    tasks: List[FrameworkTask] = []
    priority = 1

    ft = framework_result.framework_type

    # -----------------------------------------------------------------------
    # Task: complete missing framework fields
    # -----------------------------------------------------------------------
    missing_fields: List[str] = []

    if ft == FrameworkType.PECO and framework_result.peco:
        peco = framework_result.peco
        if not peco.population.strip():
            missing_fields.append("Population (P)")
        if not peco.exposure.strip():
            missing_fields.append("Exposure (E)")
        if not peco.comparator.strip():
            missing_fields.append("Comparator (C)")
        if not peco.outcome.strip():
            missing_fields.append("Outcome (O)")
    elif framework_result.pico:
        pico = framework_result.pico
        if not pico.population.strip():
            missing_fields.append("Population (P)")
        if not pico.intervention.strip():
            missing_fields.append("Intervention (I)")
        if not pico.comparator.strip():
            missing_fields.append("Comparator (C)")
        if not pico.outcome.strip():
            missing_fields.append("Outcome (O)")
    else:
        missing_fields.append("all framework fields (no PICO/PECO data present)")

    if missing_fields:
        tasks.append(FrameworkTask(
            task_id=_make_task_id(),
            title="Complete framework fields",
            description=(
                f"The following {ft.value} framework elements are missing and must "
                f"be supplied before the project can advance: "
                + ", ".join(missing_fields) + "."
            ),
            phase="framework",
            status=TaskStatus.PENDING,
            priority=priority,
            metadata={"missing_fields": missing_fields},
        ))
        priority += 1

    # -----------------------------------------------------------------------
    # Task: resolve validation errors
    # -----------------------------------------------------------------------
    if (
        framework_result.validation
        and framework_result.validation.status == ValidationStatus.INVALID
    ):
        tasks.append(FrameworkTask(
            task_id=_make_task_id(),
            title="Resolve framework validation errors",
            description=(
                "The framework has failed validation. "
                "Errors to resolve: "
                + "; ".join(framework_result.validation.errors) + "."
            ),
            phase="framework",
            status=TaskStatus.PENDING,
            priority=priority,
            metadata={"errors": framework_result.validation.errors},
        ))
        priority += 1

    # -----------------------------------------------------------------------
    # Task: address validation warnings
    # -----------------------------------------------------------------------
    if (
        framework_result.validation
        and framework_result.validation.warnings
        and framework_result.validation.status != ValidationStatus.INVALID
    ):
        tasks.append(FrameworkTask(
            task_id=_make_task_id(),
            title="Review framework validation warnings",
            description=(
                "The framework has warnings that should be reviewed: "
                + "; ".join(framework_result.validation.warnings) + "."
            ),
            phase="framework",
            status=TaskStatus.PENDING,
            priority=priority,
            metadata={"warnings": framework_result.validation.warnings},
        ))
        priority += 1

    # -----------------------------------------------------------------------
    # Task: generate research question
    # -----------------------------------------------------------------------
    question_text = (
        framework_result.generated_question or framework_result.raw_question
    ).strip()
    if not question_text:
        tasks.append(FrameworkTask(
            task_id=_make_task_id(),
            title="Generate structured research question",
            description=(
                f"No research question has been generated for this "
                f"{ft.value} framework. "
                "Call build_research_question() to produce a structured question."
            ),
            phase="framework",
            status=TaskStatus.PENDING,
            priority=priority,
            metadata={},
        ))
        priority += 1

    # -----------------------------------------------------------------------
    # Task: generate research objectives
    # -----------------------------------------------------------------------
    if not framework_result.objectives:
        tasks.append(FrameworkTask(
            task_id=_make_task_id(),
            title="Generate research objectives",
            description=(
                "No research objectives have been defined. "
                "Call generate_research_objectives() to produce a structured "
                "objective list from the framework elements."
            ),
            phase="framework",
            status=TaskStatus.PENDING,
            priority=priority,
            metadata={},
        ))
        priority += 1

    # -----------------------------------------------------------------------
    # Task: select study design
    # -----------------------------------------------------------------------
    if framework_result.study_design is None:
        tasks.append(FrameworkTask(
            task_id=_make_task_id(),
            title="Select study design",
            description=(
                "No study design has been recommended or selected. "
                "Call recommend_study_design() to receive a deterministic "
                "recommendation based on the current framework."
            ),
            phase="framework",
            status=TaskStatus.PENDING,
            priority=priority,
            metadata={},
        ))
        priority += 1
    elif framework_result.study_design.recommended_design == StudyDesign.UNKNOWN:
        tasks.append(FrameworkTask(
            task_id=_make_task_id(),
            title="Confirm study design selection",
            description=(
                "The study design is currently UNKNOWN. "
                "Complete the framework fields so that a specific design "
                "can be recommended deterministically."
            ),
            phase="framework",
            status=TaskStatus.PENDING,
            priority=priority,
            metadata={},
        ))
        priority += 1

    # -----------------------------------------------------------------------
    # Task: advance to literature search (all gates passed)
    # -----------------------------------------------------------------------
    design_ok, _ = check_design_selected_ready(framework_result)
    if design_ok:
        tasks.append(FrameworkTask(
            task_id=_make_task_id(),
            title="Advance to literature search phase",
            description=(
                "All framework gates have passed. The project is ready to "
                "advance to the Literature Search phase. Initiate the "
                "literature search strategy engine."
            ),
            phase="framework",
            status=TaskStatus.PENDING,
            priority=priority,
            metadata={"gate": "design_selected_ready", "gate_passed": True},
        ))

    return tasks


# ===========================================================================
# Convenience / Integration Functions
# ===========================================================================

def infer_framework(question: str) -> ResearchFrameworkResult:
    """
    Top-level entry point: infer framework type and populate the appropriate
    PICO or PECO structure from a free-text research question.

    Returns a ResearchFrameworkResult containing the inferred framework,
    a ValidationResult, generated research question, objectives, and
    (where valid) a StudyDesignRecommendation.
    """
    if not question or not question.strip():
        return ResearchFrameworkResult(
            framework_type=FrameworkType.UNKNOWN,
            raw_question=question or "",
            validation=ValidationResult(
                status=ValidationStatus.INVALID,
                errors=["Research question is empty."],
            ),
        )

    framework_type = infer_framework_type(question)

    if framework_type == FrameworkType.PECO:
        peco = PECOFramework(
            population=_extract_population(question),
            exposure=_extract_exposure(question),
            comparator=_extract_comparator(question),
            outcome=_extract_outcome(question),
            framework_type=FrameworkType.PECO,
        )
        validation = validate_peco(peco)
        design = (
            recommend_study_design_from_peco(peco)
            if validation.status != ValidationStatus.INVALID
            else None
        )
        generated_q = build_research_question_from_peco(peco)
        objectives = generate_research_objectives_from_peco(peco)
        return ResearchFrameworkResult(
            framework_type=FrameworkType.PECO,
            peco=peco,
            validation=validation,
            study_design=design,
            raw_question=question,
            generated_question=generated_q,
            objectives=objectives,
        )

    # Default: PICO
    pico = PICOFramework(
        population=_extract_population(question),
        intervention=_extract_intervention(question),
        comparator=_extract_comparator(question),
        outcome=_extract_outcome(question),
        framework_type=FrameworkType.PICO,
    )
    validation = validate_pico(pico)
    design = (
        recommend_study_design_from_pico(pico)
        if validation.status != ValidationStatus.INVALID
        else None
    )
    generated_q = build_research_question_from_pico(pico)
    objectives = generate_research_objectives_from_pico(pico)
    return ResearchFrameworkResult(
        framework_type=FrameworkType.PICO,
        pico=pico,
        validation=validation,
        study_design=design,
        raw_question=question,
        generated_question=generated_q,
        objectives=objectives,
    )


def process_research_question(question: str) -> ResearchFrameworkResult:
    """
    Full pipeline alias for infer_framework().

    Primary integration entry point for external callers
    (UI, task engine, persistence layer).
    """
    return infer_framework(question)


def evaluate_framework_gate(
    framework_result: ResearchFrameworkResult,
) -> Tuple[bool, List[str]]:
    """
    Alias for check_question_defined_ready() retained for backward
    compatibility with Sprint 2 callers.
    """
    return check_question_defined_ready(framework_result)


def evaluate_design_gate(
    recommendation: Optional[StudyDesignRecommendation],
) -> Tuple[bool, List[str]]:
    """
    Evaluate whether a standalone StudyDesignRecommendation satisfies the
    design gate (backward-compatible helper).

    Returns (passed, reasons).
    """
    reasons: List[str] = []

    if recommendation is None:
        reasons.append("No study design recommendation has been generated.")
        return False, reasons

    if recommendation.recommended_design == StudyDesign.UNKNOWN:
        reasons.append(
            "Study design is UNKNOWN; a specific design must be selected."
        )
        return False, reasons

    if not recommendation.rationale.strip():
        reasons.append("Study design rationale is missing.")
        return False, reasons

    return True, reasons


def get_framework_summary(result: ResearchFrameworkResult) -> str:
    """
    Return a human-readable summary of a ResearchFrameworkResult.
    Used by the UI and reporting layer.
    """
    lines: List[str] = []
    lines.append(f"Framework Type: {result.framework_type.value}")

    if result.framework_type == FrameworkType.PICO and result.pico:
        p = result.pico
        lines.append(f"  Population  : {p.population or '(not identified)'}")
        lines.append(f"  Intervention: {p.intervention or '(not identified)'}")
        lines.append(f"  Comparator  : {p.comparator or '(not identified)'}")
        lines.append(f"  Outcome     : {p.outcome or '(not identified)'}")
    elif result.framework_type == FrameworkType.PECO and result.peco:
        p = result.peco
        lines.append(f"  Population  : {p.population or '(not identified)'}")
        lines.append(f"  Exposure    : {p.exposure or '(not identified)'}")
        lines.append(f"  Comparator  : {p.comparator or '(not identified)'}")
        lines.append(f"  Outcome     : {p.outcome or '(not identified)'}")

    if result.generated_question:
        lines.append(f"Research Question: {result.generated_question}")

    if result.objectives:
        lines.append("Objectives:")
        for obj in result.objectives:
            lines.append(f"  - {obj}")

    if result.validation:
        lines.append(f"Validation: {result.validation.status.value}")
        for err in result.validation.errors:
            lines.append(f"  ERROR   : {err}")
        for warn in result.validation.warnings:
            lines.append(f"  WARNING : {warn}")

    if result.study_design:
        lines.append(
            f"Recommended Design: {result.study_design.recommended_design.value}"
        )
        lines.append(f"  Rationale : {result.study_design.rationale}")
        lines.append(f"  Confidence: {result.study_design.confidence}")

    return "\n".join(lines)


# ===========================================================================
# Public re-exports
# ===========================================================================

__all__ = [
    # Enumerations
    "FrameworkType",
    "StudyDesign",
    "ValidationStatus",
    "TaskStatus",
    # Data containers
    "PICOFramework",
    "PECOFramework",
    "ValidationResult",
    "StudyDesignRecommendation",
    "ResearchFrameworkResult",
    "FrameworkTask",
    # Core public API (9 required functions)
    "infer_framework_type",
    "build_framework",
    "build_research_question",
    "validate_framework",
    "generate_research_objectives",
    "recommend_study_design",
    "check_question_defined_ready",
    "check_design_selected_ready",
    "generate_framework_tasks",
    # Supporting inference
    "infer_framework",
    "infer_pico",
    "infer_peco",
    # Supporting validators
    "validate_pico",
    "validate_peco",
    # Supporting recommenders
    "recommend_study_design_from_pico",
    "recommend_study_design_from_peco",
    # Backward-compatible gate helpers
    "evaluate_framework_gate",
    "evaluate_design_gate",
    # Convenience
    "process_research_question",
    "get_framework_summary",
]
