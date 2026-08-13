"""
tests/test_literature_engine.py

Sprint 3 Phase 1 — Literature Engine tests.

Covers:
1.  PICO strategy generation
2.  PECO strategy generation
3.  Boolean query generation
4.  Missing population
5.  Missing outcome
6.  Missing intervention
7.  Missing exposure
8.  No-invention rule
9.  Empty framework
10. Strategy validation
11. Serialization roundtrip
12. Backward compatibility
13. Task generation
14. Task deduplication
15. LiteratureRecord validation
16. ScreeningDecision validation
17. Repeated strategy generation
18. Existing Sprint 1/2 behavior unchanged
"""
from __future__ import annotations

import json

import pytest

from core.models import (
    Comparator,
    Exposure,
    Intervention,
    LiteratureRecord,
    LiteratureSearchStrategy,
    Outcome,
    Population,
    ResearchFramework,
    ResearchProject,
    ResearchState,
    ScreeningDecision,
    ScreeningDecisionEnum,
    StudyDesign,
    StudyDesignType,
    TaskStatus,
)
from core.literature_engine import (
    build_boolean_query,
    build_search_strategy,
    extract_search_terms,
    generate_literature_tasks,
    validate_search_strategy,
)


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

def _project(
    title: str = "Literature Test Project",
    idea: str = "Testing the literature engine with this research idea",
) -> ResearchProject:
    return ResearchProject(title=title, idea=idea)


def _pico_project() -> ResearchProject:
    p = _project()
    p.population = Population(description="Adults with type 2 diabetes aged 18-75")
    p.intervention = Intervention(description="Metformin 1000mg twice daily")
    p.comparator = Comparator(description="Placebo")
    p.primary_outcome = Outcome(
        name="Cardiovascular mortality",
        description="Death from cardiovascular causes at 5 years",
        is_primary=True,
    )
    p.research_framework = ResearchFramework(
        framework_type="PICO",
        population="Adults with type 2 diabetes aged 18-75",
        intervention="Metformin 1000mg twice daily",
        comparator="Placebo",
        outcome="Death from cardiovascular causes at 5 years",
    )
    return p


def _peco_project() -> ResearchProject:
    p = _project()
    p.population = Population(description="Adults aged 40-70 without prior cancer diagnosis")
    p.exposure = Exposure(description="Current or former smoking status")
    p.comparator = Comparator(description="Never-smokers")
    p.primary_outcome = Outcome(
        name="Lung cancer incidence",
        description="New diagnosis of lung cancer during follow-up",
        is_primary=True,
    )
    p.research_framework = ResearchFramework(
        framework_type="PECO",
        population="Adults aged 40-70 without prior cancer diagnosis",
        exposure="Current or former smoking status",
        comparator="Never-smokers",
        outcome="New diagnosis of lung cancer during follow-up",
    )
    return p


# ──────────────────────────────────────────────
# 1. PICO strategy generation
# ──────────────────────────────────────────────

class TestPICOStrategyGeneration:
    def test_pico_strategy_builds_successfully(self):
        p = _pico_project()
        strategy = build_search_strategy(p)
        assert strategy is not None
        assert strategy.framework_type == "PICO"

    def test_pico_population_terms_populated(self):
        p = _pico_project()
        strategy = build_search_strategy(p)
        assert len(strategy.population_terms) > 0

    def test_pico_intervention_terms_populated(self):
        p = _pico_project()
        strategy = build_search_strategy(p)
        assert len(strategy.intervention_terms) > 0

    def test_pico_exposure_terms_empty(self):
        p = _pico_project()
        strategy = build_search_strategy(p)
        assert strategy.exposure_terms == []

    def test_pico_outcome_terms_populated(self):
        p = _pico_project()
        strategy = build_search_strategy(p)
        assert len(strategy.outcome_terms) > 0

    def test_pico_ready_for_search_when_complete(self):
        p = _pico_project()
        strategy = build_search_strategy(p)
        assert strategy.ready_for_search is True

    def test_pico_boolean_query_generated(self):
        p = _pico_project()
        strategy = build_search_strategy(p)
        assert strategy.boolean_query is not None
        assert "AND" in strategy.boolean_query

    def test_pico_boolean_query_contains_population(self):
        p = _pico_project()
        strategy = build_search_strategy(p)
        assert "Adults with type 2 diabetes" in strategy.boolean_query

    def test_pico_boolean_query_contains_intervention(self):
        p = _pico_project()
        strategy = build_search_strategy(p)
        assert "Metformin" in strategy.boolean_query

    def test_pico_boolean_query_contains_outcome(self):
        p = _pico_project()
        strategy = build_search_strategy(p)
        assert "cardiovascular" in strategy.boolean_query.lower()


# ──────────────────────────────────────────────
# 2. PECO strategy generation
# ──────────────────────────────────────────────

class TestPECOStrategyGeneration:
    def test_peco_strategy_builds_successfully(self):
        p = _peco_project()
        strategy = build_search_strategy(p)
        assert strategy is not None
        assert strategy.framework_type == "PECO"

    def test_peco_population_terms_populated(self):
        p = _peco_project()
        strategy = build_search_strategy(p)
        assert len(strategy.population_terms) > 0

    def test_peco_exposure_terms_populated(self):
        p = _peco_project()
        strategy = build_search_strategy(p)
        assert len(strategy.exposure_terms) > 0

    def test_peco_intervention_terms_empty(self):
        p = _peco_project()
        strategy = build_search_strategy(p)
        assert strategy.intervention_terms == []

    def test_peco_ready_for_search_when_complete(self):
        p = _peco_project()
        strategy = build_search_strategy(p)
        assert strategy.ready_for_search is True

    def test_peco_boolean_query_contains_exposure(self):
        p = _peco_project()
        strategy = build_search_strategy(p)
        assert "smoking" in strategy.boolean_query.lower()


# ──────────────────────────────────────────────
# 3. Boolean query generation
# ──────────────────────────────────────────────

class TestBooleanQueryGeneration:
    def test_complete_pico_framework_generates_query(self):
        fw = ResearchFramework(
            framework_type="PICO",
            population="Adults with T2DM",
            intervention="Metformin",
            comparator="Placebo",
            outcome="All-cause mortality",
        )
        query = build_boolean_query(fw)
        assert query is not None

    def test_query_contains_and_operator(self):
        fw = ResearchFramework(
            framework_type="PICO",
            population="Adults with T2DM",
            intervention="Metformin",
            comparator="Placebo",
            outcome="All-cause mortality",
        )
        query = build_boolean_query(fw)
        assert "AND" in query

    def test_query_contains_all_required_elements(self):
        fw = ResearchFramework(
            framework_type="PICO",
            population="Adults with T2DM",
            intervention="Metformin",
            comparator=None,
            outcome="All-cause mortality",
        )
        query = build_boolean_query(fw)
        assert "Adults with T2DM" in query
        assert "Metformin" in query
        assert "All-cause mortality" in query

    def test_query_includes_comparator_when_present(self):
        fw = ResearchFramework(
            framework_type="PICO",
            population="Adults with T2DM",
            intervention="Metformin",
            comparator="Placebo",
            outcome="All-cause mortality",
        )
        query = build_boolean_query(fw)
        assert "Placebo" in query

    def test_query_terms_are_quoted(self):
        fw = ResearchFramework(
            framework_type="PICO",
            population="Adults with T2DM",
            intervention="Metformin",
            comparator=None,
            outcome="Mortality",
        )
        query = build_boolean_query(fw)
        assert '"' in query

    def test_peco_query_uses_exposure_not_intervention(self):
        fw = ResearchFramework(
            framework_type="PECO",
            population="Adults aged 40-70",
            exposure="Smoking",
            comparator=None,
            outcome="Lung cancer",
        )
        query = build_boolean_query(fw)
        assert query is not None
        assert "Smoking" in query


# ──────────────────────────────────────────────
# 4. Missing population
# ──────────────────────────────────────────────

class TestMissingPopulation:
    def test_missing_population_prevents_ready_for_search(self):
        p = _project()
        p.research_framework = ResearchFramework(
            framework_type="PICO",
            population=None,
            intervention="Metformin",
            comparator="Placebo",
            outcome="Mortality",
        )
        strategy = build_search_strategy(p)
        assert strategy.ready_for_search is False

    def test_missing_population_in_missing_components(self):
        p = _project()
        p.research_framework = ResearchFramework(
            framework_type="PICO",
            population=None,
            intervention="Metformin",
            comparator="Placebo",
            outcome="Mortality",
        )
        strategy = build_search_strategy(p)
        assert "population" in strategy.missing_components

    def test_missing_population_no_boolean_query(self):
        fw = ResearchFramework(
            framework_type="PICO",
            population=None,
            intervention="Metformin",
            comparator=None,
            outcome="Mortality",
        )
        assert build_boolean_query(fw) is None

    def test_missing_population_generates_warning(self):
        p = _project()
        p.research_framework = ResearchFramework(
            framework_type="PICO",
            population=None,
            intervention="Metformin",
            comparator=None,
            outcome="Mortality",
        )
        strategy = build_search_strategy(p)
        assert len(strategy.warnings) > 0
        assert any("population" in w.lower() for w in strategy.warnings)


# ──────────────────────────────────────────────
# 5. Missing outcome
# ──────────────────────────────────────────────

class TestMissingOutcome:
    def test_missing_outcome_prevents_ready_for_search(self):
        p = _project()
        p.research_framework = ResearchFramework(
            framework_type="PICO",
            population="Adults with T2DM",
            intervention="Metformin",
            comparator="Placebo",
            outcome=None,
        )
        strategy = build_search_strategy(p)
        assert strategy.ready_for_search is False

    def test_missing_outcome_in_missing_components(self):
        p = _project()
        p.research_framework = ResearchFramework(
            framework_type="PICO",
            population="Adults with T2DM",
            intervention="Metformin",
            comparator="Placebo",
            outcome=None,
        )
        strategy = build_search_strategy(p)
        assert "outcome" in strategy.missing_components

    def test_missing_outcome_no_boolean_query(self):
        fw = ResearchFramework(
            framework_type="PICO",
            population="Adults with T2DM",
            intervention="Metformin",
            comparator=None,
            outcome=None,
        )
        assert build_boolean_query(fw) is None


# ──────────────────────────────────────────────
# 6. Missing intervention (PICO)
# ──────────────────────────────────────────────

class TestMissingIntervention:
    def test_missing_intervention_prevents_ready_for_search(self):
        p = _project()
        p.research_framework = ResearchFramework(
            framework_type="PICO",
            population="Adults with T2DM",
            intervention=None,
            comparator="Placebo",
            outcome="Mortality",
        )
        strategy = build_search_strategy(p)
        assert strategy.ready_for_search is False

    def test_missing_intervention_in_missing_components(self):
        p = _project()
        p.research_framework = ResearchFramework(
            framework_type="PICO",
            population="Adults with T2DM",
            intervention=None,
            comparator="Placebo",
            outcome="Mortality",
        )
        strategy = build_search_strategy(p)
        assert "intervention" in strategy.missing_components

    def test_missing_intervention_no_boolean_query(self):
        fw = ResearchFramework(
            framework_type="PICO",
            population="Adults with T2DM",
            intervention=None,
            comparator=None,
            outcome="Mortality",
        )
        assert build_boolean_query(fw) is None


# ──────────────────────────────────────────────
# 7. Missing exposure (PECO)
# ──────────────────────────────────────────────

class TestMissingExposure:
    def test_missing_exposure_prevents_ready_for_search(self):
        p = _project()
        p.research_framework = ResearchFramework(
            framework_type="PECO",
            population="Adults aged 40-70",
            exposure=None,
            comparator="Non-smokers",
            outcome="Lung cancer",
        )
        strategy = build_search_strategy(p)
        assert strategy.ready_for_search is False

    def test_missing_exposure_in_missing_components(self):
        p = _project()
        p.research_framework = ResearchFramework(
            framework_type="PECO",
            population="Adults aged 40-70",
            exposure=None,
            comparator="Non-smokers",
            outcome="Lung cancer",
        )
        strategy = build_search_strategy(p)
        assert "exposure" in strategy.missing_components

    def test_missing_exposure_no_boolean_query(self):
        fw = ResearchFramework(
            framework_type="PECO",
            population="Adults aged 40-70",
            exposure=None,
            comparator=None,
            outcome="Lung cancer",
        )
        assert build_boolean_query(fw) is None


# ──────────────────────────────────────────────
# 8. No-invention rule
# ──────────────────────────────────────────────

class TestNoInventionRule:
    def test_boolean_query_contains_only_researcher_terms(self):
        fw = ResearchFramework(
            framework_type="PICO",
            population="Unique population text",
            intervention="Unique intervention text",
            comparator=None,
            outcome="Unique outcome text",
        )
        query = build_boolean_query(fw)
        assert "Unique population text" in query
        assert "Unique intervention text" in query
        assert "Unique outcome text" in query

    def test_no_synonyms_added_to_terms(self):
        fw = ResearchFramework(
            framework_type="PICO",
            population="Adults with T2DM",
            intervention="Metformin",
            comparator=None,
            outcome="Mortality",
        )
        terms = extract_search_terms(fw)
        all_terms = (
            terms["population_terms"]
            + terms["intervention_terms"]
            + terms["outcome_terms"]
        )
        for term in all_terms:
            assert "diabetes mellitus type 2" not in term.lower()
            assert "type 2 diabetes mellitus" not in term.lower()

    def test_missing_field_produces_empty_terms_not_guesses(self):
        fw = ResearchFramework(
            framework_type="PICO",
            population=None,
            intervention="Metformin",
            comparator=None,
            outcome="Mortality",
        )
        terms = extract_search_terms(fw)
        assert terms["population_terms"] == []

    def test_no_fake_records_created(self):
        p = _pico_project()
        build_search_strategy(p)
        assert p.literature_records == []

    def test_strategy_does_not_invent_comparator_terms(self):
        fw = ResearchFramework(
            framework_type="PICO",
            population="Adults with T2DM",
            intervention="Metformin",
            comparator=None,
            outcome="Mortality",
        )
        terms = extract_search_terms(fw)
        assert terms["comparator_terms"] == []

    def test_comparator_not_extracted_from_free_text(self):
        p = _project(
            idea="Comparing metformin versus placebo in adults with type 2 diabetes"
        )
        strategy = build_search_strategy(p)
        assert strategy.comparator_terms == []


# ──────────────────────────────────────────────
# 9. Empty framework
# ──────────────────────────────────────────────

class TestEmptyFramework:
    def test_empty_framework_not_ready_for_search(self):
        p = _project()
        p.research_framework = ResearchFramework(framework_type="PICO")
        strategy = build_search_strategy(p)
        assert strategy.ready_for_search is False

    def test_empty_framework_no_boolean_query(self):
        p = _project()
        p.research_framework = ResearchFramework(framework_type="PICO")
        strategy = build_search_strategy(p)
        assert strategy.boolean_query is None

    def test_empty_framework_all_terms_empty(self):
        fw = ResearchFramework(framework_type="PICO")
        terms = extract_search_terms(fw)
        assert terms["population_terms"] == []
        assert terms["intervention_terms"] == []
        assert terms["outcome_terms"] == []

    def test_empty_framework_has_missing_components(self):
        p = _project()
        p.research_framework = ResearchFramework(framework_type="PICO")
        strategy = build_search_strategy(p)
        assert len(strategy.missing_components) > 0

    def test_empty_framework_has_warnings(self):
        p = _project()
        p.research_framework = ResearchFramework(framework_type="PICO")
        strategy = build_search_strategy(p)
        assert len(strategy.warnings) > 0


# ──────────────────────────────────────────────
# 10. Strategy validation
# ──────────────────────────────────────────────

class TestStrategyValidation:
    def test_complete_strategy_is_valid(self):
        p = _pico_project()
        strategy = build_search_strategy(p)
        is_valid, issues = validate_search_strategy(strategy)
        assert is_valid is True
        assert issues == []

    def test_incomplete_strategy_is_invalid(self):
        p = _project()
        p.research_framework = ResearchFramework(framework_type="PICO")
        strategy = build_search_strategy(p)
        is_valid, issues = validate_search_strategy(strategy)
        assert is_valid is False
        assert len(issues) > 0

    def test_missing_population_makes_invalid(self):
        p = _project()
        p.research_framework = ResearchFramework(
            framework_type="PICO",
            population=None,
            intervention="Metformin",
            comparator=None,
            outcome="Mortality",
        )
        strategy = build_search_strategy(p)
        is_valid, issues = validate_search_strategy(strategy)
        assert is_valid is False
        assert any("population" in i.lower() for i in issues)

    def test_missing_outcome_makes_invalid(self):
        p = _project()
        p.research_framework = ResearchFramework(
            framework_type="PICO",
            population="Adults",
            intervention="Metformin",
            comparator=None,
            outcome=None,
        )
        strategy = build_search_strategy(p)
        is_valid, issues = validate_search_strategy(strategy)
        assert is_valid is False
        assert any("outcome" in i.lower() for i in issues)

    def test_peco_complete_strategy_is_valid(self):
        p = _peco_project()
        strategy = build_search_strategy(p)
        is_valid, issues = validate_search_strategy(strategy)
        assert is_valid is True


# ──────────────────────────────────────────────
# 11. Serialization roundtrip
# ──────────────────────────────────────────────

class TestSerializationRoundtrip:
    def test_strategy_serializes_to_json(self):
        p = _pico_project()
        strategy = build_search_strategy(p)
        json_str = strategy.model_dump_json()
        assert "PICO" in json_str
        assert "boolean_query" in json_str

    def test_strategy_roundtrip(self):
        p = _pico_project()
        strategy = build_search_strategy(p)
        json_str = strategy.model_dump_json()
        restored = LiteratureSearchStrategy.model_validate_json(json_str)
        assert restored.framework_type == "PICO"
        assert restored.ready_for_search == strategy.ready_for_search
        assert restored.boolean_query == strategy.boolean_query
        assert restored.population_terms == strategy.population_terms

    def test_project_with_strategy_roundtrip(self):
        p = _pico_project()
        p.literature_search_strategy = build_search_strategy(p)
        json_str = p.model_dump_json()
        restored = ResearchProject.model_validate_json(json_str)
        assert restored.literature_search_strategy is not None
        assert restored.literature_search_strategy.framework_type == "PICO"
        assert restored.literature_search_strategy.ready_for_search is True

    def test_research_state_with_strategy_roundtrip(self):
        p = _pico_project()
        p.literature_search_strategy = build_search_strategy(p)
        state = ResearchState(project=p)
        json_str = state.model_dump_json()
        restored = ResearchState.model_validate_json(json_str)
        assert restored.project.literature_search_strategy is not None
        assert restored.project.literature_search_strategy.boolean_query is not None

    def test_literature_record_serializes(self):
        record = LiteratureRecord(
            title="A study on treatment outcomes",
            authors=["Smith J", "Jones A"],
            journal="The Lancet",
            pmid="12345678",
        )
        json_str = record.model_dump_json()
        restored = LiteratureRecord.model_validate_json(json_str)
        assert restored.title == "A study on treatment outcomes"
        assert restored.pmid == "12345678"
        assert len(restored.authors) == 2

    def test_screening_decision_serializes(self):
        decision = ScreeningDecision(
            record_id="rec-001",
            decision=ScreeningDecisionEnum.INCLUDE,
            reason="Meets all inclusion criteria",
        )
        json_str = decision.model_dump_json()
        restored = ScreeningDecision.model_validate_json(json_str)
        assert restored.decision == ScreeningDecisionEnum.INCLUDE
        assert restored.record_id == "rec-001"


# ──────────────────────────────────────────────
# 12. Backward compatibility
# ──────────────────────────────────────────────

class TestBackwardCompatibility:
    def test_sprint1_project_loads_without_literature_fields(self):
        sprint1_dict = {
            "id": "abc-123",
            "title": "Sprint 1 Legacy Project",
            "idea": "A legacy research idea from sprint one without literature fields",
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T00:00:00",
            "state": "IDEA",
            "tasks": [],
            "secondary_outcomes": [],
            "inclusion_criteria": {"criteria": []},
            "exclusion_criteria": {"criteria": []},
        }
        project = ResearchProject.model_validate(sprint1_dict)
        assert project.literature_search_strategy is None
        assert project.literature_records == []
        assert project.screening_decisions == []

    def test_sprint2_project_loads_without_literature_fields(self):
        sprint2_dict = {
            "id": "abc-456",
            "title": "Sprint 2 Legacy Project",
            "idea": "A sprint two project without literature fields added in sprint three",
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T00:00:00",
            "state": "QUESTION_DEFINED",
            "tasks": [],
            "secondary_outcomes": [],
            "inclusion_criteria": {"criteria": []},
            "exclusion_criteria": {"criteria": []},
            "research_framework": {
                "framework_type": "PICO",
                "population": "Adults with T2DM",
                "intervention": "Metformin",
                "comparator": "Placebo",
                "outcome": "Mortality",
            },
        }
        project = ResearchProject.model_validate(sprint2_dict)
        assert project.research_framework is not None
        assert project.literature_search_strategy is None

    def test_schema_version_is_1_2_0(self):
        state = ResearchState()
        assert state.schema_version == "1.2.0"

    def test_full_state_wrapper_backward_compat(self):
        old_state_dict = {
            "schema_version": "1.1.0",
            "saved_at": "2024-01-01T00:00:00",
            "project": {
                "id": "abc-789",
                "title": "Old Schema Project",
                "idea": "Testing that old schema version projects load correctly in sprint three",
                "created_at": "2024-01-01T00:00:00",
                "updated_at": "2024-01-01T00:00:00",
                "state": "IDEA",
                "tasks": [],
                "secondary_outcomes": [],
                "inclusion_criteria": {"criteria": []},
                "exclusion_criteria": {"criteria": []},
            },
        }
        state = ResearchState.model_validate(old_state_dict)
        assert state.project is not None
        assert state.project.literature_search_strategy is None
        assert state.project.literature_records == []


# ──────────────────────────────────────────────
# 13. Task generation
# ──────────────────────────────────────────────

class TestLiteratureTaskGeneration:
    def test_generates_literature_tasks(self):
        p = _project()
        tasks = generate_literature_tasks(p)
        assert len(tasks) > 0

    def test_generates_five_literature_tasks(self):
        p = _project()
        tasks = generate_literature_tasks(p)
        assert len(tasks) == 5

    def test_all_tasks_are_todo(self):
        p = _project()
        tasks = generate_literature_tasks(p)
        for task in tasks:
            assert task.status == TaskStatus.TODO

    def test_tasks_have_no_dependencies(self):
        p = _project()
        tasks = generate_literature_tasks(p)
        for task in tasks:
            assert task.dependencies == []

    def test_tasks_have_required_fields(self):
        p = _project()
        tasks = generate_literature_tasks(p)
        for task in tasks:
            assert task.title
            assert task.description
            assert task.why
            assert task.id

    def test_build_search_strategy_task_present(self):
        p = _project()
        tasks = generate_literature_tasks(p)
        titles = [t.title for t in tasks]
        assert "Build literature search strategy" in titles

    def test_run_literature_search_task_present(self):
        p = _project()
        tasks = generate_literature_tasks(p)
        titles = [t.title for t in tasks]
        assert "Run literature search" in titles

    def test_screen_titles_abstracts_task_present(self):
        p = _project()
        tasks = generate_literature_tasks(p)
        titles = [t.title for t in tasks]
        assert "Screen titles and abstracts" in titles

    def test_tasks_completable_via_task_engine(self):
        from core.task_engine import can_complete_task, complete_task
        p = _project()
        tasks = generate_literature_tasks(p)
        for t in tasks:
            p.tasks.append(t)
        for task in p.tasks:
            assert can_complete_task(p, task.id) is True
            complete_task(p, task.id)
            assert task.status == TaskStatus.COMPLETED


# ──────────────────────────────────────────────
# 14. Task deduplication
# ──────────────────────────────────────────────

class TestLiteratureTaskDeduplication:
    def test_second_call_generates_no_new_tasks(self):
        p = _project()
        tasks1 = generate_literature_tasks(p)
        for t in tasks1:
            p.tasks.append(t)
        tasks2 = generate_literature_tasks(p)
        assert len(tasks2) == 0

    def test_repeated_calls_do_not_accumulate_duplicates(self):
        p = _project()
        for _ in range(3):
            new = generate_literature_tasks(p)
            for t in new:
                p.tasks.append(t)
        titles = [t.title for t in p.tasks]
        assert len(titles) == len(set(titles))

    def test_titles_unique_after_multiple_strategy_builds(self):
        p = _pico_project()
        for _ in range(3):
            p.literature_search_strategy = build_search_strategy(p)
            new_tasks = generate_literature_tasks(p)
            for t in new_tasks:
                p.tasks.append(t)
        titles = [t.title for t in p.tasks]
        assert len(titles) == len(set(titles))


# ──────────────────────────────────────────────
# 15. LiteratureRecord validation
# ──────────────────────────────────────────────

class TestLiteratureRecordValidation:
    def test_minimal_record_valid(self):
        record = LiteratureRecord()
        assert record.id is not None

    def test_record_with_all_fields(self):
        from datetime import datetime
        record = LiteratureRecord(
            title="Effect of treatment on outcomes",
            authors=["Smith J", "Jones A", "Williams B"],
            journal="The Lancet",
            publication_date="2023-06-15",
            abstract="This study examined the effect of treatment on outcomes.",
            doi="10.1000/xyz123",
            pmid="12345678",
            source="PubMed",
            url="https://pubmed.ncbi.nlm.nih.gov/12345678/",
            retrieved_at=datetime(2024, 1, 1),
        )
        assert record.title == "Effect of treatment on outcomes"
        assert len(record.authors) == 3
        assert record.pmid == "12345678"
        assert record.source == "PubMed"

    def test_record_unique_ids(self):
        r1 = LiteratureRecord()
        r2 = LiteratureRecord()
        assert r1.id != r2.id

    def test_record_authors_default_empty(self):
        record = LiteratureRecord()
        assert record.authors == []

    def test_no_fake_records_in_project(self):
        p = _pico_project()
        build_search_strategy(p)
        assert p.literature_records == []


# ──────────────────────────────────────────────
# 16. ScreeningDecision validation
# ──────────────────────────────────────────────

class TestScreeningDecisionValidation:
    def test_pending_decision_default(self):
        decision = ScreeningDecision(record_id="rec-001")
        assert decision.decision == ScreeningDecisionEnum.PENDING

    def test_include_decision(self):
        decision = ScreeningDecision(
            record_id="rec-001",
            decision=ScreeningDecisionEnum.INCLUDE,
            reason="Meets all inclusion criteria",
        )
        assert decision.decision == ScreeningDecisionEnum.INCLUDE

    def test_exclude_decision(self):
        decision = ScreeningDecision(
            record_id="rec-002",
            decision=ScreeningDecisionEnum.EXCLUDE,
            reason="Wrong population",
        )
        assert decision.decision == ScreeningDecisionEnum.EXCLUDE

    def test_maybe_decision(self):
        decision = ScreeningDecision(
            record_id="rec-003",
            decision=ScreeningDecisionEnum.MAYBE,
            notes="Needs full text review",
        )
        assert decision.decision == ScreeningDecisionEnum.MAYBE

    def test_all_decisions_valid(self):
        for dec in ScreeningDecisionEnum:
            d = ScreeningDecision(record_id="rec-test", decision=dec)
            assert d.decision == dec

    def test_invalid_decision_rejected(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            ScreeningDecision(record_id="rec-001", decision="INVALID")

    def test_screening_decisions_in_project(self):
        p = _project()
        p.screening_decisions.append(
            ScreeningDecision(
                record_id="rec-001",
                decision=ScreeningDecisionEnum.INCLUDE,
            )
        )
        assert len(p.screening_decisions) == 1
        assert p.screening_decisions[0].decision == ScreeningDecisionEnum.INCLUDE


# ──────────────────────────────────────────────
# 17. Repeated strategy generation
# ──────────────────────────────────────────────

class TestRepeatedStrategyGeneration:
    def test_repeated_build_is_stable(self):
        p = _pico_project()
        s1 = build_search_strategy(p)
        s2 = build_search_strategy(p)
        assert s1.boolean_query == s2.boolean_query
        assert s1.population_terms == s2.population_terms
        assert s1.ready_for_search == s2.ready_for_search

    def test_strategy_updates_when_framework_changes(self):
        p = _pico_project()
        s1 = build_search_strategy(p)
        assert s1.ready_for_search is True
        p.research_framework.outcome = None
        s2 = build_search_strategy(p)
        assert s2.ready_for_search is False

    def test_strategy_id_changes_on_each_build(self):
        p = _pico_project()
        s1 = build_search_strategy(p)
        s2 = build_search_strategy(p)
        assert s1.id != s2.id


# ──────────────────────────────────────────────
# 18. Existing Sprint 1/2 behavior unchanged
# ──────────────────────────────────────────────

class TestExistingBehaviorPreserved:
    def test_sprint1_task_engine_unchanged(self):
        from core.task_engine import create_task, complete_task, can_complete_task
        p = _project()
        task = create_task(
            p,
            "Sprint 1 task test",
            "Testing Sprint 1 task engine still works correctly",
            "Backward compatibility",
        )
        assert task.status == TaskStatus.TODO
        assert can_complete_task(p, task.id) is True
        complete_task(p, task.id)
        assert task.status == TaskStatus.COMPLETED

    def test_sprint1_state_machine_unchanged(self):
        from core.state import transition_state, InvalidStateTransitionError
        from core.models import ResearchStateEnum
        result = transition_state(
            ResearchStateEnum.IDEA, ResearchStateEnum.QUESTION_DEFINED
        )
        assert result == ResearchStateEnum.QUESTION_DEFINED
        with pytest.raises(InvalidStateTransitionError):
            transition_state(
                ResearchStateEnum.IDEA, ResearchStateEnum.READY_FOR_SUBMISSION
            )

    def test_sprint2_framework_engine_unchanged(self):
        from core.research_engine import build_framework, validate_framework
        from core.models import FrameworkCompleteness
        p = _pico_project()
        fw = build_framework(p)
        result = validate_framework(fw)
        assert result.status == FrameworkCompleteness.COMPLETE

    def test_sprint2_state_gates_unchanged(self):
        from core.state import StateGateError, transition_state_gated
        from core.models import ResearchStateEnum
        p = _project()
        with pytest.raises(StateGateError):
            transition_state_gated(
                ResearchStateEnum.IDEA, ResearchStateEnum.QUESTION_DEFINED, p
            )

    def test_sprint1_initial_tasks_unchanged(self):
        from core.task_engine import generate_initial_tasks
        p = _project()
        generate_initial_tasks(p)
        assert len(p.tasks) == 8

    def test_sprint1_persistence_unchanged(self):
        import tempfile
        from pathlib import Path
        from core.persistence import save_project, load_project
        tmp = Path(tempfile.mkdtemp()) / "compat_test.json"
        p = _pico_project()
        save_project(p, tmp)
        loaded = load_project(tmp)
        assert loaded.title == p.title
        assert loaded.id == p.id
