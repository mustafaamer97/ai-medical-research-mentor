"""
Tests for the canonical domain models.

All tests target the NEW Sprint 1 architecture exclusively.
No legacy field names (status, framework, ProjectStatus, etc.) appear here.
"""

import pytest
from datetime import datetime, timezone
from pydantic import ValidationError

from research_copilot.core.enums import (
    ProjectState,
    StudyDesignType,
    TaskPriority,
    TaskStatus,
)
from research_copilot.core.models import (
    AnalysisPlan,
    Comparator,
    ExclusionCriteria,
    Exposure,
    InclusionCriteria,
    Intervention,
    Outcome,
    Population,
    ResearchProject,
    ResearchQuestion,
    ResearchTask,
    SampleSizePlan,
    StudyDesign,
)


# ===========================================================================
# ResearchQuestion
# ===========================================================================

class TestResearchQuestion:

    def test_valid_question(self):
        q = ResearchQuestion(question_text="Does exercise reduce blood pressure in adults?")
        assert q.question_text == "Does exercise reduce blood pressure in adults?"
        assert q.background is None

    def test_valid_question_with_background(self):
        q = ResearchQuestion(
            question_text="Does exercise reduce blood pressure in adults?",
            background="Hypertension is a major risk factor for cardiovascular disease.",
        )
        assert q.background == "Hypertension is a major risk factor for cardiovascular disease."

    def test_empty_question_raises(self):
        with pytest.raises(ValidationError) as exc_info:
            ResearchQuestion(question_text="")
        assert "must not be empty" in str(exc_info.value)

    def test_whitespace_only_question_raises(self):
        with pytest.raises(ValidationError):
            ResearchQuestion(question_text="   ")

    def test_too_short_question_raises(self):
        with pytest.raises(ValidationError) as exc_info:
            ResearchQuestion(question_text="Why?")
        assert "too short" in str(exc_info.value)

    def test_question_text_is_stripped(self):
        q = ResearchQuestion(question_text="  Does exercise help?  ")
        assert q.question_text == "Does exercise help?"

    def test_minimum_length_boundary(self):
        # Exactly 10 characters after strip should pass
        q = ResearchQuestion(question_text="1234567890")
        assert len(q.question_text) == 10

    def test_one_below_minimum_length_raises(self):
        with pytest.raises(ValidationError):
            ResearchQuestion(question_text="123456789")  # 9 chars


# ===========================================================================
# StudyDesign
# ===========================================================================

class TestStudyDesign:

    @pytest.mark.parametrize("design_type", list(StudyDesignType))
    def test_all_design_types_valid(self, design_type):
        sd = StudyDesign(design_type=design_type)
        assert sd.design_type == design_type

    def test_cross_sectional(self):
        sd = StudyDesign(design_type=StudyDesignType.CROSS_SECTIONAL)
        assert sd.design_type == StudyDesignType.CROSS_SECTIONAL

    def test_rct(self):
        sd = StudyDesign(design_type=StudyDesignType.RANDOMIZED_CONTROLLED_TRIAL)
        assert sd.design_type == StudyDesignType.RANDOMIZED_CONTROLLED_TRIAL

    def test_with_rationale(self):
        sd = StudyDesign(
            design_type=StudyDesignType.COHORT,
            rationale="Prospective follow-up required to establish temporality.",
        )
        assert sd.rationale is not None

    def test_invalid_design_type_raises(self):
        with pytest.raises(ValidationError):
            StudyDesign(design_type="MADE_UP_DESIGN")


# ===========================================================================
# Population
# ===========================================================================

class TestPopulation:

    def test_valid_population(self):
        p = Population(description="Adults aged 18-65 with hypertension")
        assert p.description == "Adults aged 18-65 with hypertension"
        assert p.setting is None

    def test_valid_with_setting(self):
        p = Population(
            description="Adults aged 18-65 with hypertension",
            setting="Primary care clinics in urban areas",
        )
        assert p.setting == "Primary care clinics in urban areas"

    def test_empty_description_raises(self):
        with pytest.raises(ValidationError) as exc_info:
            Population(description="")
        assert "must not be empty" in str(exc_info.value)

    def test_whitespace_description_raises(self):
        with pytest.raises(ValidationError):
            Population(description="   ")

    def test_description_is_stripped(self):
        p = Population(description="  Adults aged 18-65  ")
        assert p.description == "Adults aged 18-65"


# ===========================================================================
# Exposure
# ===========================================================================

class TestExposure:

    def test_valid_exposure(self):
        e = Exposure(description="Regular aerobic exercise (≥150 min/week)")
        assert e.description == "Regular aerobic exercise (≥150 min/week)"
        assert e.measurement_method is None

    def test_valid_with_measurement_method(self):
        e = Exposure(
            description="Regular aerobic exercise",
            measurement_method="Self-reported weekly minutes via validated questionnaire",
        )
        assert e.measurement_method is not None

    def test_empty_description_raises(self):
        with pytest.raises(ValidationError):
            Exposure(description="")

    def test_whitespace_description_raises(self):
        with pytest.raises(ValidationError):
            Exposure(description="  ")


# ===========================================================================
# Intervention
# ===========================================================================

class TestIntervention:

    def test_valid_intervention(self):
        i = Intervention(description="Structured 12-week aerobic exercise programme")
        assert i.description == "Structured 12-week aerobic exercise programme"
        assert i.dosage_or_protocol is None

    def test_valid_with_protocol(self):
        i = Intervention(
            description="Structured aerobic exercise",
            dosage_or_protocol="3 sessions/week, 45 minutes each, 70% VO2 max",
        )
        assert i.dosage_or_protocol is not None

    def test_empty_description_raises(self):
        with pytest.raises(ValidationError):
            Intervention(description="")

    def test_description_is_stripped(self):
        i = Intervention(description="  Aerobic exercise programme  ")
        assert i.description == "Aerobic exercise programme"


# ===========================================================================
# Comparator
# ===========================================================================

class TestComparator:

    def test_valid_comparator(self):
        c = Comparator(description="Usual care with no structured exercise")
        assert c.description == "Usual care with no structured exercise"

    def test_empty_description_raises(self):
        with pytest.raises(ValidationError):
            Comparator(description="")

    def test_whitespace_description_raises(self):
        with pytest.raises(ValidationError):
            Comparator(description="   ")


# ===========================================================================
# Outcome
# ===========================================================================

class TestOutcome:

    def test_valid_primary_outcome(self):
        o = Outcome(
            name="Systolic blood pressure",
            description="Systolic blood pressure measured in mmHg at 12 weeks",
            is_primary=True,
        )
        assert o.is_primary is True
        assert o.name == "Systolic blood pressure"

    def test_valid_secondary_outcome(self):
        o = Outcome(
            name="Diastolic blood pressure",
            description="Diastolic blood pressure measured in mmHg at 12 weeks",
            is_primary=False,
        )
        assert o.is_primary is False

    def test_default_is_not_primary(self):
        o = Outcome(
            name="Heart rate",
            description="Resting heart rate in beats per minute",
        )
        assert o.is_primary is False

    def test_with_optional_fields(self):
        o = Outcome(
            name="Quality of life",
            description="Patient-reported quality of life score",
            measurement_method="SF-36 questionnaire",
            time_point="6 months",
            is_primary=False,
        )
        assert o.measurement_method == "SF-36 questionnaire"
        assert o.time_point == "6 months"

    def test_empty_name_raises(self):
        with pytest.raises(ValidationError):
            Outcome(name="", description="Some description")

    def test_empty_description_raises(self):
        with pytest.raises(ValidationError):
            Outcome(name="Outcome name", description="")

    def test_name_is_stripped(self):
        o = Outcome(name="  SBP  ", description="Systolic blood pressure")
        assert o.name == "SBP"


# ===========================================================================
# InclusionCriteria
# ===========================================================================

class TestInclusionCriteria:

    def test_valid_criteria(self):
        ic = InclusionCriteria(criteria=["Adults aged 18+", "Diagnosed with hypertension"])
        assert len(ic.criteria) == 2

    def test_empty_list(self):
        ic = InclusionCriteria(criteria=[])
        assert ic.criteria == []

    def test_default_empty(self):
        ic = InclusionCriteria()
        assert ic.criteria == []

    def test_empty_strings_removed(self):
        ic = InclusionCriteria(criteria=["Adults aged 18+", "", "Hypertension diagnosis"])
        assert len(ic.criteria) == 2
        assert "" not in ic.criteria

    def test_whitespace_strings_removed(self):
        ic = InclusionCriteria(criteria=["Adults aged 18+", "   ", "Hypertension diagnosis"])
        assert len(ic.criteria) == 2

    def test_whitespace_is_stripped(self):
        ic = InclusionCriteria(criteria=["  Adults aged 18+  "])
        assert ic.criteria[0] == "Adults aged 18+"

    def test_all_empty_strings_yields_empty_list(self):
        ic = InclusionCriteria(criteria=["", "  ", "\t"])
        assert ic.criteria == []


# ===========================================================================
# ExclusionCriteria
# ===========================================================================

class TestExclusionCriteria:

    def test_valid_criteria(self):
        ec = ExclusionCriteria(criteria=["Pregnancy", "Severe cardiac disease"])
        assert len(ec.criteria) == 2

    def test_empty_strings_removed(self):
        ec = ExclusionCriteria(criteria=["Pregnancy", "", "  "])
        assert ec.criteria == ["Pregnancy"]

    def test_default_empty(self):
        ec = ExclusionCriteria()
        assert ec.criteria == []

    def test_whitespace_stripped(self):
        ec = ExclusionCriteria(criteria=["  Severe cardiac disease  "])
        assert ec.criteria[0] == "Severe cardiac disease"


# ===========================================================================
# SampleSizePlan
# ===========================================================================

class TestSampleSizePlan:

    def test_valid_sample_size_plan(self):
        ssp = SampleSizePlan(planned_n=200, rationale="Based on 80% power for 5mmHg difference")
        assert ssp.planned_n == 200

    def test_all_none_is_valid(self):
        ssp = SampleSizePlan()
        assert ssp.planned_n is None
        assert ssp.rationale is None
        assert ssp.notes is None

    def test_negative_planned_n_raises(self):
        with pytest.raises(ValidationError) as exc_info:
            SampleSizePlan(planned_n=-1)
        assert "positive" in str(exc_info.value)

    def test_zero_planned_n_raises(self):
        with pytest.raises(ValidationError):
            SampleSizePlan(planned_n=0)

    def test_with_notes(self):
        ssp = SampleSizePlan(
            planned_n=150,
            rationale="Based on pilot data",
            notes="Includes 10% dropout allowance",
        )
        assert ssp.notes == "Includes 10% dropout allowance"


# ===========================================================================
# AnalysisPlan
# ===========================================================================

class TestAnalysisPlan:

    def test_valid_analysis_plan(self):
        ap = AnalysisPlan(
            primary_analysis_description="Linear mixed-effects model",
            secondary_analyses=["Sensitivity analysis excluding non-compliers"],
            notes="Intention-to-treat principle applied",
        )
        assert ap.primary_analysis_description == "Linear mixed-effects model"
        assert len(ap.secondary_analyses) == 1

    def test_empty_analysis_plan(self):
        ap = AnalysisPlan()
        assert ap.primary_analysis_description is None
        assert ap.secondary_analyses == []
        assert ap.notes is None

    def test_multiple_secondary_analyses(self):
        ap = AnalysisPlan(
            secondary_analyses=["Per-protocol analysis", "Subgroup by age", "Subgroup by sex"]
        )
        assert len(ap.secondary_analyses) == 3


# ===========================================================================
# ResearchTask
# ===========================================================================

class TestResearchTask:

    def test_valid_task_minimal(self):
        task = ResearchTask(title="Define research question")
        assert task.title == "Define research question"
        assert task.status == TaskStatus.TODO
        assert task.priority == TaskPriority.MEDIUM
        assert task.completed_at is None

    def test_task_has_auto_id(self):
        task = ResearchTask(title="Write protocol")
        assert task.id is not None
        assert len(task.id) > 0

    def test_task_ids_are_unique(self):
        t1 = ResearchTask(title="Task one")
        t2 = ResearchTask(title="Task two")
        assert t1.id != t2.id

    def test_task_has_created_at(self):
        task = ResearchTask(title="Write protocol")
        assert isinstance(task.created_at, datetime)
        assert task.created_at.tzinfo is not None

    def test_task_default_status_is_todo(self):
        task = ResearchTask(title="Any task")
        assert task.status == TaskStatus.TODO

    def test_task_default_priority_is_medium(self):
        task = ResearchTask(title="Any task")
        assert task.priority == TaskPriority.MEDIUM

    def test_task_completed_at_starts_none(self):
        task = ResearchTask(title="Any task")
        assert task.completed_at is None

    def test_all_task_statuses(self):
        for status in TaskStatus:
            task = ResearchTask(title="Task", status=status)
            assert task.status == status

    def test_all_task_priorities(self):
        for priority in TaskPriority:
            task = ResearchTask(title="Task", priority=priority)
            assert task.priority == priority

    def test_task_completion_timestamp(self):
        now = datetime.now(timezone.utc)
        task = ResearchTask(title="Task", status=TaskStatus.COMPLETED, completed_at=now)
        assert task.completed_at == now

    def test_task_with_dependencies(self):
        task_a = ResearchTask(title="Task A")
        task_b = ResearchTask(title="Task B", dependencies=[task_a.id])
        assert task_a.id in task_b.dependencies

    def test_empty_title_raises(self):
        with pytest.raises(ValidationError):
            ResearchTask(title="")

    def test_task_with_why(self):
        task = ResearchTask(title="Submit ethics", why="Required before recruitment can begin")
        assert task.why == "Required before recruitment can begin"


# ===========================================================================
# ResearchProject — model-level tests
# ===========================================================================

class TestResearchProjectModel:

    def test_valid_minimal_project(self):
        project = ResearchProject(
            title="Exercise and Blood Pressure",
            idea="Investigate whether structured aerobic exercise reduces blood pressure in hypertensive adults.",
        )
        assert project.title == "Exercise and Blood Pressure"
        assert project.state == ProjectState.IDEA

    def test_project_has_auto_id(self):
        project = ResearchProject(
            title="Test Project",
            idea="A long enough idea for the project to be valid in this test.",
        )
        assert project.id is not None
        assert len(project.id) > 0

    def test_project_ids_are_unique(self):
        p1 = ResearchProject(
            title="Project One",
            idea="A long enough idea for project one to be valid in this test.",
        )
        p2 = ResearchProject(
            title="Project Two",
            idea="A long enough idea for project two to be valid in this test.",
        )
        assert p1.id != p2.id

    def test_project_has_created_at(self):
        project = ResearchProject(
            title="Test Project",
            idea="A long enough idea for the project to be valid in this test.",
        )
        assert isinstance(project.created_at, datetime)
        assert project.created_at.tzinfo is not None

    def test_project_has_updated_at(self):
        project = ResearchProject(
            title="Test Project",
            idea="A long enough idea for the project to be valid in this test.",
        )
        assert isinstance(project.updated_at, datetime)

    def test_title_too_short_raises(self):
        with pytest.raises(ValidationError) as exc_info:
            ResearchProject(
                title="Hi",
                idea="A long enough idea for the project to be valid in this test.",
            )
        assert "too short" in str(exc_info.value)

    def test_title_empty_raises(self):
        with pytest.raises(ValidationError):
            ResearchProject(
                title="",
                idea="A long enough idea for the project to be valid in this test.",
            )

    def test_idea_too_short_raises(self):
        with pytest.raises(ValidationError) as exc_info:
            ResearchProject(
                title="Valid Title",
                idea="Too short.",
            )
        assert "too short" in str(exc_info.value)

    def test_idea_empty_raises(self):
        with pytest.raises(ValidationError):
            ResearchProject(
                title="Valid Title",
                idea="",
            )

    def test_default_state_is_idea(self):
        project = ResearchProject(
            title="Test Project",
            idea="A long enough idea for the project to be valid in this test.",
        )
        assert project.state == ProjectState.IDEA

    def test_all_lifecycle_states(self):
        for state in ProjectState:
            project = ResearchProject(
                title="Test Project",
                idea="A long enough idea for the project to be valid in this test.",
                state=state,
            )
            assert project.state == state

    def test_no_status_field(self):
        """Confirm there is no competing `status` field."""
        project = ResearchProject(
            title="Test Project",
            idea="A long enough idea for the project to be valid in this test.",
        )
        assert not hasattr(project, "status")

    def test_research_question_defaults_to_none(self):
        project = ResearchProject(
            title="Test Project",
            idea="A long enough idea for the project to be valid in this test.",
        )
        assert project.research_question is None

    def test_nested_research_question(self):
        rq = ResearchQuestion(
            question_text="Does aerobic exercise reduce systolic blood pressure?"
        )
        project = ResearchProject(
            title="Exercise Study",
            idea="A long enough idea for the project to be valid in this test.",
            research_question=rq,
        )
        assert project.research_question.question_text == "Does aerobic exercise reduce systolic blood pressure?"

    def test_nested_study_design(self):
        project = ResearchProject(
            title="Exercise Study",
            idea="A long enough idea for the project to be valid in this test.",
            study_design=StudyDesign(design_type=StudyDesignType.RANDOMIZED_CONTROLLED_TRIAL),
        )
        assert project.study_design.design_type == StudyDesignType.RANDOMIZED_CONTROLLED_TRIAL

    def test_primary_outcome_enforces_is_primary_true(self):
        """primary_outcome must have is_primary=True."""
        with pytest.raises(ValidationError) as exc_info:
            ResearchProject(
                title="Exercise Study",
                idea="A long enough idea for the project to be valid in this test.",
                primary_outcome=Outcome(
                    name="SBP",
                    description="Systolic blood pressure",
                    is_primary=False,  # this should fail
                ),
            )
        assert "is_primary" in str(exc_info.value)

    def test_primary_outcome_with_is_primary_true(self):
        project = ResearchProject(
            title="Exercise Study",
            idea="A long enough idea for the project to be valid in this test.",
            primary_outcome=Outcome(
                name="SBP",
                description="Systolic blood pressure",
                is_primary=True,
            ),
        )
        assert project.primary_outcome.is_primary is True

    def test_secondary_outcomes_default_empty(self):
        project = ResearchProject(
            title="Test Project",
            idea="A long enough idea for the project to be valid in this test.",
        )
        assert project.secondary_outcomes == []

    def test_secondary_outcomes_independent_between_projects(self):
        """Mutable defaults must not be shared between instances."""
        p1 = ResearchProject(
            title="Project One",
            idea="A long enough idea for project one to be valid in this test.",
        )
        p2 = ResearchProject(
            title="Project Two",
            idea="A long enough idea for project two to be valid in this test.",
        )
        p1.secondary_outcomes.append(
            Outcome(name="SBP", description="Systolic blood pressure", is_primary=False)
        )
        assert len(p1.secondary_outcomes) == 1
        assert len(p2.secondary_outcomes) == 0

    def test_tasks_default_empty(self):
        project = ResearchProject(
            title="Test Project",
            idea="A long enough idea for the project to be valid in this test.",
        )
        assert project.tasks == []

    def test_tasks_independent_between_projects(self):
        """Task lists must not be shared between instances."""
        p1 = ResearchProject(
            title="Project One",
            idea="A long enough idea for project one to be valid in this test.",
        )
        p2 = ResearchProject(
            title="Project Two",
            idea="A long enough idea for project two to be valid in this test.",
        )
        p1.tasks.append(ResearchTask(title="Task for project 1"))
        assert len(p1.tasks) == 1
        assert len(p2.tasks) == 0

    def test_inclusion_criteria_default_empty(self):
        project = ResearchProject(
            title="Test Project",
            idea="A long enough idea for the project to be valid in this test.",
        )
        assert project.inclusion_criteria.criteria == []

    def test_exclusion_criteria_default_empty(self):
        project = ResearchProject(
            title="Test Project",
            idea="A long enough idea for the project to be valid in this test.",
        )
        assert project.exclusion_criteria.criteria == []

    def test_full_project_construction(self):
        """Smoke test: build a fully populated project."""
        project = ResearchProject(
            title="Exercise and Hypertension RCT",
            idea=(
                "Investigate whether a 12-week structured aerobic exercise programme "
                "reduces systolic blood pressure in adults with hypertension compared "
                "to usual care."
            ),
            state=ProjectState.PROTOCOL_READY,
            research_question=ResearchQuestion(
                question_text="Does a 12-week aerobic exercise programme reduce SBP in hypertensive adults?",
                background="Hypertension affects over 1 billion people worldwide.",
            ),
            study_design=StudyDesign(
                design_type=StudyDesignType.RANDOMIZED_CONTROLLED_TRIAL,
                rationale="RCT provides the highest level of evidence for causal inference.",
            ),
            population=Population(
                description="Adults aged 40-70 with stage 1 or 2 hypertension",
                setting="Primary care clinics",
            ),
            intervention=Intervention(
                description="12-week structured aerobic exercise programme",
                dosage_or_protocol="3 sessions/week, 45 min/session, 60-70% max HR",
            ),
            comparator=Comparator(description="Usual care with no structured exercise"),
            primary_outcome=Outcome(
                name="Systolic blood pressure",
                description="Systolic blood pressure measured in mmHg",
                measurement_method="Automated sphygmomanometer",
                time_point="12 weeks",
                is_primary=True,
            ),
            secondary_outcomes=[
                Outcome(
                    name="Diastolic blood pressure",
                    description="Diastolic blood pressure measured in mmHg",
                    time_point="12 weeks",
                    is_primary=False,
                ),
            ],
            inclusion_criteria=InclusionCriteria(
                criteria=["Aged 40-70", "Stage 1 or 2 hypertension diagnosis"]
            ),
            exclusion_criteria=ExclusionCriteria(
                criteria=["Pregnancy", "Severe cardiovascular disease"]
            ),
            sample_size_plan=SampleSizePlan(
                planned_n=200,
                rationale="80% power to detect 5 mmHg difference, SD=12",
            ),
            analysis_plan=AnalysisPlan(
                primary_analysis_description="Linear mixed-effects model, ITT",
                secondary_analyses=["Per-protocol analysis"],
            ),
            tasks=[ResearchTask(title="Submit ethics application")],
        )
        assert project.state == ProjectState.PROTOCOL_READY
        assert project.research_question is not None
        assert project.primary_outcome.is_primary is True
        assert len(project.secondary_outcomes) == 1
        assert len(project.tasks) == 1
