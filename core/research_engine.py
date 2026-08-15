"""
core/research_engine.py
=======================
Sprint 2 — Deterministic Research Framework Engine

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
        ResearchFramework,
        StudyDesignModel,
        FrameworkType as ModelFrameworkType,
    )
    _MODELS_AVAILABLE = True
except ImportError:  # pragma: no cover
    ResearchProject = None          # type: ignore[assignment,misc]
    ResearchFramework = None        # type: ignore[assignment,misc]
    StudyDesignModel = None         # type: ignore[assignment,misc]
    ModelFrameworkType = None       # type: ignore[assignment,misc]
    _MODELS_AVAILABLE = False

try:
    from core.state import StateGateError
except ImportError:  # pragma: no cover
    class StateGateError(Exception):  # type: ignore[no-redef]
        """Raised when a state gate check fails."""


# ===========================================================================
# Engine-internal Enumerations
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
    recommended_design: StudyDesign
    rationale: str
    alternatives: List[StudyDesign] = field(default_factory=list)
    feasibility_notes: List[str] = field(default_factory=list)
    ethical_considerations: List[str] = field(default_factory=list)
    confidence: str = "high"

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
# Keyword banks
# ===========================================================================

# PECO signal — explicit exposure / observational language
_EXPOSURE_KEYWORDS: List[str] = [
    "exposure to", "exposed to", "exposure",
    "risk factor", "risk factors",
    "environmental", "occupational",
    "smoking", "alcohol", "pollution", "radiation",
    "association between", "associated with", "linked to",
    "diet", "dietary",
]

# PICO signal — explicit intervention / trial language
_INTERVENTION_KEYWORDS: List[str] = [
    "randomized", "randomised", "rct",
    "treatment", "intervention", "therapy",
    "drug", "medication", "surgery", "procedure",
    "vaccine", "programme", "program",
    "trial", "compared to", "versus", "vs",
    "efficacy", "effectiveness",
]

# Study design scoring banks
_RCT_KEYWORDS: List[str] = [
    "randomized", "randomised", "rct", "trial", "placebo",
    "blinded", "double-blind", "single-blind",
    "efficacy", "effectiveness",
]

_COHORT_KEYWORDS: List[str] = [
    "cohort", "longitudinal", "prospective",
    "follow-up", "follow up",
    "incidence", "prognosis", "natural history",
]

_CASE_CONTROL_KEYWORDS: List[str] = [
    "case-control", "case control",
    "odds ratio", "aetiology", "etiology",
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
    """Lower-case, collapse whitespace, strip punctuation at boundaries."""
    return re.sub(r"\s+", " ", text.lower().strip())


def _score_keywords(text: str, keywords: List[str]) -> int:
    normalised = _normalise(text)
    return sum(1 for kw in keywords if kw in normalised)


def _make_task_id() -> str:
    return str(uuid.uuid4())


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_str(value: Any) -> str:
    """Safely convert a value to str; return '' for None."""
    if value is None:
        return ""
    return str(value)


# ---------------------------------------------------------------------------
# Field extraction helpers
# ---------------------------------------------------------------------------
# Constraints:
# - Return "" when no clear evidence exists (No-Invention Rule).
# - Do not absorb entire sentence into a single field.
# - Caps at a sensible max token width to avoid over-extraction.
# ---------------------------------------------------------------------------

_MAX_FIELD_TOKENS = 8   # rough cap on words per extracted field


def _cap_extraction(text: str) -> str:
    """
    Trim an extracted string to _MAX_FIELD_TOKENS words.
    If the result is a generic stop-word only, return "".
    """
    _GENERIC_STOPS = {"outcomes", "outcome", "results", "result", "effects",
                      "effect", "patients", "subjects", "participants",
                      "individuals", "people", "adults", "children"}
    words = text.split()
    trimmed = " ".join(words[:_MAX_FIELD_TOKENS]).strip().rstrip(",;.")
    if trimmed.lower() in _GENERIC_STOPS:
        return ""
    return trimmed


def _extract_population(question: str) -> str:
    """
    Extract the Population element from a research question.

    Looks for noun phrases following explicit population markers.
    Returns "" when no clear evidence is found.
    """
    patterns = [
        # "in adults with X" / "among patients with X" / "for children with X"
        r"(?:in|among|for)\s+((?:adults?|children|patients?|individuals?|people|subjects?)"
        r"(?:\s+with\s+[A-Za-z0-9 ,\-\(\)]+?)?)(?=\s+(?:who|receiving|treated|aged|,|\?|$))",
        # "patients with X"
        r"(patients?\s+with\s+[A-Za-z0-9 ,\-\(\)]+?)(?=\s+(?:who|receiving|treated|aged|,|\?|$))",
        # "adults with X"
        r"(adults?\s+with\s+[A-Za-z0-9 ,\-\(\)]+?)(?=\s+(?:who|receiving|treated|aged|,|\?|$))",
        # "children with X"
        r"(children?\s+with\s+[A-Za-z0-9 ,\-\(\)]+?)(?=\s+(?:who|receiving|treated|aged|,|\?|$))",
        # "individuals with X"
        r"(individuals?\s+with\s+[A-Za-z0-9 ,\-\(\)]+?)(?=\s+(?:who|receiving|,|\?|$))",
    ]
    for pattern in patterns:
        match = re.search(pattern, question, re.IGNORECASE)
        if match:
            extracted = match.group(1).strip().rstrip(",;.")
            capped = _cap_extraction(extracted)
            if capped:
                return capped
    return ""


def _extract_intervention(question: str) -> str:
    """
    Extract the Intervention element from a PICO question.

    Returns "" when no clear intervention evidence is found.
    """
    patterns = [
        # "effect of X on ..."
        r"(?:effect|efficacy|effectiveness)\s+of\s+([A-Za-z0-9 \-\(\)]+?)\s+(?:on|in|compared|versus|vs|\?)",
        # "X compared to Y" / "X versus Y"
        r"([A-Za-z0-9 \-\(\)]+?)\s+(?:versus|vs\.?|compared\s+(?:to|with))\s+",
        # "does X [verb]"
        r"does\s+([A-Za-z0-9 \-\(\)]+?)\s+(?:compared|versus|vs|reduce|improve|prevent|affect)",
        # "receiving / treated with / given X"
        r"(?:receiving|treated\s+with|given|taking)\s+([A-Za-z0-9 \-\(\)]+?)(?:\s+(?:compared|versus|vs|,|\?|$))",
    ]
    for pattern in patterns:
        match = re.search(pattern, question, re.IGNORECASE)
        if match:
            extracted = match.group(1).strip().rstrip(",;.")
            capped = _cap_extraction(extracted)
            if capped:
                return capped
    return ""


def _extract_comparator(question: str) -> str:
    """
    Extract the Comparator element.

    Returns "" when no comparator evidence is found.
    """
    patterns = [
        # "compared to/with X"
        r"compared\s+(?:to|with)\s+([A-Za-z0-9 \-\(\)]+?)(?=\s+(?:in|on|for|regarding|,|\?|$))",
        # "versus / vs X"
        r"(?:versus|vs\.?)\s+([A-Za-z0-9 \-\(\)]+?)(?=\s+(?:in|on|for|regarding|,|\?|$))",
        # named controls
        r"\b(placebo|standard\s+care|usual\s+care|no\s+treatment|control\s+group|sham)\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, question, re.IGNORECASE)
        if match:
            extracted = match.group(1).strip().rstrip(",;.")
            capped = _cap_extraction(extracted)
            if capped:
                return capped
    return ""


def _extract_outcome(question: str) -> str:
    """
    Extract the Outcome element.

    Returns "" when no outcome evidence is found.
    """
    patterns = [
        # "regarding X" / "in terms of X"
        r"(?:regarding|in\s+terms\s+of)\s+([A-Za-z0-9 \-\(\)]+?)(?=\s*[,\?]|$)",
        # "reduce / improve / prevent / affect X"
        r"(?:reduce|improve|prevent|affect|increase|decrease)\s+([A-Za-z0-9 \-\(\)]+?)(?=\s+(?:in|among|for|,|\?|$))",
        # "outcome: X" or "endpoint: X"
        r"(?:outcome|endpoint|measure)[s]?\s*[:\-]\s*([A-Za-z0-9 \-\(\)]+?)(?=\s*[,\?]|$)",
        # well-known clinical outcomes (named entities)
        r"\b(mortality|survival|recurrence|remission|HbA1c|blood\s+pressure|"
        r"quality\s+of\s+life|pain\s+score|hospitalisation|hospitalization|"
        r"relapse|morbidity|seizure|stroke|myocardial\s+infarction)\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, question, re.IGNORECASE)
        if match:
            extracted = match.group(1).strip().rstrip(",;.")
            capped = _cap_extraction(extracted)
            if capped:
                return capped
    return ""


def _extract_exposure(question: str) -> str:
    """
    Extract the Exposure element from a PECO question.

    Returns "" when no exposure evidence is found.
    """
    patterns = [
        # "exposure to X"
        r"(?:exposure\s+to|exposed\s+to)\s+([A-Za-z0-9 \-\(\)]+?)(?=\s+(?:and|in|among|on|,|\?|$))",
        # "association between X and ..."
        r"association\s+between\s+([A-Za-z0-9 \-\(\)]+?)\s+and\s+",
        # "effect/impact of X on ..."
        r"(?:effect|impact)\s+of\s+([A-Za-z0-9 \-\(\)]+?)\s+(?:on|with|in)",
        # named exposure concepts
        r"\b(smoking|tobacco|alcohol|diet|radiation|pollution|"
        r"occupational\s+exposure|asbestos|lead|noise)\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, question, re.IGNORECASE)
        if match:
            extracted = match.group(1).strip().rstrip(",;.")
            capped = _cap_extraction(extracted)
            if capped:
                return capped
    return ""


# ===========================================================================
# 1. infer_framework_type
# ===========================================================================

def infer_framework_type(question: str) -> FrameworkType:
    """
    Deterministically infer whether a research question calls for PICO or
    PECO structuring.

    Priority rules (in order):
    1. Empty / blank → UNKNOWN.
    2. Explicit exposure language score > intervention score → PECO.
    3. Explicit intervention / trial language score > exposure score → PICO.
    4. Scores equal and both > 0 → PICO (intervention is the safer default
       when evidence is genuinely ambiguous).
    5. Both scores = 0 → PICO (most clinical questions are interventional).

    No-Invention Rule: decision is based solely on the supplied text.
    """
    q = _safe_str(question)
    if not q.strip():
        return FrameworkType.UNKNOWN

    normalised = _normalise(q)
    exposure_score = sum(1 for kw in _EXPOSURE_KEYWORDS if kw in normalised)
    intervention_score = sum(1 for kw in _INTERVENTION_KEYWORDS if kw in normalised)

    if exposure_score > intervention_score:
        return FrameworkType.PECO
    # intervention_score >= exposure_score (including tie and both-zero) → PICO
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

    No-Invention Rule: no field value is fabricated.
    """
    if framework_type is None:
        if _safe_str(exposure).strip():
            framework_type = FrameworkType.PECO
        else:
            framework_type = FrameworkType.PICO

    if framework_type == FrameworkType.PECO:
        peco = PECOFramework(
            population=_safe_str(population),
            exposure=_safe_str(exposure),
            comparator=_safe_str(comparator),
            outcome=_safe_str(outcome),
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
            raw_question=_safe_str(raw_question),
            generated_question=generated_q,
            objectives=objectives,
        )

    pico = PICOFramework(
        population=_safe_str(population),
        intervention=_safe_str(intervention),
        comparator=_safe_str(comparator),
        outcome=_safe_str(outcome),
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
        raw_question=_safe_str(raw_question),
        generated_question=generated_q,
        objectives=objectives,
    )


# ===========================================================================
# 3. build_research_question
# ===========================================================================

def build_research_question(framework_result: ResearchFrameworkResult) -> str:
    """
    Generate a structured, neutral research question from a
    ResearchFrameworkResult.

    No-Invention Rule: assembled only from fields present in the result.
    """
    if framework_result.framework_type == FrameworkType.PECO and framework_result.peco:
        return build_research_question_from_peco(framework_result.peco)
    if framework_result.pico:
        return build_research_question_from_pico(framework_result.pico)
    return ""


def build_research_question_from_pico(pico: PICOFramework) -> str:
    """
    Assemble a neutral PICO research question.

    Template:
        "In [P], how does [I] compare with [C] regarding [O]?"
        "In [P], how does [I] affect [O]?"     (no comparator)
        "How does [I] compare with [C] regarding [O]?"  (no population)
        etc.

    No causal or effectiveness language is added beyond what is present
    in the supplied fields.
    """
    pop = pico.population.strip()
    intv = pico.intervention.strip()
    comp = pico.comparator.strip()
    out = pico.outcome.strip()

    if not any([pop, intv, out]):
        return ""

    parts: List[str] = []

    if pop:
        parts.append(f"In {pop}")

    if intv and comp:
        connector = f"how does {intv} compare with {comp}"
    elif intv:
        connector = f"how does {intv} perform"
    elif comp:
        connector = f"how does the intervention compare with {comp}"
    else:
        connector = ""

    if connector:
        parts.append(connector)

    if out:
        parts.append(f"regarding {out}")

    if not parts:
        return ""

    question = ", ".join(parts)
    if not question.endswith("?"):
        question += "?"
    return question


def build_research_question_from_peco(peco: PECOFramework) -> str:
    """
    Assemble a neutral PECO research question.

    Template:
        "In [P], is [E] associated with [O] compared with [C]?"
        "In [P], is [E] associated with [O]?"   (no comparator)

    No causal language is added beyond what is present in the fields.
    """
    pop = peco.population.strip()
    exp = peco.exposure.strip()
    comp = peco.comparator.strip()
    out = peco.outcome.strip()

    if not any([pop, exp, out]):
        return ""

    parts: List[str] = []

    if pop:
        parts.append(f"In {pop}")

    if exp and comp:
        parts.append(f"is {exp} associated with {out} compared with {comp}")
        # outcome already embedded — skip separate out clause
        out = ""
    elif exp:
        parts.append(f"is {exp} associated with")
    elif comp:
        parts.append(f"is the exposure associated with {out} compared with {comp}")
        out = ""

    if out and exp and not comp:
        parts.append(out)

    if not parts:
        return ""

    question = " ".join(parts).strip()
    if not question.endswith("?"):
        question += "?"
    return question


# ===========================================================================
# 4. validate_framework  (+ PICO / PECO validators)
# ===========================================================================

def validate_pico(pico: PICOFramework) -> ValidationResult:
    """
    Validate a PICOFramework.

    INVALID  : P, I, or O is missing.
    INCOMPLETE: all mandatory present but C is absent.
    VALID    : P, I, C, O all present.
    """
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

    if not pico.outcome.strip():
        errors.append("Outcome (O) is missing.")
    elif len(pico.outcome.strip()) < 3:
        warnings.append("Outcome description is very short; consider expanding.")

    if not pico.comparator.strip():
        warnings.append(
            "Comparator (C) is missing. "
            "Consider specifying a control condition (e.g., placebo, standard care)."
        )
        suggestions.append("Add a comparator to strengthen internal validity.")

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
    """
    Validate a PECOFramework.

    INVALID  : P, E, or O is missing.
    INCOMPLETE: mandatory present but C is absent.
    VALID    : P, E, C, O all present.
    """
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

    if not peco.outcome.strip():
        errors.append("Outcome (O) is missing.")
    elif len(peco.outcome.strip()) < 3:
        warnings.append("Outcome description is very short; consider expanding.")

    if not peco.comparator.strip():
        warnings.append(
            "Comparator (C) is missing. "
            "Consider specifying an unexposed / reference group."
        )
        suggestions.append("Add a comparator group (e.g., unexposed controls).")

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
    Generate a deterministic list of research objectives.

    No-Invention Rule: objectives reference ONLY fields that are
    non-empty in the supplied framework.  No concepts are introduced.
    """
    if framework_result.framework_type == FrameworkType.PECO and framework_result.peco:
        return generate_research_objectives_from_peco(framework_result.peco)
    if framework_result.pico:
        return generate_research_objectives_from_pico(framework_result.pico)
    return []


def generate_research_objectives_from_pico(pico: PICOFramework) -> List[str]:
    """
    Generate PICO objectives strictly from the supplied field values.

    Rules:
    - Each objective is generated only if all referenced fields are present.
    - No concepts (e.g. "efficacy", "safety") are added unless in the fields.
    - "incidence" / "prevalence" are never introduced — they are epidemiological
      concepts absent from PICO intervention frameworks.
    """
    objectives: List[str] = []
    pop = pico.population.strip()
    intv = pico.intervention.strip()
    comp = pico.comparator.strip()
    out = pico.outcome.strip()

    # Objective 1: primary comparison (requires I + O at minimum)
    if intv and out:
        pop_clause = f" in {pop}" if pop else ""
        comp_clause = f" with {comp}" if comp else ""
        objectives.append(
            f"To evaluate {intv}{comp_clause} in relation to {out}{pop_clause}."
        )

    # Objective 2: explicit comparison (requires I + C + O)
    if intv and comp and out:
        objectives.append(
            f"To compare {intv} and {comp} with respect to {out}."
        )

    # Objective 3: time-horizon objective (requires I + O + time_horizon)
    if intv and out and pico.time_horizon:
        objectives.append(
            f"To assess {out} following {intv} over {pico.time_horizon}."
        )

    # Fallback: at least one field present — minimal faithful objective
    if not objectives:
        elements = [x for x in [intv, out, pop] if x]
        if elements:
            objectives.append("To investigate " + ", ".join(elements) + ".")

    return objectives


def generate_research_objectives_from_peco(peco: PECOFramework) -> List[str]:
    """
    Generate PECO objectives strictly from the supplied field values.

    Rules:
    - "incidence" / "prevalence" are NOT introduced unless the outcome
      field itself contains those terms.
    - "with and without exposure" is NOT assumed — only what is in the data.
    - Each objective requires all referenced fields to be non-empty.
    """
    objectives: List[str] = []
    pop = peco.population.strip()
    exp = peco.exposure.strip()
    comp = peco.comparator.strip()
    out = peco.outcome.strip()

    # Detect whether incidence/prevalence language was explicitly supplied
    out_lower = out.lower()
    has_incidence = "incidence" in out_lower
    has_prevalence = "prevalence" in out_lower

    # Objective 1: association (requires E + O at minimum)
    if exp and out:
        pop_clause = f" in {pop}" if pop else ""
        objectives.append(
            f"To examine the association between {exp} and {out}{pop_clause}."
        )

    # Objective 2: comparison across groups (requires E + C + O)
    if exp and comp and out:
        objectives.append(
            f"To compare {out} between {exp} and {comp} groups."
        )

    # Objective 3: incidence objective — only if "incidence" is in outcome
    if has_incidence and pop and exp:
        objectives.append(
            f"To estimate the incidence of {out} in relation to {exp} in {pop}."
        )

    # Objective 4: prevalence objective — only if "prevalence" is in outcome
    if has_prevalence and pop:
        objectives.append(
            f"To estimate the prevalence of {out} in {pop}."
        )

    # Objective 5: time-horizon objective (requires E + O + time_horizon)
    if exp and out and peco.time_horizon:
        objectives.append(
            f"To assess the relationship between {exp} and {out} "
            f"over {peco.time_horizon}."
        )

    # Fallback: at least one field present
    if not objectives:
        elements = [x for x in [exp, out, pop] if x]
        if elements:
            objectives.append("To investigate " + ", ".join(elements) + ".")

    return objectives


# ===========================================================================
# 6. recommend_study_design
# ===========================================================================

def recommend_study_design(
    framework: ResearchFrameworkResult,
) -> StudyDesignRecommendation:
    """
    Recommend a study design from a ResearchFrameworkResult.

    No-Invention Rule: recommendation derived solely from supplied content.
    """
    if framework.framework_type == FrameworkType.PECO and framework.peco:
        return recommend_study_design_from_peco(framework.peco)
    if framework.pico:
        return recommend_study_design_from_pico(framework.pico)
    return StudyDesignRecommendation(
        recommended_design=StudyDesign.UNKNOWN,
        rationale=(
            "Insufficient framework data to recommend a study design. "
            "Please supply PICO or PECO fields."
        ),
        confidence="low",
    )


def recommend_study_design_from_pico(pico: PICOFramework) -> StudyDesignRecommendation:
    """
    Recommend a study design deterministically from PICO fields.

    Scoring: each design type accumulates points for matching keywords
    found in the combined PICO text.

    No-Invention Rule:
    - When scores are all 0, recommend UNKNOWN (not RCT by default).
    - Only recommend a design when keyword evidence supports it.
    """
    combined = " ".join(filter(None, [
        pico.population, pico.intervention, pico.comparator, pico.outcome,
        pico.time_horizon or "", pico.setting or "",
    ]))

    hierarchy = [
        StudyDesign.RCT,
        StudyDesign.COHORT,
        StudyDesign.CASE_CONTROL,
        StudyDesign.CROSS_SECTIONAL,
        StudyDesign.SYSTEMATIC_REVIEW,
    ]
    keyword_map: Dict[StudyDesign, List[str]] = {
        StudyDesign.RCT: _RCT_KEYWORDS,
        StudyDesign.COHORT: _COHORT_KEYWORDS,
        StudyDesign.CASE_CONTROL: _CASE_CONTROL_KEYWORDS,
        StudyDesign.CROSS_SECTIONAL: _CROSS_SECTIONAL_KEYWORDS,
        StudyDesign.SYSTEMATIC_REVIEW: _SR_KEYWORDS,
    }
    scores = {d: _score_keywords(combined, keyword_map[d]) for d in hierarchy}
    max_score = max(scores.values())

    # No-Invention Rule: if no keywords matched, return UNKNOWN
    if max_score == 0:
        return StudyDesignRecommendation(
            recommended_design=StudyDesign.UNKNOWN,
            rationale=(
                "No study-design keywords were identified in the supplied PICO "
                "fields. A design cannot be recommended without additional context."
            ),
            alternatives=[],
            feasibility_notes=[],
            ethical_considerations=[],
            confidence="low",
        )

    best = max(hierarchy, key=lambda d: (scores[d], -hierarchy.index(d)))
    confidence = "high" if max_score >= 2 else "medium"
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
    Recommend a study design deterministically from PECO fields.

    No-Invention Rule:
    - When scores are all 0, recommend UNKNOWN (not Cohort by default).
    - Only recommend a design when keyword evidence supports it.
    """
    combined = " ".join(filter(None, [
        peco.population, peco.exposure, peco.comparator, peco.outcome,
        peco.time_horizon or "", peco.setting or "",
    ]))

    hierarchy = [
        StudyDesign.COHORT,
        StudyDesign.CASE_CONTROL,
        StudyDesign.CROSS_SECTIONAL,
        StudyDesign.SYSTEMATIC_REVIEW,
        StudyDesign.RCT,
    ]
    keyword_map: Dict[StudyDesign, List[str]] = {
        StudyDesign.COHORT: _COHORT_KEYWORDS,
        StudyDesign.CASE_CONTROL: _CASE_CONTROL_KEYWORDS,
        StudyDesign.CROSS_SECTIONAL: _CROSS_SECTIONAL_KEYWORDS,
        StudyDesign.SYSTEMATIC_REVIEW: _SR_KEYWORDS,
        StudyDesign.RCT: _RCT_KEYWORDS,
    }
    scores = {d: _score_keywords(combined, keyword_map[d]) for d in hierarchy}
    max_score = max(scores.values())

    # No-Invention Rule: if no keywords matched, return UNKNOWN
    if max_score == 0:
        return StudyDesignRecommendation(
            recommended_design=StudyDesign.UNKNOWN,
            rationale=(
                "No study-design keywords were identified in the supplied PECO "
                "fields. A design cannot be recommended without additional context."
            ),
            alternatives=[],
            feasibility_notes=[],
            ethical_considerations=[],
            confidence="low",
        )

    best = max(hierarchy, key=lambda d: (scores[d], -hierarchy.index(d)))
    confidence = "high" if max_score >= 2 else "medium"
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
# Rationale builders — conservative, field-grounded language only
# ---------------------------------------------------------------------------

def _build_pico_rationale(design: StudyDesign, pico: PICOFramework) -> str:
    """
    Build a rationale string that references only the supplied PICO fields.

    No causal claims, feasibility assumptions, or rarity assumptions are
    introduced unless the field data supports them.
    """
    pop = pico.population or "the study population"
    intv = pico.intervention or "the intervention"
    comp = pico.comparator or "the comparator"
    out = pico.outcome or "the outcome"
    has_comp = bool(pico.comparator.strip())

    rationales: Dict[StudyDesign, str] = {
        StudyDesign.RCT: (
            f"Keywords in the supplied PICO fields (e.g. {intv}) are consistent "
            f"with a Randomised Controlled Trial design to evaluate {out} in {pop}."
            + (f" The presence of a comparator ({comp}) supports a two-arm design." if has_comp else "")
        ),
        StudyDesign.COHORT: (
            f"Keywords in the PICO fields suggest a longitudinal or follow-up "
            f"approach. A Cohort Study may be appropriate to observe {out} in "
            f"{pop} over time."
        ),
        StudyDesign.CASE_CONTROL: (
            f"Keywords in the PICO fields are consistent with a Case-Control "
            f"design to investigate the association between {intv} and {out} "
            f"in {pop}."
        ),
        StudyDesign.CROSS_SECTIONAL: (
            f"Keywords in the PICO fields suggest measurement at a single point "
            f"in time. A Cross-Sectional Study may be appropriate to assess "
            f"{out} in {pop}."
        ),
        StudyDesign.SYSTEMATIC_REVIEW: (
            f"Keywords in the PICO fields suggest an evidence-synthesis approach. "
            f"A Systematic Review may be appropriate to summarise existing "
            f"evidence on {intv} and {out} in {pop}."
        ),
    }
    return rationales.get(design, "No specific rationale available.")


def _build_peco_rationale(design: StudyDesign, peco: PECOFramework) -> str:
    """
    Build a rationale string that references only the supplied PECO fields.

    No feasibility or rarity assumptions are introduced.
    """
    pop = peco.population or "the study population"
    exp = peco.exposure or "the exposure"
    out = peco.outcome or "the outcome"
    has_comp = bool(peco.comparator.strip())
    comp = peco.comparator or "a reference group"

    rationales: Dict[StudyDesign, str] = {
        StudyDesign.COHORT: (
            f"Keywords in the PECO fields are consistent with a longitudinal "
            f"design. A Cohort Study may be appropriate to assess {out} in "
            f"{pop} in relation to {exp}."
            + (f" Comparison with {comp} is indicated." if has_comp else "")
        ),
        StudyDesign.CASE_CONTROL: (
            f"Keywords in the PECO fields are consistent with a Case-Control "
            f"design to investigate the association between {exp} and {out} "
            f"in {pop}."
        ),
        StudyDesign.CROSS_SECTIONAL: (
            f"Keywords in the PECO fields suggest a point-in-time measurement. "
            f"A Cross-Sectional Study may be appropriate to assess {out} in "
            f"{pop} in relation to {exp}."
        ),
        StudyDesign.SYSTEMATIC_REVIEW: (
            f"Keywords in the PECO fields suggest an evidence-synthesis approach. "
            f"A Systematic Review may be appropriate to summarise existing "
            f"evidence on {exp} and {out} in {pop}."
        ),
        StudyDesign.RCT: (
            f"Keywords in the PECO fields include trial-related terms. An RCT "
            f"may be considered if {exp} can be allocated in {pop} to evaluate "
            f"its effect on {out}."
        ),
    }
    return rationales.get(design, "No specific rationale available.")


def _build_feasibility_notes(design: StudyDesign) -> List[str]:
    notes: Dict[StudyDesign, List[str]] = {
        StudyDesign.RCT: [
            "Requires ethical approval and participant informed consent.",
            "Sample size and funding requirements should be assessed.",
            "Blinding feasibility depends on the intervention type.",
        ],
        StudyDesign.COHORT: [
            "Follow-up duration should be defined based on the outcome of interest.",
            "Loss to follow-up should be planned for in the analysis.",
        ],
        StudyDesign.CASE_CONTROL: [
            "Historical exposure data quality must be assessed.",
            "Control selection methodology should be pre-specified.",
        ],
        StudyDesign.CROSS_SECTIONAL: [
            "Cannot establish temporal sequence between exposure and outcome.",
            "Suitable for descriptive or hypothesis-generating purposes.",
        ],
        StudyDesign.SYSTEMATIC_REVIEW: [
            "Quality of synthesis depends on the available primary studies.",
            "A comprehensive search strategy and PRISMA reporting are recommended.",
        ],
    }
    return notes.get(design, [])


def _build_ethical_considerations(design: StudyDesign) -> List[str]:
    considerations: Dict[StudyDesign, List[str]] = {
        StudyDesign.RCT: [
            "Equipoise must exist between treatment arms.",
            "Full informed consent is required for randomisation.",
        ],
        StudyDesign.COHORT: [
            "Data privacy for longitudinal records must be maintained.",
            "Participant burden should be minimised during follow-up.",
        ],
        StudyDesign.CASE_CONTROL: [
            "Appropriate control selection is required to minimise bias.",
            "Sensitivity around case identification and data linkage applies.",
        ],
        StudyDesign.CROSS_SECTIONAL: [
            "Survey anonymisation and voluntary participation must be ensured.",
        ],
        StudyDesign.SYSTEMATIC_REVIEW: [
            "Standard publication and reporting ethics apply.",
            "PRISMA guidelines are recommended.",
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

    Gate criteria (all must pass):
    - Framework type is not UNKNOWN.
    - Validation is not INVALID.
    - Population (P) is present.
    - Outcome (O) is present.
    - A research question string exists (generated or raw).

    Note: INCOMPLETE (missing comparator) is allowed through this gate.

    No-Invention Rule: decisions based solely on supplied data.
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

    # Population and Outcome checks
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
    State gate: determine whether a study design has been selected and
    the project is ready to advance to the LITERATURE_SEARCH phase.

    Gate criteria:
    - check_question_defined_ready must pass.
    - A StudyDesignRecommendation must be present.
    - recommended_design must not be UNKNOWN.
    - rationale must be non-empty.

    No-Invention Rule: decisions based solely on supplied data.
    """
    reasons: List[str] = []

    question_ok, question_reasons = check_question_defined_ready(framework_result)
    if not question_ok:
        reasons.extend(question_reasons)

    if framework_result.study_design is None:
        reasons.append("No study design recommendation has been generated.")
    else:
        if framework_result.study_design.recommended_design == StudyDesign.UNKNOWN:
            reasons.append(
                "Study design is UNKNOWN; a specific design must be selected "
                "before advancing."
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
    framework_result_or_project: Any,
    framework: Optional[Any] = None,
) -> List[FrameworkTask]:
    """
    Generate an ordered list of actionable FrameworkTasks.

    Supports two calling conventions (backward compatible):

    Convention A — single argument:
        generate_framework_tasks(framework_result: ResearchFrameworkResult)

    Convention B — two arguments (project, framework_result):
        generate_framework_tasks(project: ResearchProject,
                                 framework: ResearchFrameworkResult)

    No-Invention Rule: task descriptions reference only fields actually
    present or absent in the supplied data.
    """
    # ------------------------------------------------------------------
    # Resolve which argument is the ResearchFrameworkResult
    # ------------------------------------------------------------------
    if framework is not None:
        fw_result: ResearchFrameworkResult = framework
    else:
        fw_result = framework_result_or_project

    # Safety guard: if fw_result is not a ResearchFrameworkResult
    if not isinstance(fw_result, ResearchFrameworkResult):
        candidate = getattr(fw_result, "framework", None)
        if isinstance(candidate, ResearchFrameworkResult):
            fw_result = candidate
        else:
            return [FrameworkTask(
                task_id=_make_task_id(),
                title="Supply a research framework",
                description=(
                    "No ResearchFrameworkResult was provided. "
                    "Call build_framework() or infer_framework() first."
                ),
                phase="framework",
                status=TaskStatus.PENDING,
                priority=1,
            )]

    tasks: List[FrameworkTask] = []
    priority = 1
    ft = fw_result.framework_type

    # ------------------------------------------------------------------
    # Task: complete missing framework fields
    # ------------------------------------------------------------------
    missing_fields: List[str] = []

    if ft == FrameworkType.PECO and fw_result.peco:
        peco = fw_result.peco
        if not peco.population.strip():
            missing_fields.append("Population (P)")
        if not peco.exposure.strip():
            missing_fields.append("Exposure (E)")
        if not peco.comparator.strip():
            missing_fields.append("Comparator (C)")
        if not peco.outcome.strip():
            missing_fields.append("Outcome (O)")
    elif fw_result.pico:
        pico = fw_result.pico
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

    # ------------------------------------------------------------------
    # Task: resolve validation errors
    # ------------------------------------------------------------------
    if (
        fw_result.validation
        and fw_result.validation.status == ValidationStatus.INVALID
    ):
        tasks.append(FrameworkTask(
            task_id=_make_task_id(),
            title="Resolve framework validation errors",
            description=(
                "The framework has failed validation. Errors to resolve: "
                + "; ".join(fw_result.validation.errors) + "."
            ),
            phase="framework",
            status=TaskStatus.PENDING,
            priority=priority,
            metadata={"errors": fw_result.validation.errors},
        ))
        priority += 1

    # ------------------------------------------------------------------
    # Task: review validation warnings
    # ------------------------------------------------------------------
    if (
        fw_result.validation
        and fw_result.validation.warnings
        and fw_result.validation.status != ValidationStatus.INVALID
    ):
        tasks.append(FrameworkTask(
            task_id=_make_task_id(),
            title="Review framework validation warnings",
            description=(
                "The framework has warnings that should be reviewed: "
                + "; ".join(fw_result.validation.warnings) + "."
            ),
            phase="framework",
            status=TaskStatus.PENDING,
            priority=priority,
            metadata={"warnings": fw_result.validation.warnings},
        ))
        priority += 1

    # ------------------------------------------------------------------
    # Task: generate research question
    # ------------------------------------------------------------------
    question_text = (
        fw_result.generated_question or fw_result.raw_question
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
        ))
        priority += 1

    # ------------------------------------------------------------------
    # Task: generate research objectives
    # ------------------------------------------------------------------
    if not fw_result.objectives:
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
        ))
        priority += 1

    # ------------------------------------------------------------------
    # Task: select study design
    # ------------------------------------------------------------------
    if fw_result.study_design is None:
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
        ))
        priority += 1
    elif fw_result.study_design.recommended_design == StudyDesign.UNKNOWN:
        tasks.append(FrameworkTask(
            task_id=_make_task_id(),
            title="Confirm study design selection",
            description=(
                "The study design is UNKNOWN because the framework fields do not "
                "contain sufficient study-design keywords. "
                "Review the framework or manually specify a design."
            ),
            phase="framework",
            status=TaskStatus.PENDING,
            priority=priority,
        ))
        priority += 1

    # ------------------------------------------------------------------
    # Task: advance to literature search (only when all gates pass)
    # ------------------------------------------------------------------
    design_ok, _ = check_design_selected_ready(fw_result)
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
# Top-level inference pipeline
# ===========================================================================

def infer_pico(question: str) -> PICOFramework:
    """Infer a PICOFramework from a free-text research question."""
    q = _safe_str(question)
    return PICOFramework(
        population=_extract_population(q),
        intervention=_extract_intervention(q),
        comparator=_extract_comparator(q),
        outcome=_extract_outcome(q),
        framework_type=FrameworkType.PICO,
    )


def infer_peco(question: str) -> PECOFramework:
    """Infer a PECOFramework from a free-text research question."""
    q = _safe_str(question)
    return PECOFramework(
        population=_extract_population(q),
        exposure=_extract_exposure(q),
        comparator=_extract_comparator(q),
        outcome=_extract_outcome(q),
        framework_type=FrameworkType.PECO,
    )


def infer_framework(question: str) -> ResearchFrameworkResult:
    """
    Top-level entry point: infer framework type and populate the
    appropriate PICO or PECO structure from a free-text question.
    """
    q = _safe_str(question)

    if not q.strip():
        return ResearchFrameworkResult(
            framework_type=FrameworkType.UNKNOWN,
            raw_question=q,
            validation=ValidationResult(
                status=ValidationStatus.INVALID,
                errors=["Research question is empty."],
            ),
        )

    framework_type = infer_framework_type(q)

    if framework_type == FrameworkType.PECO:
        peco = infer_peco(q)
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
            raw_question=q,
            generated_question=generated_q,
            objectives=objectives,
        )

    pico = infer_pico(q)
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
        raw_question=q,
        generated_question=generated_q,
        objectives=objectives,
    )


def process_research_question(question: str) -> ResearchFrameworkResult:
    """Full pipeline alias for infer_framework()."""
    return infer_framework(question)


def evaluate_framework_gate(
    framework_result: ResearchFrameworkResult,
) -> Tuple[bool, List[str]]:
    """Backward-compatible alias for check_question_defined_ready()."""
    return check_question_defined_ready(framework_result)


def evaluate_design_gate(
    recommendation: Optional[StudyDesignRecommendation],
) -> Tuple[bool, List[str]]:
    """
    Evaluate whether a standalone StudyDesignRecommendation satisfies
    the design gate (backward-compatible helper).
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
    """Return a human-readable summary of a ResearchFrameworkResult."""
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
    # Core public API (9 required Sprint 2 functions)
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
