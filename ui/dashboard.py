from __future__ import annotations

from typing import Optional

import streamlit as st

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
    ResearchStateEnum,
    SampleSizePlan,
    StudyDesign,
    StudyDesignType,
    TaskStatus,
)
from core.state import (
    get_valid_next_states,
    state_progress_index,
    transition_state,
)
from core.task_engine import (
    can_complete_task,
    complete_task,
    get_completed_tasks,
    get_pending_tasks,
)


def _state_badge(state: ResearchStateEnum) -> str:
    labels = {
        ResearchStateEnum.IDEA: "💡 Idea",
        ResearchStateEnum.QUESTION_DEFINED: "❓ Question Defined",
        ResearchStateEnum.DESIGN_SELECTED: "🧪 Design Selected",
        ResearchStateEnum.PROTOCOL_READY: "📋 Protocol Ready",
        ResearchStateEnum.LITERATURE_SEARCH: "📚 Literature Search",
        ResearchStateEnum.SCREENING: "🔍 Screening",
        ResearchStateEnum.DATA_COLLECTION: "📊 Data Collection",
        ResearchStateEnum.DATA_READY: "✅ Data Ready",
        ResearchStateEnum.ANALYSIS_PLAN_LOCKED: "🔒 Analysis Plan Locked",
        ResearchStateEnum.ANALYSIS_COMPLETE: "📈 Analysis Complete",
        ResearchStateEnum.MANUSCRIPT_DRAFT: "✍️ Manuscript Draft",
        ResearchStateEnum.AUDIT: "🔎 Audit",
        ResearchStateEnum.JOURNAL_SELECTION: "📰 Journal Selection",
        ResearchStateEnum.READY_FOR_SUBMISSION: "🚀 Ready for Submission",
    }
    return labels.get(state, state.value)


def _priority_icon(priority: str) -> str:
    return {
        "LOW": "🟢",
        "MEDIUM": "🟡",
        "HIGH": "🟠",
        "CRITICAL": "🔴",
    }.get(priority, "⚪")


def render_dashboard(project: ResearchProject) -> ResearchProject:
    st.title(f"🔬 {project.title}")
    _render_state_section(project)
    st.divider()
    _render_research_details(project)
    st.divider()
    _render_tasks_section(project)
    return project


def _render_state_section(project: ResearchProject) -> None:
    idx, total = state_progress_index(project.state)
    pct = int((idx / total) * 100) if total > 0 else 0

    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown(f"**Current Phase:** {_state_badge(project.state)}")
        st.progress(pct, text=f"Progress: {pct}%")
    with col2:
        st.metric("Phase", f"{idx + 1}/{total + 1}")

    valid_next = get_valid_next_states(project.state)
    if valid_next:
        st.markdown("**Advance to next phase:**")
        for next_state in valid_next:
            if st.button(
                f"→ {_state_badge(next_state)}",
                key=f"advance_{next_state.value}",
                use_container_width=True,
            ):
                try:
                    project.state = transition_state(project.state, next_state)
                    project.touch()
                    st.success(f"Advanced to: {_state_badge(next_state)}")
                    st.rerun()
                except Exception as e:
                    st.error(str(e))
    else:
        st.info("🎉 This project has reached its final phase.")


def _render_research_details(project: ResearchProject) -> None:
    st.subheader("📝 Research Details")
    tab1, tab2, tab3, tab4 = st.tabs(
        ["Question & Design", "Population & PICO", "Criteria", "Plans"]
    )
    with tab1:
        _render_research_question(project)
        st.divider()
        _render_study_design(project)
    with tab2:
        _render_population(project)
        _render_exposure_intervention(project)
        _render_comparator(project)
        _render_outcomes(project)
    with tab3:
        _render_inclusion_criteria(project)
        _render_exclusion_criteria(project)
    with tab4:
        _render_sample_size(project)
        _render_analysis_plan(project)


def _render_research_question(project: ResearchProject) -> None:
    st.markdown("#### Research Question")
    with st.expander(
        "Define / Edit Research Question",
        expanded=project.research_question is None,
    ):
        with st.form("rq_form"):
            current_q = project.research_question
            q_text = st.text_area(
                "Research Question *",
                value=current_q.question_text if current_q else "",
                placeholder="e.g., Does metformin reduce cardiovascular mortality in adults with type 2 diabetes?",
                height=100,
            )
            background = st.text_area(
                "Background / Rationale",
                value=current_q.background or "" if current_q else "",
                placeholder="Why is this question important?",
                height=80,
            )
            if st.form_submit_button("Save Research Question", use_container_width=True):
                if len(q_text.strip()) < 10:
                    st.error("Research question must be at least 10 characters.")
                else:
                    project.research_question = ResearchQuestion(
                        question_text=q_text.strip(),
                        background=background.strip() or None,
                    )
                    project.touch()
                    st.success("Research question saved.")
                    st.rerun()
    if project.research_question:
        st.markdown(f"**Question:** {project.research_question.question_text}")
        if project.research_question.background:
            st.markdown(f"**Background:** {project.research_question.background}")


def _render_study_design(project: ResearchProject) -> None:
    st.markdown("#### Study Design")
    with st.expander(
        "Select Study Design",
        expanded=project.study_design is None,
    ):
        with st.form("design_form"):
            design_options = [d.value for d in StudyDesignType]
            current_val = (
                project.study_design.design_type.value
                if project.study_design
                else design_options[0]
            )
            selected = st.selectbox(
                "Study Design *",
                design_options,
                index=design_options.index(current_val),
            )
            rationale = st.text_area(
                "Rationale for design choice",
                value=project.study_design.rationale or "" if project.study_design else "",
                placeholder="Why did you choose this design?",
                height=80,
            )
            if st.form_submit_button("Save Study Design", use_container_width=True):
                project.study_design = StudyDesign(
                    design_type=StudyDesignType(selected),
                    rationale=rationale.strip() or None,
                )
                project.touch()
                st.success("Study design saved.")
                st.rerun()
    if project.study_design:
        st.markdown(f"**Design:** {project.study_design.design_type.value}")
        if project.study_design.rationale:
            st.markdown(f"**Rationale:** {project.study_design.rationale}")


def _render_population(project: ResearchProject) -> None:
    st.markdown("#### Population")
    with st.expander("Define Population", expanded=project.population is None):
        with st.form("pop_form"):
            current = project.population
            desc = st.text_area(
                "Population Description *",
                value=current.description if current else "",
                placeholder="e.g., Adults aged 18–75 with confirmed type 2 diabetes diagnosis",
                height=80,
            )
            setting = st.text_input(
                "Setting",
                value=current.setting or "" if current else "",
                placeholder="e.g., Outpatient primary care clinics",
            )
            if st.form_submit_button("Save Population", use_container_width=True):
                if len(desc.strip()) < 3:
                    st.error("Population description must be at least 3 characters.")
                else:
                    project.population = Population(
                        description=desc.strip(),
                        setting=setting.strip() or None,
                    )
                    project.touch()
                    st.success("Population saved.")
                    st.rerun()
    if project.population:
        st.markdown(f"**Population:** {project.population.description}")
        if project.population.setting:
            st.markdown(f"**Setting:** {project.population.setting}")


def _render_exposure_intervention(project: ResearchProject) -> None:
    st.markdown("#### Exposure / Intervention")
    with st.expander(
        "Define Exposure or Intervention",
        expanded=(project.exposure is None and project.intervention is None),
    ):
        tab_e, tab_i = st.tabs(["Exposure (Observational)", "Intervention (Experimental)"])
        with tab_e:
            with st.form("exposure_form"):
                current = project.exposure
                desc = st.text_area(
                    "Exposure Description *",
                    value=current.description if current else "",
                    placeholder="e.g., Metformin use (any dose for ≥6 months)",
                    height=80,
                )
                method = st.text_input(
                    "Measurement Method",
                    value=current.measurement_method or "" if current else "",
                    placeholder="e.g., Prescription records",
                )
                if st.form_submit_button("Save Exposure", use_container_width=True):
                    if len(desc.strip()) < 3:
                        st.error("Exposure description required.")
                    else:
                        project.exposure = Exposure(
                            description=desc.strip(),
                            measurement_method=method.strip() or None,
                        )
                        project.touch()
                        st.success("Exposure saved.")
                        st.rerun()
        with tab_i:
            with st.form("intervention_form"):
                current = project.intervention
                desc = st.text_area(
                    "Intervention Description *",
                    value=current.description if current else "",
                    placeholder="e.g., Metformin 500mg twice daily",
                    height=80,
                )
                protocol = st.text_input(
                    "Dosage / Protocol",
                    value=current.dosage_or_protocol or "" if current else "",
                    placeholder="e.g., Titrated to 2000mg/day over 4 weeks",
                )
                if st.form_submit_button("Save Intervention", use_container_width=True):
                    if len(desc.strip()) < 3:
                        st.error("Intervention description required.")
                    else:
                        project.intervention = Intervention(
                            description=desc.strip(),
                            dosage_or_protocol=protocol.strip() or None,
                        )
                        project.touch()
                        st.success("Intervention saved.")
                        st.rerun()
    if project.exposure:
        st.markdown(f"**Exposure:** {project.exposure.description}")
    if project.intervention:
        st.markdown(f"**Intervention:** {project.intervention.description}")


def _render_comparator(project: ResearchProject) -> None:
    st.markdown("#### Comparator")
    with st.expander("Define Comparator", expanded=project.comparator is None):
        with st.form("comp_form"):
            current = project.comparator
            desc = st.text_area(
                "Comparator Description *",
                value=current.description if current else "",
                placeholder="e.g., Adults with T2DM not receiving metformin / Placebo",
                height=80,
            )
            if st.form_submit_button("Save Comparator", use_container_width=True):
                if len(desc.strip()) < 3:
                    st.error("Comparator description required.")
                else:
                    project.comparator = Comparator(description=desc.strip())
                    project.touch()
                    st.success("Comparator saved.")
                    st.rerun()
    if project.comparator:
        st.markdown(f"**Comparator:** {project.comparator.description}")


def _render_outcomes(project: ResearchProject) -> None:
    st.markdown("#### Outcomes")
    with st.expander(
        "Define Primary Outcome",
        expanded=project.primary_outcome is None,
    ):
        with st.form("primary_outcome_form"):
            current = project.primary_outcome
            name = st.text_input(
                "Outcome Name *",
                value=current.name if current else "",
                placeholder="e.g., All-cause mortality",
            )
            desc = st.text_area(
                "Description *",
                value=current.description if current else "",
                placeholder="e.g., Death from any cause during follow-up",
                height=80,
            )
            method = st.text_input(
                "Measurement Method",
                value=current.measurement_method or "" if current else "",
                placeholder="e.g., National death registry",
            )
            time_point = st.text_input(
                "Time Point",
                value=current.time_point or "" if current else "",
                placeholder="e.g., At 5 years follow-up",
            )
            if st.form_submit_button("Save Primary Outcome", use_container_width=True):
                if len(name.strip()) < 2 or len(desc.strip()) < 3:
                    st.error("Name and description are required.")
                else:
                    project.primary_outcome = Outcome(
                        name=name.strip(),
                        description=desc.strip(),
                        measurement_method=method.strip() or None,
                        time_point=time_point.strip() or None,
                        is_primary=True,
                    )
                    project.touch()
                    st.success("Primary outcome saved.")
                    st.rerun()
    if project.primary_outcome:
        st.markdown(
            f"**Primary Outcome:** {project.primary_outcome.name} "
            f"— {project.primary_outcome.description}"
        )
    st.markdown("##### Secondary Outcomes")
    with st.expander("Add Secondary Outcome"):
        with st.form("secondary_outcome_form"):
            name = st.text_input(
                "Outcome Name *",
                placeholder="e.g., Cardiovascular mortality",
            )
            desc = st.text_area(
                "Description *",
                placeholder="e.g., Death attributed to cardiovascular cause",
                height=60,
            )
            method = st.text_input(
                "Measurement Method",
                placeholder="e.g., ICD-10 coding",
            )
            time_point = st.text_input(
                "Time Point",
                placeholder="e.g., At 5 years",
            )
            if st.form_submit_button("Add Secondary Outcome", use_container_width=True):
                if len(name.strip()) < 2 or len(desc.strip()) < 3:
                    st.error("Name and description required.")
                else:
                    project.secondary_outcomes.append(
                        Outcome(
                            name=name.strip(),
                            description=desc.strip(),
                            measurement_method=method.strip() or None,
                            time_point=time_point.strip() or None,
                            is_primary=False,
                        )
                    )
                    project.touch()
                    st.success("Secondary outcome added.")
                    st.rerun()
    if project.secondary_outcomes:
        for i, o in enumerate(project.secondary_outcomes, 1):
            st.markdown(f"{i}. **{o.name}** — {o.description}")


def _render_inclusion_criteria(project: ResearchProject) -> None:
    st.markdown("#### Inclusion Criteria")
    with st.expander("Manage Inclusion Criteria"):
        with st.form("inclusion_form"):
            current = "\n".join(project.inclusion_criteria.criteria)
            text = st.text_area(
                "Enter each criterion on a new line",
                value=current,
                height=120,
                placeholder=(
                    "e.g.\nAge 18–75 years\n"
                    "Diagnosis of T2DM (ICD-10: E11)\n"
                    "Ability to provide informed consent"
                ),
            )
            if st.form_submit_button("Save Inclusion Criteria", use_container_width=True):
                criteria = [c.strip() for c in text.splitlines() if c.strip()]
                project.inclusion_criteria = InclusionCriteria(criteria=criteria)
                project.touch()
                st.success("Inclusion criteria saved.")
                st.rerun()
    if project.inclusion_criteria.criteria:
        for c in project.inclusion_criteria.criteria:
            st.markdown(f"✅ {c}")


def _render_exclusion_criteria(project: ResearchProject) -> None:
    st.markdown("#### Exclusion Criteria")
    with st.expander("Manage Exclusion Criteria"):
        with st.form("exclusion_form"):
            current = "\n".join(project.exclusion_criteria.criteria)
            text = st.text_area(
                "Enter each criterion on a new line",
                value=current,
                height=120,
                placeholder=(
                    "e.g.\nPregnancy or breastfeeding\n"
                    "Severe renal impairment (eGFR < 30)\n"
                    "Prior metformin use"
                ),
            )
            if st.form_submit_button("Save Exclusion Criteria", use_container_width=True):
                criteria = [c.strip() for c in text.splitlines() if c.strip()]
                project.exclusion_criteria = ExclusionCriteria(criteria=criteria)
                project.touch()
                st.success("Exclusion criteria saved.")
                st.rerun()
    if project.exclusion_criteria.criteria:
        for c in project.exclusion_criteria.criteria:
            st.markdown(f"❌ {c}")


def _render_sample_size(project: ResearchProject) -> None:
    st.markdown("#### Sample Size Plan")
    with st.expander("Define Sample Size Plan", expanded=False):
        with st.form("sample_size_form"):
            current = project.sample_size_plan
            planned_n = st.number_input(
                "Planned N",
                min_value=1,
                value=int(current.planned_n) if (current and current.planned_n) else 100,
                step=1,
            )
            rationale = st.text_area(
                "Rationale",
                value=current.rationale or "" if current else "",
                placeholder="e.g., Based on 80% power to detect HR of 0.75 (reference: Smith et al.)",
                height=80,
            )
            notes = st.text_input(
                "Notes",
                value=current.notes or "" if current else "",
            )
            if st.form_submit_button("Save Sample Size Plan", use_container_width=True):
                project.sample_size_plan = SampleSizePlan(
                    planned_n=int(planned_n),
                    rationale=rationale.strip() or None,
                    notes=notes.strip() or None,
                )
                project.touch()
                st.success("Sample size plan saved.")
                st.rerun()
    if project.sample_size_plan and project.sample_size_plan.planned_n:
        st.markdown(f"**Planned N:** {project.sample_size_plan.planned_n}")


def _render_analysis_plan(project: ResearchProject) -> None:
    st.markdown("#### Analysis Plan")
    with st.expander("Define Analysis Plan", expanded=False):
        with st.form("analysis_plan_form"):
            current = project.analysis_plan
            primary_desc = st.text_area(
                "Primary Analysis Description",
                value=current.primary_analysis_description or "" if current else "",
                placeholder="e.g., Cox proportional hazards regression adjusted for confounders",
                height=80,
            )
            secondary_text = st.text_area(
                "Secondary Analyses (one per line)",
                value="\n".join(current.secondary_analyses) if current else "",
                height=80,
                placeholder=(
                    "e.g.\nSensitivity analysis excluding early events\n"
                    "Subgroup analysis by age"
                ),
            )
            notes = st.text_input(
                "Notes",
                value=current.notes or "" if current else "",
            )
            if st.form_submit_button("Save Analysis Plan", use_container_width=True):
                secondary_list = [
                    s.strip() for s in secondary_text.splitlines() if s.strip()
                ]
                project.analysis_plan = AnalysisPlan(
                    primary_analysis_description=primary_desc.strip() or None,
                    secondary_analyses=secondary_list,
                    notes=notes.strip() or None,
                )
                project.touch()
                st.success("Analysis plan saved.")
                st.rerun()
    if project.analysis_plan and project.analysis_plan.primary_analysis_description:
        st.markdown(
            f"**Primary Analysis:** {project.analysis_plan.primary_analysis_description}"
        )


def _render_tasks_section(project: ResearchProject) -> None:
    st.subheader("✅ Research Tasks")
    pending = get_pending_tasks(project)
    completed = get_completed_tasks(project)

    col1, col2, col3 = st.columns(3)
    col1.metric("Total", len(project.tasks))
    col2.metric("Pending", len(pending))
    col3.metric("Completed", len(completed))

    if pending:
        st.markdown("#### Pending Tasks")
        for task in sorted(pending, key=lambda t: list(TaskStatus).index(t.status)):
            status_icon = {
                "TODO": "⬜",
                "IN_PROGRESS": "🔄",
                "BLOCKED": "🚫",
            }.get(task.status.value, "⬜")
            icon = _priority_icon(task.priority.value)

            col_a, col_b = st.columns([5, 1])
            with col_a:
                st.markdown(f"{status_icon} {icon} **{task.title}**")
                st.caption(task.description)
                st.caption(f"💡 *{task.why}*")
                if task.dependencies:
                    unmet = [
                        t.title
                        for t in project.tasks
                        if t.id in task.dependencies
                        and t.status != TaskStatus.COMPLETED
                    ]
                    if unmet:
                        st.caption(f"⛔ Waiting for: {', '.join(unmet)}")
            with col_b:
                can_do = can_complete_task(project, task.id)
                if st.button(
                    "Done",
                    key=f"complete_{task.id}",
                    disabled=not can_do,
                    use_container_width=True,
                ):
                    try:
                        complete_task(project, task.id)
                        st.success(f"'{task.title}' completed!")
                        st.rerun()
                    except Exception as e:
                        st.error(str(e))
            st.divider()

    if completed:
        with st.expander(f"Completed Tasks ({len(completed)})"):
            for task in completed:
                st.markdown(f"✅ ~~{task.title}~~")
                if task.completed_at:
                    st.caption(
                        f"Completed: {task.completed_at.strftime('%Y-%m-%d %H:%M')}"
                    )
