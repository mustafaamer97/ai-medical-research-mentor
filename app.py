"""
AI Research Co-Pilot — Application Entry Point

Sprint 1: Minimal Streamlit shell.

Purpose:
  - Verify domain loads correctly
  - Verify ResearchProject can be instantiated
  - Verify application starts successfully

The complete UI will be built in future sprints after
the domain foundation is frozen.
"""

import streamlit as st

from research_copilot.core.enums import ProjectState
from research_copilot.core.models import ResearchProject
from research_copilot.core.project import create_project


def main() -> None:
    st.set_page_config(
        page_title="AI Research Co-Pilot",
        page_icon="🔬",
        layout="wide",
    )

    st.title("🔬 AI Research Co-Pilot")
    st.caption("Sprint 1 — Domain Foundation")

    st.info(
        "Sprint 1 establishes the canonical domain model. "
        "The full UI will be implemented in Sprint 2 onwards."
    )

    st.divider()

    # ------------------------------------------------------------------
    # Domain verification: instantiate a ResearchProject
    # ------------------------------------------------------------------
    st.subheader("Domain Verification")

    try:
        demo_project = create_project(
            title="Demo Research Project",
            idea=(
                "This is a demonstration project created to verify that the "
                "ResearchProject domain model loads and operates correctly."
            ),
        )

        st.success("✅ ResearchProject domain loaded successfully.")

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Project ID", demo_project.id[:8] + "…")
        with col2:
            st.metric("State", demo_project.state.value)
        with col3:
            st.metric(
                "Created",
                demo_project.created_at.strftime("%Y-%m-%d %H:%M UTC"),
            )

        with st.expander("Full domain object (JSON)", expanded=False):
            st.json(demo_project.model_dump(mode="json"))

    except Exception as exc:  # noqa: BLE001
        st.error(f"❌ Domain instantiation failed: {exc}")
        raise

    st.divider()
    st.caption(
        "AI Research Co-Pilot · Sprint 1 · "
        "Domain foundation — researcher remains the decision-maker."
    )


if __name__ == "__main__":
    main()
