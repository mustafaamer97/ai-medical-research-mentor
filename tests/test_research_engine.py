"""
tests/test_research_engine.py
Sprint 2 — Research Engine tests.
"""
from __future__ import annotations

import pytest

from core.models import (
    Comparator,
    Exposure,
    FrameworkCompleteness,
    Intervention,
    Outcome,
    Population,
    ResearchFramework,
    ResearchProject,
    ResearchQuestion,
    ResearchState,
    StudyDesign,
    StudyDesignType,
    TaskStatus,
)
from core.research_engine import (
    build_framework,
    build_research_question,
    check_design_selected_ready,
    check_question_defined_ready,
    generate_framework_tasks,
    generate_research_objectives,
    infer_framework_type,
    recommend_study_design,
    validate_framework,
)
from core.state import (
    InvalidStateTransitionError,
    StateGateError,
    transition_state,
    transition_state_gated,
)


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

def _project(
    title: str = "Test Project Title",
    idea: str = "Test research idea for engine testing purposes",
) -> ResearchProject:
    return ResearchProject(title=title, idea=idea)


def _pico_project() -> ResearchProject:
    p = _project(
        title="Metformin RCT",
        idea="Effect of metformin treatment on cardiovascular outcomes in adults with type 2 diabetes",
    )
    p.population = Population(description="Adults with type 2 diabetes aged 18-75")
    p.intervention = Intervention(description="Metformin 1000mg twice daily")
    p.comparator = Comparator(description="Placebo")
    p.primary_outcome = Outcome(
        name="Cardiovascular mortality",
        description="Death from cardiovascular causes at 5 years",
        is_primary=True,
    )
    return p


def _peco_project() -> ResearchProject:
    p = _project(
        title="Smoking and Lung Cancer",
        idea="Association between smoking exposure and lung cancer incidence in middle-aged adults",
    )
    p.population = Population(description="Adults aged 40-70 without prior cancer diagnosis")
    p.exposure = Exposure(description="Current or former smoking status")
    p.comparator = Comparator(description="Never-smokers")
    p.primary_outcome = Outcome(
        name="Lung cancer incidence",
        description="New diagnosis of lung cancer during follow-up",
        is_primary=True,
    )
    return p


# ──────────────────────────────────────────────
# 1. PICO detection
# ──────────────────────────────────────────────

class TestPICODetection:
    def test_intervention_field_forces_pico(self):
        p = _project(idea="Some research idea about patients in a study")
        p.intervention = Intervention(description="Drug X treatment protocol")
        assert infer_framework_type(p) == "PICO"

    def test_intervention_keyword_infers_pico(self):
        p = _project(idea="Effect of intervention treatment on outcomes in patients")
        assert infer_framework_type(p) == "PICO"

    def test_rct_keyword_infers_pico(self):
        p = _project(idea="Randomized controlled trial of therapy in adults")
        assert infer_framework_type(p) == "PICO"

    def test_pico_project_builds_pico_framework(self):
        p = _pico_project()
        fw = build_framework(p)
        assert fw.framework_type == "PICO"

    def test_pico_framework_has_intervention_not_exposure(self):
        p = _pico_project()
        fw = build_framework(p)
        assert fw.intervention is not None
        assert fw.exposure is None

    def test_diagnostic_keywords_infer_pico(self):
        p = _project(idea="Sensitivity and specificity of diagnostic test for screening")
        assert infer_framework_type(p) == "PICO"

    def test_metformin_intervention_example_is_pico(self):
        """Point 3 verification: classic metformin intervention study → PICO."""
        p = _project(
            title="Metformin cardiovascular study",
            idea="Effect of metformin compared with standard care on cardiovascular outcomes in adults with type 2 diabetes",
        )
        assert infer_framework_type(p) == "PICO"


# ──────────────────────────────────────────────
# 2. PECO detection
# ──────────────────────────────────────────────

class TestPECODetection:
    def test_exposure_field_forces_peco(self):
        p = _project(idea="Some research idea about risk factor in population")
        p.exposure = Exposure(description="Smoking exposure measurement")
        assert infer_framework_type(p) == "PECO"

    def test_exposure_keyword_infers_peco(self):
        p = _project(idea="Association between exposure to environmental factor and disease incidence")
        assert infer_framework_type(p) == "PECO"

    def test_observational_keyword_infers_peco(self):
        p = _project(idea="Prospective cohort study of risk factors in middle-aged adults")
        assert infer_framework_type(p) == "PECO"

    def test_peco_project_builds_peco_framework(self):
        p = _peco_project()
        fw = build_framework(p)
        assert fw.framework_type == "PECO"

    def test_peco_framework_has_exposure_not_intervention(self):
        p = _peco_project()
        fw = build_framework(p)
        assert fw.exposure is not None
        assert fw.intervention is None

    def test_smoking_lung_cancer_example_is_peco(self):
        """Point 4 verification: smoking/lung cancer → PECO."""
        p = _project(
            title="Smoking lung cancer study",
            idea="Association between smoking exposure and lung cancer among adults",
        )
        assert infer_framework_type(p) == "PECO"

    def test_peco_exposure_separate_from_intervention(self):
        """Point 4: exposure field must not bleed into intervention."""
        p = _peco_project()
        fw = build_framework(p)
        assert fw.intervention is None
        assert fw.exposure == "Current or former smoking status"


# ──────────────────────────────────────────────
# 3. Missing comparator detection — never invented
# ──────────────────────────────────────────────

class TestMissingComparator:
    def test_missing_comparator_detected(self):
        p = _pico_project()
        p.comparator = None
        fw = build_framework(p)
        assert "comparator" in fw.missing_fields()

    def test_missing_comparator_in_validation(self):
        p = _pico_project()
        p.comparator = None
        fw = build_framework(p)
        result = validate_framework(fw)
        assert "comparator" in result.missing_fields

    def test_missing_comparator_prevents_complete_status(self):
        p = _pico_project()
        p.comparator = None
        fw = build_framework(p)
        result = validate_framework(fw)
        assert result.status != FrameworkCompleteness.COMPLETE

    def test_missing_comparator_no_draft_question(self):
        p = _pico_project()
        p.comparator = None
        fw = build_framework(p)
        result = validate_framework(fw)
        assert result.draft_question is None

    def test_comparator_never_extracted_from_free_text(self):
        """Point 3 + 5: comparator must be None even when idea mentions 'standard care'."""
        p = _project(
            idea="Effect of metformin compared with standard care on cardiovascular outcomes in adults with type 2 diabetes",
        )
        # No comparator model field set — must not be extracted from text
        fw = build_framework(p)
        assert fw.comparator is None

    def test_comparator_only_from_explicit_model_field(self):
        p = _project(idea="Some research idea about patients receiving treatment versus placebo")
        p.comparator = Comparator(description="Placebo")
        fw = build_framework(p)
        assert fw.comparator == "Placebo"


# ──────────────────────────────────────────────
# 4. Missing outcome detection
# ──────────────────────────────────────────────

class TestMissingOutcome:
    def test_missing_outcome_detected(self):
        p = _pico_project()
        p.primary_outcome = None
        fw = build_framework(p)
        assert "outcome" in fw.missing_fields()

    def test_missing_outcome_in_validation(self):
        p = _pico_project()
        p.primary_outcome = None
        fw = build_framework(p)
        result = validate_framework(fw)
        assert "outcome" in result.missing_fields

    def test_missing_outcome_prevents_complete(self):
        p = _pico_project()
        p.primary_outcome = None
        fw = build_framework(p)
        result = validate_framework(fw)
        assert result.status != FrameworkCompleteness.COMPLETE


# ──────────────────────────────────────────────
# 5. Missing population detection
# ──────────────────────────────────────────────

class TestMissingPopulation:
    def test_missing_population_detected_pico(self):
        fw = ResearchFramework(
            framework_type="PICO",
            population=None,
            intervention="Drug X",
            comparator="Placebo",
            outcome="Mortality",
        )
        assert "population" in fw.missing_fields()

    def test_missing_population_detected_peco(self):
        fw = ResearchFramework(
            framework_type="PECO",
            population=None,
            exposure="Smoking",
            comparator="Non-smokers",
            outcome="Lung cancer",
        )
        assert "population" in fw.missing_fields()

    def test_missing_population_validation_result(self):
        fw = ResearchFramework(
            framework_type="PICO",
            population=None,
            intervention="Drug X",
            comparator="Placebo",
            outcome="Mortality",
        )
        result = validate_framework(fw)
        assert "population" in result.missing_fields


# ──────────────────────────────────────────────
# 6. Complete framework
# ──────────────────────────────────────────────

class TestCompleteFramework:
    def test_complete_pico_framework(self):
        fw = ResearchFramework(
            framework_type="PICO",
            population="Adults with T2DM",
            intervention="Metformin",
            comparator="Placebo",
            outcome="Cardiovascular mortality at 5 years",
        )
        assert fw.is_complete() is True
        assert fw.missing_fields() == []

    def test_complete_peco_framework(self):
        fw = ResearchFramework(
            framework_type="PECO",
            population="Adults aged 40-70",
            exposure="Smoking",
            comparator="Non-smokers",
            outcome="Lung cancer incidence",
        )
        assert fw.is_complete() is True

    def test_complete_framework_validation_status(self):
        fw = ResearchFramework(
            framework_type="PICO",
            population="Adults with T2DM",
            intervention="Metformin",
            comparator="Placebo",
            outcome="Cardiovascular mortality at 5 years",
        )
        result = validate_framework(fw)
        assert result.status == FrameworkCompleteness.COMPLETE

    def test_complete_framework_score_100(self):
        fw = ResearchFramework(
            framework_type="PICO",
            population="Adults with T2DM",
            intervention="Metformin",
            comparator="Placebo",
            outcome="Cardiovascular mortality at 5 years",
        )
        result = validate_framework(fw)
        assert result.completeness_score == 100

    def test_complete_pico_project(self):
        p = _pico_project()
        fw = build_framework(p)
        result = validate_framework(fw)
        assert result.status == FrameworkCompleteness.COMPLETE


# ──────────────────────────────────────────────
# 7. Incomplete framework
# ──────────────────────────────────────────────

class TestIncompleteFramework:
    def test_empty_pico_framework_is_incomplete(self):
        fw = ResearchFramework(framework_type="PICO")
        assert fw.is_complete() is False
        assert len(fw.missing_fields()) == 4

    def test_empty_peco_framework_is_incomplete(self):
        fw = ResearchFramework(framework_type="PECO")
        assert fw.is_complete() is False
        assert len(fw.missing_fields()) == 4

    def test_partially_filled_framework_needs_clarification(self):
        fw = ResearchFramework(
            framework_type="PICO",
            population="Adults with T2DM",
            intervention="Metformin",
            comparator=None,
            outcome=None,
        )
        result = validate_framework(fw)
        assert result.status == FrameworkCompleteness.NEEDS_CLARIFICATION

    def test_incomplete_framework_zero_draft_question(self):
        fw = ResearchFramework(framework_type="PICO")
        result = validate_framework(fw)
        assert result.draft_question is None

    def test_completeness_score_partial(self):
        fw = ResearchFramework(
            framework_type="PICO",
            population="Adults",
            intervention="Drug X",
            comparator=None,
            outcome=None,
        )
        result = validate_framework(fw)
        assert 0 < result.completeness_score < 100


# ──────────────────────────────────────────────
# 8. Research question generation
# ──────────────────────────────────────────────

class TestResearchQuestionGeneration:
    def test_complete_framework_generates_question(self):
        p = _pico_project()
        result = build_research_question(p)
        assert result.draft_question is not None
        assert len(result.draft_question) > 20

    def test_draft_question_contains_population(self):
        p = _pico_project()
        result = build_research_question(p)
        assert result.draft_question is not None
        assert "Adults with type 2 diabetes" in result.draft_question

    def test_draft_question_contains_comparator(self):
        p = _pico_project()
        result = build_research_question(p)
        assert "Placebo" in result.draft_question

    def test_peco_complete_generates_question(self):
        p = _peco_project()
        result = build_research_question(p)
        assert result.status == FrameworkCompleteness.COMPLETE
        assert result.draft_question is not None

    def test_time_frame_included_in_question_when_present(self):
        fw = ResearchFramework(
            framework_type="PICO",
            population="Adults with T2DM",
            intervention="Metformin",
            comparator="Placebo",
            outcome="All-cause mortality",
            time_frame="5 years",
        )
        result = validate_framework(fw)
        assert result.draft_question is not None
        assert "5 years" in result.draft_question

    def test_incomplete_project_returns_no_question(self):
        """Point 6: draft question must NOT be generated for incomplete framework."""
        p = _project(idea="Some vague research idea without structured content or population")
        result = build_research_question(p)
        assert result.draft_question is None


# ──────────────────────────────────────────────
# 9. Refusal to invent missing information
# ──────────────────────────────────────────────

class TestNoInventedInformation:
    def test_missing_comparator_not_invented(self):
        p = _pico_project()
        p.comparator = None
        fw = build_framework(p)
        assert fw.comparator is None

    def test_missing_comparator_not_extracted_from_text(self):
        """Point 5: comparator mentioned in free text must not be invented."""
        p = _project(
            idea="Comparing metformin versus placebo in adults with type 2 diabetes"
        )
        fw = build_framework(p)
        assert fw.comparator is None

    def test_incomplete_result_has_no_draft_question(self):
        fw = ResearchFramework(framework_type="PICO")
        result = validate_framework(fw)
        assert result.draft_question is None

    def test_needs_clarification_returns_missing_list(self):
        fw = ResearchFramework(
            framework_type="PICO",
            population="Adults",
            intervention="Drug X",
            comparator=None,
            outcome=None,
        )
        result = validate_framework(fw)
        assert len(result.missing_fields) > 0
        assert result.draft_question is None

    def test_confidence_notes_mention_missing(self):
        p = _project(idea="Effect of some treatment on some outcome in some study population")
        p.comparator = None
        fw = build_framework(p)
        assert fw.confidence_notes is not None
        assert "comparator" in fw.confidence_notes.lower() or "missing" in fw.confidence_notes.lower()

    def test_empty_idea_project_framework_safe(self):
        """Point 14: borderline idea must fail safely."""
        p = _project(idea="Vague research idea without clear elements provided")
        fw = build_framework(p)
        result = validate_framework(fw)
        assert result.draft_question is None
        assert result.status in (FrameworkCompleteness.INCOMPLETE, FrameworkCompleteness.NEEDS_CLARIFICATION)


# ──────────────────────────────────────────────
# 10. Study design recommendation
# ──────────────────────────────────────────────

class TestStudyDesignRecommendation:
    def test_pico_recommends_rct(self):
        fw = ResearchFramework(
            framework_type="PICO",
            population="Adults",
            intervention="Drug X",
            comparator="Placebo",
            outcome="Mortality",
        )
        rec = recommend_study_design(fw)
        assert rec.recommended_design == StudyDesignType.RCT

    def test_peco_recommends_cohort(self):
        fw = ResearchFramework(
            framework_type="PECO",
            population="Adults",
            exposure="Smoking",
            comparator="Non-smokers",
            outcome="Lung cancer",
        )
        rec = recommend_study_design(fw)
        assert rec.recommended_design == StudyDesignType.COHORT

    def test_recommendation_always_needs_expert_review(self):
        """Point 9: needs_expert_review must always be True."""
        fw = ResearchFramework(framework_type="PICO")
        rec = recommend_study_design(fw)
        assert rec.needs_expert_review is True

    def test_peco_recommendation_always_needs_expert_review(self):
        fw = ResearchFramework(framework_type="PECO")
        rec = recommend_study_design(fw)
        assert rec.needs_expert_review is True

    def test_pico_has_alternative_designs(self):
        fw = ResearchFramework(framework_type="PICO")
        rec = recommend_study_design(fw)
        assert len(rec.alternative_designs) > 0

    def test_peco_has_alternative_designs(self):
        fw = ResearchFramework(framework_type="PECO")
        rec = recommend_study_design(fw)
        assert len(rec.alternative_designs) > 0

    def test_recommendation_has_rationale(self):
        fw = ResearchFramework(framework_type="PICO")
        rec = recommend_study_design(fw)
        assert rec.rationale and len(rec.rationale) > 10

    def test_recommendation_has_limitations(self):
        fw = ResearchFramework(framework_type="PICO")
        rec = recommend_study_design(fw)
        assert len(rec.limitations) > 0

    def test_recommendation_presented_as_suggestion(self):
        """Point 8: rationale must not claim definitive correctness."""
        for ft in ["PICO", "PECO"]:
            fw = ResearchFramework(framework_type=ft)
            rec = recommend_study_design(fw)
            assert rec.needs_expert_review is True
            forbidden = ["proven", "definitively correct", "guarantees", "will work", "is effective"]
            full_text = rec.rationale.lower()
            for term in forbidden:
                assert term not in full_text, f"Forbidden term '{term}' in rationale"

    def test_limitations_mention_expert_review(self):
        fw = ResearchFramework(framework_type="PICO")
        rec = recommend_study_design(fw)
        full_limitations = " ".join(rec.limitations).lower()
        assert "researcher" in full_limitations or "statistician" in full_limitations or "expert" in full_limitations


# ──────────────────────────────────────────────
# 11. Task generation for missing framework fields
# ──────────────────────────────────────────────

class TestFrameworkTaskGeneration:
    def test_generates_tasks_for_missing_fields(self):
        p = _project()
        fw = ResearchFramework(
            framework_type="PICO",
            population=None,
            intervention=None,
            comparator=None,
            outcome=None,
        )
        tasks = generate_framework_tasks(p, fw)
        assert len(tasks) > 0

    def test_generates_comparator_task_when_missing(self):
        p = _pico_project()
        p.comparator = None
        fw = build_framework(p)
        tasks = generate_framework_tasks(p, fw)
        titles = [t.title for t in tasks]
        assert any("comparator" in t.lower() for t in titles)

    def test_no_duplicate_tasks_generated(self):
        """Point 11: second call must not create duplicates."""
        p = _pico_project()
        p.comparator = None
        fw = build_framework(p)
        tasks1 = generate_framework_tasks(p, fw)
        for t in tasks1:
            p.tasks.append(t)
        tasks2 = generate_framework_tasks(p, fw)
        titles1 = {t.title for t in tasks1}
        titles2 = {t.title for t in tasks2}
        assert titles1.isdisjoint(titles2)

    def test_no_duplicate_tasks_on_repeated_calls(self):
        """Regression: three repeated refinement calls must not accumulate duplicates."""
        p = _project()
        fw = ResearchFramework(
            framework_type="PICO",
            population=None,
            intervention=None,
            comparator=None,
            outcome=None,
        )
        for _ in range(3):
            new_tasks = generate_framework_tasks(p, fw)
            for t in new_tasks:
                p.tasks.append(t)

        titles = [t.title for t in p.tasks]
        assert len(titles) == len(set(titles)), "Duplicate task titles found after repeated calls"

    def test_complete_framework_generates_no_tasks(self):
        p = _pico_project()
        fw = build_framework(p)
        tasks = generate_framework_tasks(p, fw)
        assert len(tasks) == 0

    def test_generated_tasks_use_research_task_model(self):
        from core.models import ResearchTask
        p = _project()
        fw = ResearchFramework(
            framework_type="PICO",
            population=None,
            intervention=None,
            comparator=None,
            outcome=None,
        )
        tasks = generate_framework_tasks(p, fw)
        for task in tasks:
            assert isinstance(task, ResearchTask)
            assert task.status == TaskStatus.TODO

    def test_generated_tasks_have_no_dependencies(self):
        """Point 10: tasks must use existing ResearchTask architecture."""
        p = _project()
        fw = ResearchFramework(
            framework_type="PICO",
            population=None,
            intervention=None,
            comparator=None,
            outcome=None,
        )
        tasks = generate_framework_tasks(p, fw)
        for task in tasks:
            assert task.dependencies == []

    def test_generated_tasks_completable_via_task_engine(self):
        """Point 10: generated tasks must be completable through existing task engine."""
        from core.task_engine import can_complete_task, complete_task
        p = _project()
        fw = ResearchFramework(
            framework_type="PICO",
            population=None,
            intervention=None,
            comparator=None,
            outcome=None,
        )
        tasks = generate_framework_tasks(p, fw)
        for t in tasks:
            p.tasks.append(t)
        for task in p.tasks:
            assert can_complete_task(p, task.id) is True
            complete_task(p, task.id)
            assert task.status == TaskStatus.COMPLETED


# ──────────────────────────────────────────────
# 12. Serialization roundtrip with ResearchFramework
# ──────────────────────────────────────────────

class TestResearchFrameworkSerialization:
    def test_framework_serializes_to_json(self):
        fw = ResearchFramework(
            framework_type="PICO",
            population="Adults with T2DM",
            intervention="Metformin",
            comparator="Placebo",
            outcome="All-cause mortality at 5 years",
            time_frame="5 years",
        )
        json_str = fw.model_dump_json()
        assert "PICO" in json_str
        assert "Metformin" in json_str

    def test_framework_roundtrip(self):
        fw = ResearchFramework(
            framework_type="PECO",
            population="Adults aged 40-70",
            exposure="Smoking",
            comparator="Never-smokers",
            outcome="Lung cancer incidence",
        )
        json_str = fw.model_dump_json()
        restored = ResearchFramework.model_validate_json(json_str)
        assert restored.framework_type == "PECO"
        assert restored.exposure == fw.exposure
        assert restored.population == fw.population

    def test_project_with_framework_roundtrip(self):
        """Point 2: ResearchProject → ResearchState → JSON → ResearchProject."""
        p = _pico_project()
        p.research_framework = build_framework(p)
        json_str = p.model_dump_json()
        restored = ResearchProject.model_validate_json(json_str)
        assert restored.research_framework is not None
        assert restored.research_framework.framework_type == "PICO"

    def test_research_state_wrapper_with_framework(self):
        p = _pico_project()
        p.research_framework = build_framework(p)
        state = ResearchState(project=p)
        json_str = state.model_dump_json()
        restored = ResearchState.model_validate_json(json_str)
        assert restored.project.research_framework is not None
        assert restored.project.research_framework.intervention == "Metformin 1000mg twice daily"

    def test_framework_missing_fields_preserved_after_roundtrip(self):
        fw = ResearchFramework(
            framework_type="PICO",
            population="Adults",
            intervention=None,
            comparator=None,
            outcome=None,
        )
        json_str = fw.model_dump_json()
        restored = ResearchFramework.model_validate_json(json_str)
        assert restored.intervention is None
        assert restored.comparator is None
        assert "intervention" in restored.missing_fields()

    def test_sprint1_project_without_framework_loads_successfully(self):
        """Point 12: backward compatibility — Sprint 1 JSON without research_framework."""
        import json
        sprint1_dict = {
            "id": "abc-123",
            "title": "Sprint 1 Legacy Project",
            "idea": "A legacy research idea from sprint one without a framework field",
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T00:00:00",
            "state": "IDEA",
            "tasks": [],
            "secondary_outcomes": [],
            "inclusion_criteria": {"criteria": []},
            "exclusion_criteria": {"criteria": []},
        }
        json_str = json.dumps(sprint1_dict)
        project = ResearchProject.model_validate_json(json_str)
        assert project.title == "Sprint 1 Legacy Project"
        assert project.research_framework is None

    def test_sprint1_state_wrapper_without_framework_loads(self):
        """Point 12: full ResearchState backward compat."""
        import json
        sprint1_state = {
            "schema_version": "1.0.0",
            "saved_at": "2024-01-01T00:00:00",
            "project": {
                "id": "abc-456",
                "title": "Legacy State Project",
                "idea": "A legacy idea from sprint one stored in research state wrapper",
                "created_at": "2024-01-01T00:00:00",
                "updated_at": "2024-01-01T00:00:00",
                "state": "IDEA",
                "tasks": [],
                "secondary_outcomes": [],
                "inclusion_criteria": {"criteria": []},
                "exclusion_criteria": {"criteria": []},
            },
        }
        json_str = json.dumps(sprint1_state)
        state = ResearchState.model_validate_json(json_str)
        assert state.project is not None
        assert state.project.research_framework is None
        assert state.project.title == "Legacy State Project"


# ──────────────────────────────────────────────
# 13. State gate integration
# ──────────────────────────────────────────────

class TestStateGateIntegration:
    def test_check_question_defined_ready_fails_without_framework(self):
        p = _project()
        ready, reasons = check_question_defined_ready(p)
        assert ready is False
        assert len(reasons) > 0

    def test_check_question_defined_ready_fails_with_incomplete_framework(self):
        """Point 7: IDEA → QUESTION_DEFINED fails with incomplete framework."""
        p = _pico_project()
        p.comparator = None
        p.research_framework = build_framework(p)
        ready, reasons = check_question_defined_ready(p)
        assert ready is False

    def test_check_question_defined_ready_fails_without_research_question(self):
        p = _pico_project()
        p.research_framework = build_framework(p)
        p.research_question = None
        ready, reasons = check_question_defined_ready(p)
        assert ready is False

    def test_check_question_defined_ready_passes_with_all_required(self):
        p = _pico_project()
        p.research_framework = build_framework(p)
        p.research_question = ResearchQuestion(
            question_text="Does metformin reduce cardiovascular mortality in adults with T2DM?"
        )
        ready, reasons = check_question_defined_ready(p)
        assert ready is True
        assert reasons == []

    def test_check_design_selected_ready_fails_without_design(self):
        """Point 7: QUESTION_DEFINED → DESIGN_SELECTED fails without design."""
        p = _project()
        ready, reasons = check_design_selected_ready(p)
        assert ready is False

    def test_check_design_selected_ready_passes_with_design(self):
        p = _project()
        p.study_design = StudyDesign(design_type=StudyDesignType.RCT)
        ready, reasons = check_design_selected_ready(p)
        assert ready is True

    def test_gated_transition_idea_to_question_blocked_without_framework(self):
        from core.models import ResearchStateEnum
        p = _project()
        with pytest.raises(StateGateError):
            transition_state_gated(ResearchStateEnum.IDEA, ResearchStateEnum.QUESTION_DEFINED, p)

    def test_gated_transition_idea_to_question_allowed_when_ready(self):
        from core.models import ResearchStateEnum
        p = _pico_project()
        p.research_framework = build_framework(p)
        p.research_question = ResearchQuestion(
            question_text="Does metformin reduce cardiovascular mortality in adults with T2DM?"
        )
        result = transition_state_gated(
            ResearchStateEnum.IDEA, ResearchStateEnum.QUESTION_DEFINED, p
        )
        assert result == ResearchStateEnum.QUESTION_DEFINED

    def test_gated_transition_still_rejects_invalid_structural_transitions(self):
        from core.models import ResearchStateEnum
        p = _pico_project()
        with pytest.raises(InvalidStateTransitionError):
            transition_state_gated(
                ResearchStateEnum.IDEA, ResearchStateEnum.READY_FOR_SUBMISSION, p
            )

    def test_ungated_transition_still_works(self):
        """Backward compat: ungated transition_state unchanged."""
        from core.models import ResearchStateEnum
        result = transition_state(ResearchStateEnum.IDEA, ResearchStateEnum.QUESTION_DEFINED)
        assert result == ResearchStateEnum.QUESTION_DEFINED


# ──────────────────────────────────────────────
# 14. Research objectives generation
# ──────────────────────────────────────────────

class TestResearchObjectives:
    def test_generates_objectives_from_complete_project(self):
        p = _pico_project()
        p.research_framework = build_framework(p)
        objectives = generate_research_objectives(p)
        assert len(objectives) > 0
        assert "Insufficient" not in objectives[0]

    def test_insufficient_info_returns_guidance_message(self):
        p = _project(idea="Vague research idea with no structured content provided at all")
        objectives = generate_research_objectives(p)
        assert len(objectives) > 0
        assert any(
            "Insufficient" in obj or "complete" in obj.lower() for obj in objectives
        )

    def test_objectives_do_not_invent_content(self):
        p = _pico_project()
        p.research_framework = build_framework(p)
        objectives = generate_research_objectives(p)
        full_text = " ".join(objectives).lower()
        assert "p < 0.05" not in full_text
        assert "statistically significant" not in full_text


# ──────────────────────────────────────────────
# 15. ResearchFramework model validation
# ──────────────────────────────────────────────

class TestResearchFrameworkModel:
    def test_pico_required_fields(self):
        fw = ResearchFramework(framework_type="PICO")
        required = fw.required_fields()
        assert "population" in required
        assert "intervention" in required
        assert "comparator" in required
        assert "outcome" in required
        assert "exposure" not in required

    def test_peco_required_fields(self):
        fw = ResearchFramework(framework_type="PECO")
        required = fw.required_fields()
        assert "population" in required
        assert "exposure" in required
        assert "comparator" in required
        assert "outcome" in required
        assert "intervention" not in required

    def test_invalid_framework_type_rejected(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            ResearchFramework(framework_type="INVALID")

    def test_time_frame_optional_does_not_block_completeness(self):
        fw = ResearchFramework(
            framework_type="PICO",
            population="Adults",
            intervention="Drug X",
            comparator="Placebo",
            outcome="Mortality",
            time_frame=None,
        )
        assert fw.is_complete() is True

    def test_warnings_issued_for_missing_time_frame(self):
        fw = ResearchFramework(
            framework_type="PICO",
            population="Adults",
            intervention="Drug X",
            comparator="Placebo",
            outcome="Mortality",
        )
        result = validate_framework(fw)
        assert len(result.warnings) > 0
