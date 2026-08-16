"""
Project domain service layer.

Provides the canonical operations on ResearchProject:
  - create_project()
  - update_project()

Keeps business logic independent of any UI framework.

NO-INVENTION PRINCIPLE:
  This layer never fills in missing research content.
  It only persists what the researcher explicitly provides.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from research_copilot.core.models import ResearchProject
from research_copilot.core.enums import ProjectState


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def create_project(title: str, idea: str) -> ResearchProject:
    """
    Create a new ResearchProject.

    Parameters
    ----------
    title : str
        Human-readable project title.
    idea : str
        The core research idea as articulated by the researcher.

    Returns
    -------
    ResearchProject
        A freshly created project in the IDEA state.

    Raises
    ------
    ValidationError
        If title or idea fail domain validation.
    """
    return ResearchProject(title=title, idea=idea)


def update_project(
    project: ResearchProject,
    updates: Dict[str, Any],
) -> ResearchProject:
    """
    Apply researcher-provided updates to a ResearchProject.

    Only the fields present in `updates` are modified.
    The `updated_at` timestamp is always refreshed.
    The project `id` and `created_at` are never modified by this function.

    Parameters
    ----------
    project : ResearchProject
        The project to update (mutated in-place).
    updates : Dict[str, Any]
        A dict of field names to new values.

    Returns
    -------
    ResearchProject
        The same project instance after mutation.

    Raises
    ------
    ValueError
        If an attempt is made to update `id` or `created_at`.
    ValidationError
        If any updated value fails domain validation.
    """
    protected_fields = {"id", "created_at"}

    for field_name, value in updates.items():
        if field_name in protected_fields:
            raise ValueError(
                f"Field '{field_name}' is protected and cannot be updated "
                "via update_project()."
            )
        setattr(project, field_name, value)

    project.updated_at = _now_utc()
    return project


def touch(project: ResearchProject) -> ResearchProject:
    """
    Update the `updated_at` timestamp without changing any other field.

    Parameters
    ----------
    project : ResearchProject
        The project to touch.

    Returns
    -------
    ResearchProject
        The same project instance.
    """
    project.updated_at = _now_utc()
    return project
