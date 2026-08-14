"""
core/literature_engine.py

Sprint 3 Phase 1 — Deterministic Literature Search Strategy Engine.

Transforms a validated ResearchFramework into a structured search strategy.

NO-INVENTION RULE (strictly enforced throughout this module):
- No synonyms are generated.
- No MeSH terms are added.
- No medical concepts are invented.
- No citations, papers, authors, or abstracts are fabricated.
- Only researcher-provided text from ResearchFramework fields is used.
- Missing fields are reported, not guessed or filled.
- Boolean query is only produced when all required elements are present.

LLM-ready architecture:
An LLM enhancement layer can be added in a future sprint above this module
without modifying this module's public API.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from core.models import (
    LiteratureSearchStrategy,
    ResearchFramework,
    ResearchProject,
    ResearchTask,
    TaskPriority,
    TaskStatus,
)


# ──────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────

def build_search_strategy(project: ResearchProject) -> LiteratureSearchStrategy:
    """
    Builds a LiteratureSearchStrategy from a ResearchProject.

    Uses project.research_framework when present.
    Falls back to direct project model fields when framework is absent.
    Never invents terms, synonyms, or medical concepts.
    Missing components are reported in warnings and missing_components.
    """
    if project.research_framework is not None:
        return _build_strategy_from_framework(project, project.research_framework)
    return _build_strategy_without_framework(project)


def extract_search_terms(framework: ResearchFramework) -> Dict[str, List[str]]:
    """
    Extracts raw search term lists from a ResearchFramework.

    Returns a dict with keys:
        population_terms, intervention_terms, exposure_terms,
        comparator_terms, outcome_terms

    Terms are split from the framework field text only.
    No synonyms or external concepts are added.
    """
    return {
        "population_terms": _tokenize(framework.population),
        "intervention_terms": (
            _tokenize(framework.intervention)
            if framework.framework_type == "PICO"
            else []
        ),
        "exposure_terms": (
            _tokenize(framework.exposure)
            if framework.framework_type == "PECO"
            else []
        ),
        "comparator_terms": _tokenize(framework.comparator),
        "outcome_terms": _tokenize(framework.outcome),
    }


def build_boolean_query(framework: ResearchFramework) -> Optional[str]:
    """
    Builds a structured Boolean AND query from available framework elements.

    Format:
        ("population") AND ("intervention or exposure") AND ("outcome")
        AND ("comparator")  — only when comparator is present

    Returns None if required elements (population, primary IE, outcome)
    are missing. Never invents terms to fill gaps.
    """
    population = framework.population
    outcome = framework.outcome
    ie = (
        framework.intervention
        if framework.framework_type == "PICO"
        else framework.exposure
    )

    if not population or not ie or not outcome:
        return None

    parts: List[str] = [
        f'("{population.strip()}")',
        f'("{ie.strip()}")',
        f'("{outcome.strip()}")',
    ]

    if framework.comparator:
        parts.append(f'("{framework.comparator.strip()}")')

    return "\nAND\n".join(parts)


def validate_search_strategy(
    strategy: LiteratureSearchStrategy,
) -> Tuple[bool, List[str]]:
    """
    Validates a LiteratureSearchStrategy for readiness.

    Returns (is_valid: bool, issues: List[str]).

    A strategy is valid when:
    - population_terms is not empty
    - At least one of intervention_terms or exposure_terms is not empty
    - outcome_terms is not empty
    - boolean_query is not None
    """
    issues: List[str] = []

    if not strategy.population_terms:
        issues.append("Population terms are missing.")

    has_ie = bool(strategy.intervention_terms or strategy.exposure_terms)
    if not has_ie:
        if strategy.framework_type == "PICO":
            issues.append("Intervention terms are missing.")
        else:
            issues.append("Exposure terms are missing.")

    if not strategy.outcome_terms:
        issues.append("Outcome terms are missing.")

    if strategy.boolean_query is None:
        issues.append(
            "Boolean query could not be generated due to missing required components."
        )

    return len(issues) == 0, issues


def generate_literature_tasks(project: ResearchProject) -> List[ResearchTask]:
    """
    Generates targeted ResearchTasks for the literature search phase.

    Uses the existing ResearchTask model and architecture.
    Checks existing task titles to prevent duplicates across repeated calls.
    Does not invent content.
    Returns only tasks not already present in project.tasks.
    """
    task_definitions: List[Tuple[str, str, str, TaskPriority]] = [
        (
            "Build literature search strategy",
            "Use the PICO/PECO framework to construct a structured Boolean search "
            "strategy identifying all key search terms from your research framework.",
            "A structured search strategy ensures comprehensive, reproducible "
            "literature retrieval.",
            TaskPriority.CRITICAL,
        ),
        (
            "Review and refine search strategy",
            "Review the generated search strategy for accuracy, completeness, and "
            "relevance before running the search. Consult with a librarian or "
            "information specialist if needed.",
            "Expert review of the search strategy reduces the risk of missing key evidence.",
            TaskPriority.HIGH,
        ),
        (
            "Run literature search",
            "Execute the search strategy in relevant databases (e.g., PubMed, Embase, "
            "Cochrane Library). Document search dates and result counts.",
            "Running a systematic literature search is the foundation of "
            "evidence-based research.",
            TaskPriority.CRITICAL,
        ),
        (
            "Deduplicate retrieved records",
            "Remove duplicate records retrieved across multiple databases before "
            "proceeding to title and abstract screening.",
            "Deduplication prevents double-counting and reduces screening workload.",
            TaskPriority.HIGH,
        ),
        (
            "Screen titles and abstracts",
            "Apply the inclusion and exclusion criteria to screen retrieved records "
            "at the title and abstract level. Document reasons for exclusion.",
            "Title and abstract screening is required to identify studies eligible "
            "for full-text review.",
            TaskPriority.CRITICAL,
        ),
    ]

    existing_titles = {t.title for t in project.tasks}
    new_tasks: List[ResearchTask] = []

    for title, description, why, priority in task_definitions:
        if title in existing_titles:
            continue
        task = ResearchTask(
            title=title,
            description=description,
            why=why,
            priority=priority,
            dependencies=[],
        )
        new_tasks.append(task)
        existing_titles.add(title)

    return new_tasks


# ──────────────────────────────────────────────
# Private helpers
# ──────────────────────────────────────────────

def _build_strategy_from_framework(
    project: ResearchProject,
    framework: ResearchFramework,
) -> LiteratureSearchStrategy:
    """Builds strategy from an explicit ResearchFramework."""
    terms = extract_search_terms(framework)
    boolean_query = build_boolean_query(framework)

    missing_components: List[str] = []
    warnings: List[str] = []

    if not framework.population:
        missing_components.append("population")
        warnings.append(
            "Population is not defined. "
            "Search strategy cannot be completed without a population."
        )

    if framework.framework_type == "PICO" and not framework.intervention:
        missing_components.append("intervention")
        warnings.append(
            "Intervention is not defined. "
            "PICO search strategy requires an intervention."
        )

    if framework.framework_type == "PECO" and not framework.exposure:
        missing_components.append("exposure")
        warnings.append(
            "Exposure is not defined. "
            "PECO search strategy requires an exposure."
        )

    if not framework.outcome:
        missing_components.append("outcome")
        warnings.append(
            "Primary outcome is not defined. "
            "Search strategy cannot be completed without an outcome."
        )

    if not framework.comparator:
        warnings.append(
            "Comparator is not defined. "
            "The search strategy will proceed without a comparator term. "
            "Consider adding a comparator to narrow search results."
        )

    if not framework.time_frame:
        warnings.append(
            "Time frame is not specified. "
            "Consider adding a time frame to improve search precision."
        )

    ie_present = bool(
        framework.intervention
        if framework.framework_type == "PICO"
        else framework.exposure
    )
    ready_for_search = (
        bool(framework.population)
        and ie_present
        and bool(framework.outcome)
    )

    return LiteratureSearchStrategy(
        framework_type=framework.framework_type,
        population_terms=terms["population_terms"],
        intervention_terms=terms["intervention_terms"],
        exposure_terms=terms["exposure_terms"],
        comparator_terms=terms["comparator_terms"],
        outcome_terms=terms["outcome_terms"],
        boolean_query=boolean_query,
        warnings=warnings,
        missing_components=missing_components,
        ready_for_search=ready_for_search,
    )


def _build_strategy_without_framework(
    project: ResearchProject,
) -> LiteratureSearchStrategy:
    """
    Graceful degradation when no ResearchFramework exists.
    Uses direct project model fields.
    Reports missing components — does not invent content.
    """
    warnings: List[str] = [
        "No research framework (PICO/PECO) has been built yet. "
        "Build the framework first to generate a complete search strategy."
    ]
    missing_components: List[str] = []

    population_terms: List[str] = []
    if project.population:
        population_terms = _tokenize(project.population.description)
    else:
        missing_components.append("population")

    intervention_terms: List[str] = []
    exposure_terms: List[str] = []
    framework_type: str = "PICO"

    if project.intervention:
        intervention_terms = _tokenize(project.intervention.description)
        framework_type = "PICO"
    elif project.exposure:
        exposure_terms = _tokenize(project.exposure.description)
        framework_type = "PECO"
    else:
        missing_components.append("intervention or exposure")
        warnings.append(
            "Neither intervention nor exposure is defined. "
            "Search strategy cannot be completed."
        )

    outcome_terms: List[str] = []
    if project.primary_outcome:
        outcome_terms = _tokenize(project.primary_outcome.description)
    else:
        missing_components.append("outcome")
        warnings.append(
            "Primary outcome is not defined. "
            "Search strategy cannot be completed without an outcome."
        )

    comparator_terms: List[str] = []
    if project.comparator:
        comparator_terms = _tokenize(project.comparator.description)

    boolean_query: Optional[str] = None
    pop = project.population.description if project.population else None
    ie = (
        project.intervention.description
        if project.intervention
        else (
            project.exposure.description
            if project.exposure
            else None
        )
    )
    out = project.primary_outcome.description if project.primary_outcome else None

    if pop and ie and out:
        parts = [f'("{pop}")', f'("{ie}")', f'("{out}")']
        if project.comparator:
            parts.append(f'("{project.comparator.description}")')
        boolean_query = "\nAND\n".join(parts)

    ready_for_search = bool(pop and ie and out)

    return LiteratureSearchStrategy(
        framework_type=framework_type,
        population_terms=population_terms,
        intervention_terms=intervention_terms,
        exposure_terms=exposure_terms,
        comparator_terms=comparator_terms,
        outcome_terms=outcome_terms,
        boolean_query=boolean_query,
        warnings=warnings,
        missing_components=missing_components,
        ready_for_search=ready_for_search,
    )


def _tokenize(text: Optional[str]) -> List[str]:
    """
    Splits researcher-provided text into a list of meaningful tokens.

    Rules:
    - Strips whitespace
    - Returns the full phrase as primary item
    - Also splits on semicolons or slashes for multi-concept fields
    - Never adds external content
    - Returns empty list for None or empty input

    This function never invents terms. Output is a direct transformation
    of researcher-provided input only.
    """
    if not text or not text.strip():
        return []

    text = text.strip()

    parts = [p.strip() for p in text.replace(";", "/").split("/") if p.strip()]

    seen: set = set()
    result: List[str] = []
    for p in parts:
        if p.lower() not in seen:
            seen.add(p.lower())
            result.append(p)

    return result if result else [text]
