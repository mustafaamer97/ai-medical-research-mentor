from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from core.models import ResearchProject, ResearchTask, TaskPriority, TaskStatus


class TaskDependencyError(Exception):
    pass


class TaskNotFoundError(Exception):
    pass


def _get_task(project: ResearchProject, task_id: str) -> ResearchTask:
    for t in project.tasks:
        if t.id == task_id:
            return t
    raise TaskNotFoundError(
        f"Task '{task_id}' not found in project '{project.id}'."
    )


def create_task(
    project: ResearchProject,
    title: str,
    description: str,
    why: str,
    priority: TaskPriority = TaskPriority.MEDIUM,
    dependencies: Optional[List[str]] = None,
) -> ResearchTask:
    task = ResearchTask(
        title=title,
        description=description,
        why=why,
        priority=priority,
        dependencies=dependencies or [],
    )
    project.tasks.append(task)
    project.touch()
    return task


def update_task(
    project: ResearchProject,
    task_id: str,
    title: Optional[str] = None,
    description: Optional[str] = None,
    why: Optional[str] = None,
    priority: Optional[TaskPriority] = None,
) -> ResearchTask:
    task = _get_task(project, task_id)
    if title is not None:
        task.title = title
    if description is not None:
        task.description = description
    if why is not None:
        task.why = why
    if priority is not None:
        task.priority = priority
    project.touch()
    return task


def can_complete_task(project: ResearchProject, task_id: str) -> bool:
    task = _get_task(project, task_id)
    for dep_id in task.dependencies:
        try:
            dep = _get_task(project, dep_id)
            if dep.status != TaskStatus.COMPLETED:
                return False
        except TaskNotFoundError:
            return False
    return True


def complete_task(project: ResearchProject, task_id: str) -> ResearchTask:
    task = _get_task(project, task_id)
    if task.status == TaskStatus.COMPLETED:
        return task
    if not can_complete_task(project, task_id):
        unmet = _get_unmet_dependencies(project, task)
        raise TaskDependencyError(
            f"Cannot complete task '{task.title}'. "
            f"Unmet dependencies: {[t.title for t in unmet]}."
        )
    task.status = TaskStatus.COMPLETED
    task.completed_at = datetime.utcnow()
    project.touch()
    return task


def block_task(project: ResearchProject, task_id: str) -> ResearchTask:
    task = _get_task(project, task_id)
    task.status = TaskStatus.BLOCKED
    project.touch()
    return task


def start_task(project: ResearchProject, task_id: str) -> ResearchTask:
    task = _get_task(project, task_id)
    if task.status in (TaskStatus.TODO, TaskStatus.BLOCKED):
        task.status = TaskStatus.IN_PROGRESS
        project.touch()
    return task


def get_pending_tasks(project: ResearchProject) -> List[ResearchTask]:
    return [
        t for t in project.tasks
        if t.status in (TaskStatus.TODO, TaskStatus.IN_PROGRESS, TaskStatus.BLOCKED)
    ]


def get_completed_tasks(project: ResearchProject) -> List[ResearchTask]:
    return [t for t in project.tasks if t.status == TaskStatus.COMPLETED]


def check_dependencies(
    project: ResearchProject, task_id: str
) -> List[ResearchTask]:
    task = _get_task(project, task_id)
    return _get_unmet_dependencies(project, task)


def _get_unmet_dependencies(
    project: ResearchProject, task: ResearchTask
) -> List[ResearchTask]:
    unmet: List[ResearchTask] = []
    for dep_id in task.dependencies:
        try:
            dep = _get_task(project, dep_id)
            if dep.status != TaskStatus.COMPLETED:
                unmet.append(dep)
        except TaskNotFoundError:
            pass
    return unmet


def generate_initial_tasks(project: ResearchProject) -> None:
    definitions = [
        {
            "title": "Define research population",
            "description": (
                "Clearly describe the target population for your study, "
                "including relevant demographic and clinical characteristics."
            ),
            "why": (
                "A well-defined population ensures your study question is "
                "answerable and results are interpretable."
            ),
            "priority": TaskPriority.CRITICAL,
        },
        {
            "title": "Define exposure or intervention",
            "description": (
                "Specify the exposure (for observational studies) or intervention "
                "(for experimental studies) you are investigating."
            ),
            "why": (
                "Precise exposure or intervention definition is essential "
                "for a valid study design."
            ),
            "priority": TaskPriority.CRITICAL,
        },
        {
            "title": "Define comparator",
            "description": (
                "Identify the comparison group or condition "
                "(e.g., unexposed group, placebo, standard of care)."
            ),
            "why": (
                "A clearly defined comparator is required "
                "to interpret effect estimates."
            ),
            "priority": TaskPriority.HIGH,
        },
        {
            "title": "Define primary outcome",
            "description": (
                "Specify the single primary outcome, including "
                "how and when it will be measured."
            ),
            "why": (
                "The primary outcome determines the core hypothesis "
                "and drives sample size planning."
            ),
            "priority": TaskPriority.CRITICAL,
        },
        {
            "title": "Define secondary outcomes",
            "description": (
                "List any secondary outcomes you will measure, "
                "with measurement details."
            ),
            "why": (
                "Secondary outcomes must be pre-specified to avoid "
                "post-hoc outcome selection bias."
            ),
            "priority": TaskPriority.HIGH,
        },
        {
            "title": "Define inclusion criteria",
            "description": (
                "List the criteria a participant must meet "
                "to be eligible for the study."
            ),
            "why": (
                "Inclusion criteria define your target population "
                "and support reproducibility."
            ),
            "priority": TaskPriority.HIGH,
        },
        {
            "title": "Define exclusion criteria",
            "description": (
                "List the criteria that would disqualify a participant "
                "from the study."
            ),
            "why": (
                "Exclusion criteria protect participant safety "
                "and study validity."
            ),
            "priority": TaskPriority.HIGH,
        },
        {
            "title": "Select study design",
            "description": (
                "Choose the most appropriate study design for your research question "
                "(e.g., cohort, RCT, case-control)."
            ),
            "why": (
                "The study design determines feasibility, "
                "the level of evidence, and analytical approach."
            ),
            "priority": TaskPriority.CRITICAL,
        },
    ]

    for defn in definitions:
        task = ResearchTask(
            title=defn["title"],
            description=defn["description"],
            why=defn["why"],
            priority=defn["priority"],
            dependencies=[],
        )
        project.tasks.append(task)

    project.touch()
