from __future__ import annotations

from typing import Optional

import streamlit as st

from core.models import ResearchProject
from core.task_engine import generate_initial_tasks


def render_onboarding() -> Optional[ResearchProject]:
    st.title("🔬 New Research Project")
    st.markdown("Fill in the details below to start your research journey.")

    with st.form("new_project_form", clear_on_submit=False):
        title = st.text_input(
            "Project Title",
            placeholder="e.g., Effect of metformin on cardiovascular outcomes in T2DM",
        )
        idea = st.text_area(
            "Research Idea",
            placeholder="Describe your research idea in a few sentences...",
            height=140,
        )
        submitted = st.form_submit_button("Create Project", use_container_width=True)

    if submitted:
        errors = []
        if not title or len(title.strip()) < 3:
            errors.append("Project title must be at least 3 characters.")
        if not idea or len(idea.strip()) < 10:
            errors.append("Research idea must be at least 10 characters.")

        if errors:
            for e in errors:
                st.error(e)
            return None

        project = ResearchProject(title=title.strip(), idea=idea.strip())
        generate_initial_tasks(project)
        return project

    return None
