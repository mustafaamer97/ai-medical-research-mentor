"""
core/research_engine.py
=======================
Sprint 2 — Deterministic Research Framework Engine

Provides:
- PICO / PECO inference and structuring
- Research framework validation
- Study design recommendation engine
- State gate evaluation (No-Invention Rule enforced throughout)

No-Invention Rule: All outputs are derived deterministically from user-supplied
inputs. The engine never fabricates populations, outcomes, exposures, or
comparators that were not present in the source data.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Internal imports — tolerant of partial Sprint 1/2 model availability
# ---------------------------------------------------------------------------
try:
    from core.models import ResearchProject, ProjectStatus
except ImportError:  # pragma: no cover
    ResearchProject = None  # type: ignore
    ProjectStatus = None  # type: ignore

try:
    from core.state import StateManager
except ImportError:  # pragma: no cover
    StateManager = None  # type: ignore


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
        """Return True only if all four core PICO elements are non-empty."""
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
    schema_version: str = "1.2.0"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "framework_type": self.framework_type.value,
            "raw_question": self.raw_question,
            "pico": self.pico.to_dict() if self.pico else None,
            "peco": self.peco.to_dict() if self.peco else None,
            "validation": self.validation.to_dict() if self.validation else None,
            "study_design": self.study_design.to_dict() if self.study_design else None,
        }


# ===========================================================================
# PICO / PECO Inference Engine
# ===========================================================================

# Keywords that signal an *exposure* question (→ PECO) rather than an
# intervention question (→ PICO).
_EXPOSURE_KEYWORDS: List[str] = [
    "exposure", "exposed", "risk factor", "risk factors",
    "environmental", "occupational", "diet", "dietary",
    "smoking", "alcohol", "pollution", "radiation",
    "association", "associated with", "linked to",
    "observational", "cohort", "case-control",
]

# Keywords that signal an *intervention* question (→ PICO).
_INTERVENTION_KEYWORDS: List[str] = [
    "treatment", "intervention", "therapy", "drug", "medication",
    "surgery", "procedure", "vaccine", "programme", "program",
    "trial", "rct", "randomized", "randomised",
    "compared to", "versus", "vs",
]


def _normalise(text: str) -> str:
    """Lower-case and collapse whitespace."""
    return re.sub(r"\s+", " ", text.lower().strip())


def infer_framework_type(question: str) -> FrameworkType:
    """
    Deterministically infer whether a research question is PICO or PECO.

    Rules (applied in order — first match wins):
    1. If question contains explicit PECO / exposure keywords → PECO.
    2. If question contains explicit PICO / intervention keywords → PICO.
    3. Default → PICO (most common clinical framework).

    No-Invention Rule: decision is based solely on supplied question text.
    """
    if not question or not question.strip():
        return FrameworkType.UNKNOWN

    normalised = _normalise(question)

    exposure_score = sum(1 for kw in _EXPOSURE_KEYWORDS if kw in normalised)
    intervention_score = sum(1 for kw in _INTERVENTION_KEYWORDS if kw in normalised)

    if exposure_score > intervention_score:
        return FrameworkType.PECO
    if intervention_score >= 0:  # default to PICO
        return FrameworkType.PICO
    return FrameworkType.UNKNOWN


# ---------------------------------------------------------------------------
# Field extraction helpers
# ---------------------------------------------------------------------------

def _extract_population(question: str) -> str:
    """
    Extract the Population element from a research question.

    Strategy: look for noun phrases following 'in', 'among', 'for',
    'patients with', 'adults with', 'children with'.
    Returns the matched phrase or empty string (No-Invention Rule).
    """
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
    """Extract Intervention element."""
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
    """Extract Comparator / Control element."""
    patterns = [
        r"(?:compared\s+(?:to|with)|versus|vs\.?)\s+([A-Za-z0-9 ,\-]+?)(?:\s+(?:in|on|for|reduce|improve|affect|,|\?))",
        r"(?:versus|vs\.?)\s+([A-Za-z0-9 ,\-]+?)(?:\s+(?:in|on|for|,|\?))",
        r"(?:placebo|standard\s+care|usual\s+care|no\s+treatment|control)",
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
    """Extract Outcome element."""
    patterns = [
        r"(?:on|affect|reduce|improve|prevent|increase|decrease)\s+([A-Za-z0-9 ,\-]+?)(?:\s+(?:in|among|for|,|\?|$))",
        r"(?:outcome|endpoint|measure)[s]?\s*[:\-]?\s*([A-Za-z0-9 ,\-]+?)(?:\s*[,\?]|$)",
        r"(?:mortality|survival|recurrence|remission|quality\s+of\s+life|pain|function|hospitalisation|hospitalization)",
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
    """Extract Exposure element (for PECO questions)."""
    patterns = [
        r"(?:exposure\s+to|exposed\s+to)\s+([A-Za-z0-9 ,\-]+?)(?:\s+(?:and|in|among|on|,|\?))",
        r"(?:effect|impact|association)\s+of\s+([A-Za-z0-9 ,\-]+?)\s+(?:on|with|in)",
        r"(?:smoking|alcohol|diet|radiation|pollution|occupational)\s+([A-Za-z0-9 ,\-]*)",
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
# Public API — Framework Inference
# ===========================================================================

def infer_pico(question: str) -> PICOFramework:
    """
    Deterministically infer a PICOFramework from a research question string.

    No-Invention Rule: only text present in *question* is used.
    Missing elements are returned as empty strings, never fabricated.
    """
    return PICOFramework(
        population=_extract_population(question),
        intervention=_extract_intervention(question),
        comparator=_extract_comparator(question),
        outcome=_extract_outcome(question),
        framework_type=FrameworkType.PICO,
    )


def infer_peco(question: str) -> PECOFramework:
    """
    Deterministically infer a PECOFramework from a research question string.

    No-Invention Rule: only text present in *question* is used.
    """
    return PECOFramework(
        population=_extract_population(question),
        exposure=_extract_exposure(question),
        comparator=_extract_comparator(question),
        outcome=_extract_outcome(question),
        framework_type=FrameworkType.PECO,
    )


def infer_framework(question: str) -> ResearchFrameworkResult:
    """
    Top-level entry point: infer framework type and populate the appropriate
    PICO or PECO structure from a free-text research question.

    Returns a ResearchFrameworkResult containing the inferred framework,
    a ValidationResult, and (where possible) a StudyDesignRecommendation.
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
        peco = infer_peco(question)
        validation = validate_peco(peco)
        design = recommend_study_design_from_peco(peco) if validation.is_valid else None
        return ResearchFrameworkResult(
            framework_type=framework_type,
            peco=peco,
            validation=validation,
            study_design=design,
            raw_question=question,
        )

    # Default: PICO
    pico = infer_pico(question)
    validation = validate_pico(pico)
    design = recommend_study_design_from_pico(pico) if validation.is_valid else None
    return ResearchFrameworkResult(
        framework_type=FrameworkType.PICO,
        pico=pico,
        validation=validation,
        study_design=design,
        raw_question=question,
    )


# ===========================================================================
# Validation Engine
# ===========================================================================

def validate_pico(pico: PICOFramework) -> ValidationResult:
    """
    Validate a PICOFramework.  Returns errors for missing mandatory fields
    and warnings for fields that appear unusually short.
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
    """
    Validate a PECOFramework.
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
# Study Design Recommendation Engine
# ===========================================================================

# ---------------------------------------------------------------------------
# Heuristic keyword sets used for deterministic design selection
# ---------------------------------------------------------------------------

_RCT_KEYWORDS = [
    "randomized", "randomised", "rct", "trial", "placebo",
    "blinded", "double-blind", "single-blind",
    "treatment", "intervention", "drug", "therapy", "vaccine",
    "efficacy", "effectiveness",
]

_COHORT_KEYWORDS = [
    "cohort", "longitudinal", "follow-up", "follow up", "prospective",
    "incidence", "prognosis", "natural history",
    "over time", "years", "months",
]

_CASE_CONTROL_KEYWORDS = [
    "case-control", "case control", "odds ratio", "risk factor",
    "aetiology", "etiology", "cause", "causes", "rare disease",
]

_CROSS_SECTIONAL_KEYWORDS = [
    "prevalence", "cross-sectional", "cross sectional",
    "survey", "point in time", "snapshot",
    "burden", "frequency",
]

_SR_KEYWORDS = [
    "systematic review", "meta-analysis", "meta analysis",
    "evidence synthesis", "pooled", "literature review",
    "existing evidence", "review of",
]


def _score_keywords(text: str, keywords: List[str]) -> int:
    normalised = _normalise(text)
    return sum(1 for kw in keywords if kw in normalised)


def recommend_study_design_from_pico(pico: PICOFramework) -> StudyDesignRecommendation:
    """
    Recommend a study design deterministically from PICO elements.

    Decision logic (deterministic scoring — no AI invention):
    1. Combine all PICO text.
    2. Score against keyword sets for each design type.
    3. Select highest scorer; apply tie-breaking hierarchy:
       RCT > Cohort > Case-Control > Cross-Sectional > Systematic Review.
    4. Provide rationale and alternatives from actual PICO content.
    """
    combined = " ".join([
        pico.population, pico.intervention, pico.comparator, pico.outcome,
        pico.time_horizon or "", pico.setting or "",
    ])

    scores = {
        StudyDesign.RCT: _score_keywords(combined, _RCT_KEYWORDS),
        StudyDesign.COHORT: _score_keywords(combined, _COHORT_KEYWORDS),
        StudyDesign.CASE_CONTROL: _score_keywords(combined, _CASE_CONTROL_KEYWORDS),
        StudyDesign.CROSS_SECTIONAL: _score_keywords(combined, _CROSS_SECTIONAL_KEYWORDS),
        StudyDesign.SYSTEMATIC_REVIEW: _score_keywords(combined, _SR_KEYWORDS),
    }

    # Hierarchy for tie-breaking (index = priority, lower = preferred)
    hierarchy = [
        StudyDesign.RCT,
        StudyDesign.COHORT,
        StudyDesign.CASE_CONTROL,
        StudyDesign.CROSS_SECTIONAL,
        StudyDesign.SYSTEMATIC_REVIEW,
    ]

    best_design = max(hierarchy, key=lambda d: (scores[d], -hierarchy.index(d)))

    if scores[best_design] == 0:
        # No keywords matched — recommend RCT for intervention PICO by default
        best_design = StudyDesign.RCT
        confidence = "low"
    else:
        confidence = "high" if scores[best_design] >= 2 else "medium"

    alternatives = [d for d in hierarchy if d != best_design and scores[d] > 0]

    rationale = _build_pico_rationale(best_design, pico)
    feasibility = _build_feasibility_notes(best_design)
    ethical = _build_ethical_considerations(best_design)

    return StudyDesignRecommendation(
        recommended_design=best_design,
        rationale=rationale,
        alternatives=alternatives,
        feasibility_notes=feasibility,
        ethical_considerations=ethical,
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

    scores = {
        StudyDesign.COHORT: _score_keywords(combined, _COHORT_KEYWORDS),
        StudyDesign.CASE_CONTROL: _score_keywords(combined, _CASE_CONTROL_KEYWORDS),
        StudyDesign.CROSS_SECTIONAL: _score_keywords(combined, _CROSS_SECTIONAL_KEYWORDS),
        StudyDesign.SYSTEMATIC_REVIEW: _score_keywords(combined, _SR_KEYWORDS),
        StudyDesign.RCT: _score_keywords(combined, _RCT_KEYWORDS),
    }

    hierarchy = [
        StudyDesign.COHORT,
        StudyDesign.CASE_CONTROL,
        StudyDesign.CROSS_SECTIONAL,
        StudyDesign.SYSTEMATIC_REVIEW,
        StudyDesign.RCT,
    ]

    best_design = max(hierarchy, key=lambda d: (scores[d], -hierarchy.index(d)))

    if scores[best_design] == 0:
        best_design = StudyDesign.COHORT
        confidence = "low"
    else:
        confidence = "high" if scores[best_design] >= 2 else "medium"

    alternatives = [d for d in hierarchy if d != best_design and scores[d] > 0]

    rationale = _build_peco_rationale(best_design, peco)
    feasibility = _build_feasibility_notes(best_design)
    ethical = _build_ethical_considerations(best_design)

    return StudyDesignRecommendation(
        recommended_design=best_design,
        rationale=rationale,
        alternatives=alternatives,
        feasibility_notes=feasibility,
        ethical_considerations=ethical,
        confidence=confidence,
    )


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
    notes = {
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
    considerations = {
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
# State Gate Evaluation
# ===========================================================================

def evaluate_framework_gate(framework_result: ResearchFrameworkResult) -> Tuple[bool, List[str]]:
    """
    Evaluate whether a ResearchFrameworkResult meets the gate criteria
    required to advance to the next research phase.

    Returns:
        (passed: bool, reasons: List[str])

    Gate criteria:
    - Framework type must not be UNKNOWN.
    - Validation status must be VALID or INCOMPLETE (not INVALID).
    - At least Population and Outcome must be non-empty.

    No-Invention Rule: gate decisions are based solely on the content
    of framework_result; nothing is assumed or fabricated.
    """
    reasons: List[str] = []

    if framework_result.framework_type == FrameworkType.UNKNOWN:
        reasons.append("Framework type could not be determined from the research question.")
        return False, reasons

    if framework_result.validation is None:
        reasons.append("Validation has not been performed.")
        return False, reasons

    if framework_result.validation.status == ValidationStatus.INVALID:
        reasons.append("Framework validation failed.")
        reasons.extend(framework_result.validation.errors)
        return False, reasons

    # Check minimum field population
    if framework_result.framework_type == FrameworkType.PECO and framework_result.peco:
        if not framework_result.peco.population.strip():
            reasons.append("Population is required to advance.")
            return False, reasons
        if not framework_result.peco.outcome.strip():
            reasons.append("Outcome is required to advance.")
            return False, reasons
    elif framework_result.pico:
        if not framework_result.pico.population.strip():
            reasons.append("Population is required to advance.")
            return False, reasons
        if not framework_result.pico.outcome.strip():
            reasons.append("Outcome is required to advance.")
            return False, reasons
    else:
        reasons.append("No PICO or PECO framework data present.")
        return False, reasons

    return True, reasons


def evaluate_design_gate(recommendation: Optional[StudyDesignRecommendation]) -> Tuple[bool, List[str]]:
    """
    Evaluate whether a StudyDesignRecommendation meets the gate criteria
    required to advance to literature search phase.

    Returns:
        (passed: bool, reasons: List[str])
    """
    reasons: List[str] = []

    if recommendation is None:
        reasons.append("No study design recommendation has been generated.")
        return False, reasons

    if recommendation.recommended_design == StudyDesign.UNKNOWN:
        reasons.append("Study design could not be determined.")
        return False, reasons

    if not recommendation.rationale.strip():
        reasons.append("Study design rationale is missing.")
        return False, reasons

    return True, reasons


# ===========================================================================
# Convenience / Integration Functions
# ===========================================================================

def process_research_question(question: str) -> ResearchFrameworkResult:
    """
    Full pipeline: infer framework → validate → recommend design.

    This is the primary integration entry point for external callers
    (UI, task engine, persistence layer).

    No-Invention Rule: all outputs derive from *question* only.
    """
    return infer_framework(question)


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

    if result.validation:
        lines.append(f"Validation: {result.validation.status.value}")
        for err in result.validation.errors:
            lines.append(f"  ERROR   : {err}")
        for warn in result.validation.warnings:
            lines.append(f"  WARNING : {warn}")

    if result.study_design:
        lines.append(f"Recommended Design: {result.study_design.recommended_design.value}")
        lines.append(f"  Rationale: {result.study_design.rationale}")

    return "\n".join(lines)
