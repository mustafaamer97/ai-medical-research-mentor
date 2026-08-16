"""
Tests for the project domain service layer.

Tests target create_project(), update_project(), and touch().
"""

import time
import pytest
from datetime import datetime, timezone
from pydantic import ValidationError

from research_copilot.core.enums import ProjectState, StudyDesignType
from research_copilot.core.models import (
    ResearchProject,
    ResearchQuestion,
    StudyDesign,
)
from research_copilot.core.project import create_project, touch, update_project


# ===========================================================================
# create_project
# ===========================================================================

class TestCreateProject:

    def test_creates_valid_project(self):
        project = create_project(
            title="Exercise and Blood Pressure",
            idea="Investigate whether structured exercise reduces blood pressure in adults.",
        )
        assert isinstance(project, ResearchProject)

    def test_created_project_has_id(self):
        project = create_project(
            title="Exercise Study",
            idea="Investigate whether structured exercise reduces blood pressure in adults.",
        )
        assert project.id is not None
        assert isinstance(project.id, str)
        assert len(project.id) > 0

    def test_created_project_ids_are_unique(self):
        p1 = create_project(
            title="Project One",
            idea="Investigate whether structured exercise reduces blood pressure in adults.",
        )
        p2 = create_project(
            title="Project Two",
            idea="Investigate whether structured exercise reduces blood pressure in adults.",
        )
        assert p1.id != p2.id

    def test_created_project_has_created_at(self):
        project = create_project(
            title="Exercise Study",
            idea="Investigate whether structured exercise reduces blood pressure in adults.",
        )
        assert isinstance(project.created_at, datetime)
        assert project.created_at.tzinfo is not None

    def test_created_project_has_updated_at(self):
        project = create_project(
            title="Exercise Study",
            idea="Investigate whether structured exercise reduces blood pressure in adults.",
        )
        assert isinstance(project.updated_at, datetime)

    def test_created_project_default_state_is_idea(self):
        project = create_project(
            title="Exercise Study",
            idea="Investigate whether structured exercise reduces blood pressure in adults.",
        )
        assert project.state == ProjectState.IDEA

    def test_short_title_raises(self):
        with pytest.raises(ValidationError):
            create_project(
                title="Hi",
                idea="Investigate whether structured exercise reduces blood pressure in adults.",
            )

    def test_short_idea_raises(self):
        with pytest.raises(ValidationError):
            create_project(
                title="Exercise Study",
                idea="Too short.",
            )

    def test_empty_title_raises(self):
        with pytest.raises(ValidationError):
            create_project(title="", idea="A long enough idea for this project to be valid.")

    def test_empty_idea_raises(self):
        with pytest.raises(ValidationError):
            create_project(title="Valid Title", idea="")


# ===========================================================================
# update_project
# ===========================================================================

class TestUpdateProject:

    def _make_project(self) -> ResearchProject:
        return create_project(
            title="Exercise Study",
            idea="Investigate whether structured exercise reduces blood pressure in adults.",
        )

    def test_update_title(self):
        project = self._make_project()
        updated = update_project(project, {"title": "Updated Exercise Study"})
        assert updated.title == "Updated Exercise Study"

    def test_update_changes_updated_at(self):
        project = self._make_project()
        before = project.updated_at
        # Ensure measurable time delta
        time.sleep(0.01)
        update_project(project, {"title": "New Title For Exercise Study"})
        assert project.updated_at > before

    def test_update_does_not_change_created_at(self):
        project = self._make_project()
        original_created_at = project.created_at
        update_project(project, {"title": "New Title For Exercise Study"})
        assert project.created_at == original_created_at

    def test_update_does_not_change_id(self):
        project = self._make_project()
        original_id = project.id
        update_project(project, {"title": "New Title For Exercise Study"})
        assert project.id == original_id

    def test_update_id_raises(self):
        project = self._make_project()
        with pytest.raises(ValueError) as exc_info:
            update_project(project, {"id": "some-new-id"})
        assert "protected" in str(exc_info.value)

    def test_update_created_at_raises(self):
        project = self._make_project()
        with pytest.raises(ValueError) as exc_info:
            update_project(project, {"created_at": datetime.now(timezone.utc)})
        assert "protected" in str(exc_info.value)

    def test_update_returns_same_project_instance(self):
        project = self._make_project()
        returned = update_project(project, {"title": "New Title For Exercise Study"})
        assert returned is project

    def test_update_state(self):
        project = self._make_project()
        update_project(project, {"state": ProjectState.QUESTION_DEFINED})
        assert project.state == ProjectState.QUESTION_DEFINED

    def test_update_nested_research_question(self):
        project = self._make_project()
        rq = ResearchQuestion(
            question_text="Does aerobic exercise reduce blood pressure in hypertensive adults?"
        )
        update_project(project, {"research_question": rq})
        assert project.research_question is not None
        assert "aerobic exercise" in project.research_question.question_text

    def test_update_nested_study_design(self):
        project = self._make_project()
        sd = StudyDesign(design_type=StudyDesignType.COHORT)
        update_project(project, {"study_design": sd})
        assert project.study_design.design_type == StudyDesignType.COHORT

    def test_update_with_invalid_value_raises(self):
        project = self._make_project()
        with pytest.raises((ValidationError, ValueError)):
            update_project(project, {"state": "NOT_A_REAL_STATE"})

    def test_multiple_fields_updated_simultaneously(self):
        project = self._make_project()
        update_project(
            project,
            {
                "title": "Updated Title For Exercise Study",
                "state": ProjectState.DESIGN_SELECTED,
            },
        )
        assert project.title == "Updated Title For Exercise Study"
        assert project.state == ProjectState.DESIGN_SELECTED


# ===========================================================================
# touch
# ===========================================================================

class TestTouch:

    def test_touch_updates_updated_at(self):
        project = create_project(
            title="Exercise Study",
            idea="Investigate whether structured exercise reduces blood pressure in adults.",
        )
        before = project.updated_at
        time.sleep(0.01)
        touch(project)
        assert project.updated_at > before

    def test_touch_does_not_change_title(self):
        project = create_project(
            title="Exercise Study",
            idea="Investigate whether structured exercise reduces blood pressure in adults.",
        )
        original_title = project.title
        touch(project)
        assert project.title == original_title

    def test_touch_does_not_change_id(self):
        project = create_project(
            title="Exercise Study",
            idea="Investigate whether structured exercise reduces blood pressure in adults.",
        )
        original_id = project.id
        touch(project)
        assert project.id == original_id

    def test_touch_does_not_change_created_at(self):
        project = create_project(
            title="Exercise Study",
            idea="Investigate whether structured exercise reduces blood pressure in adults.",
        )
        original_created_at = project.created_at
        touch(project)
        assert project.created_at == original_created_at

    def test_touch_returns_same_instance(self):
        project = create_project(
            title="Exercise Study",
            idea="Investigate whether structured exercise reduces blood pressure in adults.",
        )
        returned = touch(project)
        assert returned is project
