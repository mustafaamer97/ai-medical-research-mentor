from __future__ import annotations

import pytest

from core.models import ResearchProject, ResearchTask, TaskPriority, TaskStatus
from core.task_engine import (
    TaskDependencyError,
    TaskNotFoundError,
    block_task,
    can_complete_task,
    check_dependencies,
    complete_task,
    create_task,
    generate_initial_tasks,
    get_completed_tasks,
    get_pending_tasks,
    start_task,
    update_task,
)


def _make_project() -> ResearchProject:
    return ResearchProject(
        title="Task Test Project",
        idea="Testing the task engine thoroughly with this research idea",
    )


class TestTaskCreation:
    def test_create_task_adds_to_project(self):
        project = _make_project()
        task = create_task(
            project, "Define population", "Describe the population", "It matters"
        )
        assert len(project.tasks) == 1
        assert task.title == "Define population"

    def test_create_task_default_status_todo(self):
        project = _make_project()
        task = create_task(
            project, "Define population", "Describe the population", "It matters"
        )
        assert task.status == TaskStatus.TODO

    def test_create_task_default_priority_medium(self):
        project = _make_project()
        task = create_task(
            project, "Define population", "Describe the population", "It matters"
        )
        assert task.priority == TaskPriority.MEDIUM

    def test_create_task_with_priority(self):
        project = _make_project()
        task = create_task(
            project,
            "Define population",
            "Describe the population",
            "It matters",
            priority=TaskPriority.CRITICAL,
        )
        assert task.priority == TaskPriority.CRITICAL

    def test_create_multiple_tasks(self):
        project = _make_project()
        create_task(project, "Task one", "Description one", "Why one")
        create_task(project, "Task two", "Description two", "Why two")
        assert len(project.tasks) == 2

    def test_create_task_with_dependency(self):
        project = _make_project()
        t1 = create_task(project, "Task one", "Description one", "Why one")
        t2 = create_task(
            project,
            "Task two",
            "Description two",
            "Why two",
            dependencies=[t1.id],
        )
        assert t1.id in t2.dependencies


class TestTaskUpdate:
    def test_update_title(self):
        project = _make_project()
        task = create_task(project, "Old title", "Description here", "Why")
        updated = update_task(project, task.id, title="New title here")
        assert updated.title == "New title here"

    def test_update_priority(self):
        project = _make_project()
        task = create_task(project, "Some task", "Description here", "Why")
        update_task(project, task.id, priority=TaskPriority.HIGH)
        assert task.priority == TaskPriority.HIGH

    def test_update_nonexistent_task_raises(self):
        project = _make_project()
        with pytest.raises(TaskNotFoundError):
            update_task(project, "nonexistent-id", title="New title")


class TestTaskCompletion:
    def test_complete_task_no_dependencies(self):
        project = _make_project()
        task = create_task(project, "Simple task", "No deps needed", "Matters")
        result = complete_task(project, task.id)
        assert result.status == TaskStatus.COMPLETED
        assert result.completed_at is not None

    def test_complete_task_with_completed_dependency(self):
        project = _make_project()
        t1 = create_task(project, "Task one", "First task description", "Why one")
        t2 = create_task(
            project,
            "Task two",
            "Second task description",
            "Why two",
            dependencies=[t1.id],
        )
        complete_task(project, t1.id)
        result = complete_task(project, t2.id)
        assert result.status == TaskStatus.COMPLETED

    def test_complete_task_with_unmet_dependency_raises(self):
        project = _make_project()
        t1 = create_task(project, "Task one", "First task description", "Why one")
        t2 = create_task(
            project,
            "Task two",
            "Second task description",
            "Why two",
            dependencies=[t1.id],
        )
        with pytest.raises(TaskDependencyError):
            complete_task(project, t2.id)

    def test_complete_already_completed_is_idempotent(self):
        project = _make_project()
        task = create_task(project, "Simple task", "No deps needed", "Matters")
        complete_task(project, task.id)
        result = complete_task(project, task.id)
        assert result.status == TaskStatus.COMPLETED

    def test_complete_nonexistent_task_raises(self):
        project = _make_project()
        with pytest.raises(TaskNotFoundError):
            complete_task(project, "nonexistent-id")


class TestCanCompleteTask:
    def test_can_complete_with_no_deps(self):
        project = _make_project()
        task = create_task(project, "Simple task", "No deps needed", "Matters")
        assert can_complete_task(project, task.id) is True

    def test_cannot_complete_with_unmet_dep(self):
        project = _make_project()
        t1 = create_task(project, "Task one", "First task description", "Why one")
        t2 = create_task(
            project,
            "Task two",
            "Second task description",
            "Why two",
            dependencies=[t1.id],
        )
        assert can_complete_task(project, t2.id) is False

    def test_can_complete_when_dep_is_done(self):
        project = _make_project()
        t1 = create_task(project, "Task one", "First task description", "Why one")
        t2 = create_task(
            project,
            "Task two",
            "Second task description",
            "Why two",
            dependencies=[t1.id],
        )
        complete_task(project, t1.id)
        assert can_complete_task(project, t2.id) is True

    def test_cannot_complete_with_missing_dep_id(self):
        project = _make_project()
        t1 = create_task(
            project,
            "Task one",
            "Description one",
            "Why",
            dependencies=["nonexistent-id"],
        )
        assert can_complete_task(project, t1.id) is False


class TestBlockTask:
    def test_block_task(self):
        project = _make_project()
        task = create_task(project, "Simple task", "Description here", "Why")
        blocked = block_task(project, task.id)
        assert blocked.status == TaskStatus.BLOCKED


class TestStartTask:
    def test_start_task(self):
        project = _make_project()
        task = create_task(project, "Simple task", "Description here", "Why")
        started = start_task(project, task.id)
        assert started.status == TaskStatus.IN_PROGRESS


class TestGetTasks:
    def test_get_pending_tasks(self):
        project = _make_project()
        t1 = create_task(project, "Task one", "Description one", "Why one")
        t2 = create_task(project, "Task two", "Description two", "Why two")
        complete_task(project, t1.id)
        pending = get_pending_tasks(project)
        assert len(pending) == 1
        assert pending[0].id == t2.id

    def test_get_completed_tasks(self):
        project = _make_project()
        t1 = create_task(project, "Task one", "Description one", "Why one")
        create_task(project, "Task two", "Description two", "Why two")
        complete_task(project, t1.id)
        completed = get_completed_tasks(project)
        assert len(completed) == 1
        assert completed[0].id == t1.id

    def test_get_pending_includes_blocked(self):
        project = _make_project()
        task = create_task(project, "Task one", "Description one", "Why one")
        block_task(project, task.id)
        pending = get_pending_tasks(project)
        assert len(pending) == 1

    def test_get_pending_includes_in_progress(self):
        project = _make_project()
        task = create_task(project, "Task one", "Description one", "Why one")
        start_task(project, task.id)
        pending = get_pending_tasks(project)
        assert len(pending) == 1


class TestCheckDependencies:
    def test_check_deps_no_unmet(self):
        project = _make_project()
        task = create_task(project, "Simple task", "Description here", "Why")
        unmet = check_dependencies(project, task.id)
        assert unmet == []

    def test_check_deps_with_unmet(self):
        project = _make_project()
        t1 = create_task(project, "Task one", "Description one", "Why one")
        t2 = create_task(
            project,
            "Task two",
            "Description two",
            "Why two",
            dependencies=[t1.id],
        )
        unmet = check_dependencies(project, t2.id)
        assert len(unmet) == 1
        assert unmet[0].id == t1.id

    def test_check_deps_after_completion(self):
        project = _make_project()
        t1 = create_task(project, "Task one", "Description one", "Why one")
        t2 = create_task(
            project,
            "Task two",
            "Description two",
            "Why two",
            dependencies=[t1.id],
        )
        complete_task(project, t1.id)
        unmet = check_dependencies(project, t2.id)
        assert unmet == []


class TestGenerateInitialTasks:
    def test_generates_tasks(self):
        project = _make_project()
        generate_initial_tasks(project)
        assert len(project.tasks) > 0

    def test_generates_eight_tasks(self):
        project = _make_project()
        generate_initial_tasks(project)
        assert len(project.tasks) == 8

    def test_all_tasks_are_todo(self):
        project = _make_project()
        generate_initial_tasks(project)
        for task in project.tasks:
            assert task.status == TaskStatus.TODO

    def test_tasks_have_required_fields(self):
        project = _make_project()
        generate_initial_tasks(project)
        for task in project.tasks:
            assert task.title
            assert task.description
            assert task.why
            assert task.id

    def test_critical_tasks_present(self):
        project = _make_project()
        generate_initial_tasks(project)
        critical = [t for t in project.tasks if t.priority == TaskPriority.CRITICAL]
        assert len(critical) > 0

    def test_no_scientific_content_invented(self):
        project = _make_project()
        generate_initial_tasks(project)
        for task in project.tasks:
            assert "mmHg" not in task.description
            assert "mg/dL" not in task.description
