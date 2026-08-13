from __future__ import annotations

import pytest
from pydantic import ValidationError

from core.models import (
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
    ResearchState,
    ResearchStateEnum,
    ResearchTask,
    SampleSizePlan,
    StudyDesign,
    StudyDesignType,
    TaskPriority,
    TaskStatus,
)


class TestResearchQuestion:
    def test_valid(self):
        rq = ResearchQuestion(
            question_text="Does metformin reduce mortality in T2DM patients?"
        )
        assert rq.question_text.startswith("Does")

    def test_valid_with_background(self):
        rq = ResearchQuestion(
            question_text="Does metformin reduce mortality in T2DM patients?",
            background="T2DM is a major cause of cardiovascular mortality.",
        )
        assert rq.background is not None

    def test_invalid_too_short(self):
        with pytest.raises(ValidationError):
            ResearchQuestion(question_text="Short?")

    def test_invalid_empty(self):
        with pytest.raises(ValidationError):
            ResearchQuestion(question_text="")


class TestPopulation:
    def test_valid(self):
        p = Population(description="Adults aged 18-75 with T2DM")
        assert p.description

    def test_invalid_too_short(self):
        with pytest.raises(ValidationError):
            Population(description="X")

    def test_with_setting(self):
        p = Population(
            description="Adults aged 18-75 with T2DM",
            setting="Outpatient clinics",
        )
        assert p.setting == "Outpatient clinics"


class TestOutcome:
    def test_valid_primary(self):
        o = Outcome(
            name="All-cause mortality",
            description="Death from any cause",
            is_primary=True,
        )
        assert o.is_primary is True

    def test_valid_secondary(self):
        o = Outcome(name="CV mortality", description="Death from cardiovascular cause")
        assert o.is_primary is False

    def test_invalid_name_too_short(self):
        with pytest.raises(ValidationError):
            Outcome(name="X", description="Death from any cause")

    def test_invalid_description_too_short(self):
        with pytest.raises(ValidationError):
            Outcome(name="All-cause mortality", description="D")


class TestCriteria:
    def test_inclusion_strips_empty(self):
        ic = InclusionCriteria(criteria=["Age > 18", "", "  ", "T2DM diagnosis"])
        assert len(ic.criteria) == 2

    def test_exclusion_strips_empty(self):
        ec = ExclusionCriteria(criteria=["Pregnancy", "   "])
        assert len(ec.criteria) == 1

    def test_empty_list_allowed(self):
        ic = InclusionCriteria(criteria=[])
        assert ic.criteria == []


class TestStudyDesign:
    def test_valid_rct(self):
        sd = StudyDesign(design_type=StudyDesignType.RCT)
        assert sd.design_type == StudyDesignType.RCT

    def test_all_design_types(self):
        for dt in StudyDesignType:
            sd = StudyDesign(design_type=dt)
            assert sd.design_type == dt

    def test_invalid_design_type(self):
        with pytest.raises(ValidationError):
            StudyDesign(design_type="INVALID_DESIGN")


class TestSampleSizePlan:
    def test_valid(self):
        sp = SampleSizePlan(planned_n=200, rationale="80% power to detect HR 0.75")
        assert sp.planned_n == 200

    def test_invalid_zero_n(self):
        with pytest.raises(ValidationError):
            SampleSizePlan(planned_n=0)

    def test_invalid_negative_n(self):
        with pytest.raises(ValidationError):
            SampleSizePlan(planned_n=-50)

    def test_optional_fields(self):
        sp = SampleSizePlan()
        assert sp.planned_n is None


class TestResearchTask:
    def test_valid(self):
        t = ResearchTask(
            title="Define population",
            description="Describe the target population",
            why="Needed for a valid study",
        )
        assert t.status == TaskStatus.TODO
        assert t.priority == TaskPriority.MEDIUM
        assert t.id is not None

    def test_invalid_title_too_short(self):
        with pytest.raises(ValidationError):
            ResearchTask(
                title="AB",
                description="Valid description here",
                why="Because",
            )

    def test_default_id_is_unique(self):
        t1 = ResearchTask(
            title="Task one", description="Description one", why="Why one"
        )
        t2 = ResearchTask(
            title="Task two", description="Description two", why="Why two"
        )
        assert t1.id != t2.id

    def test_all_statuses(self):
        for s in TaskStatus:
            t = ResearchTask(
                title="Valid title",
                description="Valid description",
                why="Valid why",
                status=s,
            )
            assert t.status == s

    def test_all_priorities(self):
        for p in TaskPriority:
            t = ResearchTask(
                title="Valid title",
                description="Valid description",
                why="Valid why",
                priority=p,
            )
            assert t.priority == p


class TestResearchProject:
    def _make_project(self, **kwargs):
        defaults = {
            "title": "Test Project Alpha",
            "idea": "Investigate the effect of X on Y in population Z",
        }
        defaults.update(kwargs)
        return ResearchProject(**defaults)

    def test_valid_minimal(self):
        p = self._make_project()
        assert p.state == ResearchStateEnum.IDEA
        assert p.tasks == []

    def test_invalid_title_too_short(self):
        with pytest.raises(ValidationError):
            self._make_project(title="AB")

    def test_invalid_idea_too_short(self):
        with pytest.raises(ValidationError):
            self._make_project(idea="Short")

    def test_unique_ids(self):
        p1 = self._make_project()
        p2 = self._make_project()
        assert p1.id != p2.id

    def test_default_state_is_idea(self):
        p = self._make_project()
        assert p.state == ResearchStateEnum.IDEA

    def test_touch_updates_timestamp(self):
        import time
        p = self._make_project()
        before = p.updated_at
        time.sleep(0.02)
        p.touch()
        assert p.updated_at > before

    def test_with_full_components(self):
        p = self._make_project()
        p.research_question = ResearchQuestion(
            question_text="Does X reduce mortality in population Z?"
        )
        p.study_design = StudyDesign(design_type=StudyDesignType.COHORT)
        p.population = Population(description="Adults aged 18-65 with condition Z")
        p.primary_outcome = Outcome(
            name="All-cause mortality", description="Death from any cause"
        )
        assert p.research_question is not None
        assert p.study_design.design_type == StudyDesignType.COHORT


class TestSerialization:
    def _make_full_project(self):
        p = ResearchProject(
            title="Serialization Test Project",
            idea="This project tests complete serialization of all fields",
        )
        p.research_question = ResearchQuestion(
            question_text="Does treatment X reduce outcome Y in population Z?",
            background="Background context here.",
        )
        p.study_design = StudyDesign(
            design_type=StudyDesignType.RCT, rationale="Gold standard"
        )
        p.population = Population(
            description="Adults with condition Z aged 18-75", setting="Hospitals"
        )
        p.exposure = Exposure(
            description="Treatment X", measurement_method="Prescription records"
        )
        p.comparator = Comparator(description="Placebo")
        p.primary_outcome = Outcome(
            name="Outcome Y",
            description="Reduction in outcome Y at 12 months",
            is_primary=True,
        )
        p.secondary_outcomes = [
            Outcome(name="Secondary A", description="Secondary outcome A description")
        ]
        p.inclusion_criteria = InclusionCriteria(
            criteria=["Age 18-75", "Condition Z diagnosis"]
        )
        p.exclusion_criteria = ExclusionCriteria(
            criteria=["Pregnancy", "Severe renal impairment"]
        )
        p.sample_size_plan = SampleSizePlan(
            planned_n=500, rationale="Power calculation reference"
        )
        p.analysis_plan = AnalysisPlan(
            primary_analysis_description="Cox regression adjusted for age and sex",
            secondary_analyses=["Sensitivity analysis 1"],
        )
        p.tasks.append(
            ResearchTask(
                title="Task one",
                description="Task one description",
                why="Because it is needed",
            )
        )
        return p

    def test_serialize_to_json(self):
        p = self._make_full_project()
        json_str = p.model_dump_json()
        assert "Serialization Test Project" in json_str

    def test_deserialize_from_json(self):
        p = self._make_full_project()
        json_str = p.model_dump_json()
        restored = ResearchProject.model_validate_json(json_str)
        assert restored.title == p.title
        assert restored.idea == p.idea
        assert restored.id == p.id

    def test_roundtrip_preserves_state(self):
        p = self._make_full_project()
        p.state = ResearchStateEnum.QUESTION_DEFINED
        json_str = p.model_dump_json()
        restored = ResearchProject.model_validate_json(json_str)
        assert restored.state == ResearchStateEnum.QUESTION_DEFINED

    def test_roundtrip_preserves_tasks(self):
        p = self._make_full_project()
        json_str = p.model_dump_json()
        restored = ResearchProject.model_validate_json(json_str)
        assert len(restored.tasks) == len(p.tasks)
        assert restored.tasks[0].id == p.tasks[0].id

    def test_roundtrip_preserves_criteria(self):
        p = self._make_full_project()
        json_str = p.model_dump_json()
        restored = ResearchProject.model_validate_json(json_str)
        assert restored.inclusion_criteria.criteria == [
            "Age 18-75",
            "Condition Z diagnosis",
        ]
        assert restored.exclusion_criteria.criteria == [
            "Pregnancy",
            "Severe renal impairment",
        ]

    def test_research_state_wrapper(self):
        p = self._make_full_project()
        state = ResearchState(project=p)
        json_str = state.model_dump_json()
        restored_state = ResearchState.model_validate_json(json_str)
        assert restored_state.project is not None
        assert restored_state.project.title == p.title

    def test_research_state_empty(self):
        state = ResearchState()
        json_str = state.model_dump_json()
        restored = ResearchState.model_validate_json(json_str)
        assert restored.project is None

    def test_roundtrip_secondary_outcomes(self):
        p = self._make_full_project()
        json_str = p.model_dump_json()
        restored = ResearchProject.model_validate_json(json_str)
        assert len(restored.secondary_outcomes) == 1
        assert restored.secondary_outcomes[0].name == "Secondary A"
