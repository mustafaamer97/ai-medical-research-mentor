from __future__ import annotations

import streamlit as st

from config.settings import APP_TITLE
from core.persistence import clear_project, load_project, save_project
from ui.dashboard import render_dashboard
from ui.onboarding import render_onboarding

st.set_page_config(
    page_title=APP_TITLE,
    page_icon="🔬",
    layout="centered",
    initial_sidebar_state="collapsed",
)

if "project" not in st.session_state:
    st.session_state.project = load_project()

if "page" not in st.session_state:
    st.session_state.page = (
        "dashboard" if st.session_state.project else "onboarding"
    )

with st.sidebar:
    st.title("🔬 Research Mentor")
    st.markdown("---")
    if st.session_state.project:
        st.markdown(f"**Project:** {st.session_state.project.title}")
        st.markdown(f"**State:** {st.session_state.project.state.value}")
        st.markdown("---")
        if st.button("🗑️ Delete Project", use_container_width=True):
            clear_project()
            st.session_state.project = None
            st.session_state.page = "onboarding"
            st.rerun()
    else:
        st.info("No active project.")
    st.markdown("---")
    st.caption("Sprint 1 — Research Foundation")

if st.session_state.page == "onboarding" or st.session_state.project is None:
    project = render_onboarding()
    if project is not None:
        st.session_state.project = project
        save_project(project)
        st.session_state.page = "dashboard"
        st.rerun()
elif st.session_state.page == "dashboard":
    project = render_dashboard(st.session_state.project)
    save_project(project)
    st.session_state.project = project
