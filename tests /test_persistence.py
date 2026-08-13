from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from core.models import (
    Comparator,
    Exposure,
    InclusionCriteria,
    Outcome,
    Population,
    ResearchProject,
    ResearchQuestion,
    ResearchStateEnum,
    StudyDesign,
    StudyDesignType,
)
from core.persistence import clear_project, load_project, save_project
from core.task_engine import generate_initial_tasks


def _tmp_path() -> Path:
    d = tempfile.mkdtemp()
    return Path(d) / "test_project.json"


def _make_project() -> ResearchProject:
    p = ResearchProject(
        title="Persistence Test Project",
        idea="Testing persistence layer with complete project data",
    )
    generate_initial_tasks(p)
    return p


class TestSaveLoad:
    def test_save_and_load_returns_same_title(self):
        path = _tmp_path()
        p = _make_project()
        save_project(p, path)
        loaded = load_project(path)
        assert loaded is not None
        assert loaded.title == p.title

    def test_save_and_load_returns_same_id(self):
        path = _tmp_path()
        p = _make_project()
        save_project(p, path)
        loaded = load_project(path)
        assert loaded.id == p.id

    def test_save_and_load_preserves_state(self):
        path = _tmp_path()
        p = _make_project()
        p.state = ResearchStateEnum.QUESTION_DEFINED
        save_project(p, path)
        loaded = load_project(path)
        assert loaded.state == ResearchStateEnum.QUESTION_DEFINED

    def test_save_and_load_preserves_tasks(self):
        path = _tmp_path()
        p = _make_project()
        save_project(p, path)
        loaded = load_project(path)
        assert len(loaded.tasks) == len(p.tasks)

    def test_save_and_load_preserves_task_ids(self):
        path = _tmp_path()
        p = _make_project()
        original_ids = {t.id for t in p.tasks}
        save_project(p, path)
        loaded = load_project(path)
        loaded_ids = {t.id for t in loaded.tasks}
        assert original_ids == loaded_ids

    def test_save_and_load_preserves_research_question(self):
        path = _tmp_path()
        p = _make_project()
        p.research_question = ResearchQuestion(
            question_text="Does treatment X reduce outcome Y in patients?"
        )
        save_project(p, path)
        loaded = load_project(path)
        assert loaded.research_question is not None
        assert loaded.research_question.question_text == p.research_question.question_text

    def test_save_and_load_preserves_population(self):
        path = _tmp_path()
        p = _make_project()
        p.population = Population(
            description="Adults aged 18-75 with condition Z",
            setting="Hospital outpatient",
        )
        save_project(p, path)
        loaded = load_project(path)
        assert loaded.population.description == p.population.description
        assert loaded.population.setting == p.population.setting

    def test_save_and_load_preserves_inclusion_criteria(self):
        path = _tmp_path()
        p = _make_project()
        p.inclusion_criteria = InclusionCriteria(
            criteria=["Age 18-75", "Condition Z diagnosis"]
        )
        save_project(p, path)
        loaded = load_project(path)
        assert loaded.inclusion_criteria.criteria == ["Age 18-75", "Condition Z diagnosis"]

    def test_save_and_load_preserves_study_design(self):
        path = _tmp_path()
        p = _make_project()
        p.study_design = StudyDesign(
            design_type=StudyDesignType.COHORT, rationale="Best fit"
        )
        save_project(p, path)
        loaded = load_project(path)
        assert loaded.study_design.design_type == StudyDesignType.COHORT

    def test_save_and_load_preserves_primary_outcome(self):
        path = _tmp_path()
        p = _make_project()
        p.primary_outcome = Outcome(
            name="All-cause mortality",
            description="Death from any cause during follow-up",
            is_primary=True,
        )
        save_project(p, path)
        loaded = load_project(path)
        assert loaded.primary_outcome.name == "All-cause mortality"
        assert loaded.primary_outcome.is_primary is True

    def test_load_returns_none_when_no_file(self):
        path = _tmp_path()
        result = load_project(path)
        assert result is None

    def test_load_returns_none_on_corrupt_file(self):
        path = _tmp_path()
        path.write_text("NOT VALID JSON {{{", encoding="utf-8")
        result = load_project(path)
        assert result is None

    def test_clear_removes_file(self):
        path = _tmp_path()
        p = _make_project()
        save_project(p, path)
        assert path.exists()
        clear_project(path)
        assert not path.exists()

    def test_clear_on_nonexistent_file_is_safe(self):
        path = _tmp_path()
        clear_project(path)  # should not raise

    def test_overwrite_project(self):
        path = _tmp_path()
        p1 = _make_project()
        save_project(p1, path)
        p2 = ResearchProject(
            title="Second Project Overwrite",
            idea="This completely replaces the first project in storage",
        )
        save_project(p2, path)
        loaded = load_project(path)
        assert loaded.title == "Second Project Overwrite"
        assert loaded.id == p2.id
