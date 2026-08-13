"""
Sprint 1 + Sprint 2 + Sprint 3 Phase 1 — Streamlit Smoke Test

Sprint 1:  47 tests  (S1-01 through S1-47)
Sprint 2:  21 tests  (S2-01 through S2-21)
Sprint 3:  18 tests  (S3-01 through S3-18)
Total:     86 tests
"""
from __future__ import annotations

import json
import sys
import tempfile
import traceback
from pathlib import Path

ROOT = Path(__file__).parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

PASS = "✅ PASS"
FAIL = "❌ FAIL"
results: list[tuple[str, str, str]] = []


def check(name: str, fn):
    try:
        fn()
        results.append((PASS, name, ""))
    except Exception as exc:
        results.append(
            (FAIL, name, f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}")
        )


import pytest as pytest  # noqa: E402


# ══════════════════════════════════════════════
# SPRINT 1 SMOKE TESTS — 47 tests
# ══════════════════════════════════════════════

def test_import_config_settings():
    from config import settings
    assert settings.APP_TITLE
    assert settings.PERSISTENCE_FILE


def test_import_core_models():
    from core import models
    assert hasattr(models, "ResearchProject")
    assert hasattr(models, "ResearchTask")
    assert hasattr(models, "ResearchState")


def test_import_core_state():
    from core import state
    assert hasattr(state, "transition_state")
    assert hasattr(state, "validate_transition")
    assert hasattr(state, "InvalidStateTransitionError")


def test_import_core_task_engine():
    from core import task_engine
    assert hasattr(task_engine, "create_task")
    assert hasattr(task_engine, "complete_task")
    assert hasattr(task_engine, "generate_initial_tasks")


def test_import_core_persistence():
    from core import persistence
    assert hasattr(persistence, "save_project")
    assert hasattr(persistence, "load_project")
    assert hasattr(persistence, "clear_project")


def test_import_core_audit():
    from core import audit
    assert hasattr(audit, "AuditLog")
    assert hasattr(audit, "AuditEntry")


def test_import_ui_onboarding():
    from ui import onboarding
    assert hasattr(onboarding, "render_onboarding")


def test_import_ui_dashboard():
    from ui import dashboard
    assert hasattr(dashboard, "render_dashboard")


def test_import_app_module():
    app_path = ROOT / "app.py"
    assert app_path.exists(), "app.py not found"
    source = app_path.read_text()
    compile(source, "app.py", "exec")


def test_onboarding_creates_project():
    from core.models import ResearchProject
    from core.task_engine import generate_initial_tasks
    p = ResearchProject(
        title="Smoke Test Project Alpha",
        idea="Investigating the effect of treatment X on outcome Y in population Z",
    )
    generate_initial_tasks(p)
    assert p.title == "Smoke Test Project Alpha"
    assert len(p.tasks) == 8


def test_onboarding_rejects_short_title():
    from pydantic import ValidationError
    from core.models import ResearchProject
    with pytest.raises(ValidationError):
        ResearchProject(
            title="AB",
            idea="Investigating the effect of treatment X on outcome Y",
        )


def test_onboarding_rejects_short_idea():
    from pydantic import ValidationError
    from core.models import ResearchProject
    with pytest.raises(ValidationError):
        ResearchProject(title="Valid Project Title", idea="Short")


def test_exactly_eight_initial_tasks():
    from core.models import ResearchProject
    from core.task_engine import generate_initial_tasks
    p = ResearchProject(
        title="Eight Tasks Test",
        idea="Testing that exactly eight initial tasks are generated for this project",
    )
    generate_initial_tasks(p)
    assert len(p.tasks) == 8


def test_initial_tasks_all_todo():
    from core.models import ResearchProject, TaskStatus
    from core.task_engine import generate_initial_tasks
    p = ResearchProject(
        title="Task Status Test",
        idea="Verifying all initial tasks begin with TODO status in this project",
    )
    generate_initial_tasks(p)
    for task in p.tasks:
        assert task.status == TaskStatus.TODO


def test_initial_tasks_have_critical_priority():
    from core.models import ResearchProject, TaskPriority
    from core.task_engine import generate_initial_tasks
    p = ResearchProject(
        title="Priority Test Project",
        idea="Verifying critical priority tasks are generated for this research project",
    )
    generate_initial_tasks(p)
    priorities = {t.priority for t in p.tasks}
    assert TaskPriority.CRITICAL in priorities


def test_persistence_save_and_load():
    tmp = Path(tempfile.mkdtemp()) / "s1_save.json"
    from core.models import ResearchProject, ResearchStateEnum
    from core.persistence import save_project, load_project
    from core.task_engine import generate_initial_tasks
    p = ResearchProject(
        title="Persistence Smoke Test",
        idea="Verifying that the persistence layer correctly saves and restores project state",
    )
    generate_initial_tasks(p)
    p.state = ResearchStateEnum.QUESTION_DEFINED
    save_project(p, tmp)
    loaded = load_project(tmp)
    assert loaded is not None
    assert loaded.title == p.title
    assert loaded.id == p.id
    assert loaded.state == ResearchStateEnum.QUESTION_DEFINED
    assert len(loaded.tasks) == 8


def test_persistence_file_is_valid_json():
    tmp = Path(tempfile.mkdtemp()) / "s1_json.json"
    from core.models import ResearchProject
    from core.persistence import save_project
    from core.task_engine import generate_initial_tasks
    p = ResearchProject(
        title="JSON Validity Test",
        idea="Verifying that the saved file is valid JSON that can be parsed externally",
    )
    generate_initial_tasks(p)
    save_project(p, tmp)
    raw = tmp.read_text(encoding="utf-8")
    parsed = json.loads(raw)
    assert "project" in parsed
    assert parsed["project"]["title"] == "JSON Validity Test"


def test_persistence_corrupt_file_returns_none():
    tmp = Path(tempfile.mkdtemp()) / "corrupt.json"
    from core.persistence import load_project
    tmp.write_text("CORRUPT {{{{ NOT JSON", encoding="utf-8")
    result = load_project(tmp)
    assert result is None


def test_persistence_missing_file_returns_none():
    tmp = Path(tempfile.mkdtemp()) / "nonexistent.json"
    from core.persistence import load_project
    result = load_project(tmp)
    assert result is None


def test_persistence_clear_project():
    tmp = Path(tempfile.mkdtemp()) / "to_delete.json"
    from core.models import ResearchProject
    from core.persistence import save_project, load_project, clear_project
    p = ResearchProject(
        title="Delete Me Project Test",
        idea="This project will be deleted to test the clear project functionality",
    )
    save_project(p, tmp)
    assert tmp.exists()
    clear_project(tmp)
    assert not tmp.exists()
    result = load_project(tmp)
    assert result is None


def test_persistence_survives_restart():
    tmp = Path(tempfile.mkdtemp()) / "restart.json"
    from core.models import (
        ResearchProject,
        ResearchQuestion,
        StudyDesign,
        StudyDesignType,
        Population,
        Outcome,
        InclusionCriteria,
        ExclusionCriteria,
        ResearchStateEnum,
    )
    from core.persistence import save_project, load_project
    from core.task_engine import generate_initial_tasks, complete_task
    p = ResearchProject(
        title="Restart Survival Test",
        idea="Testing that all project data survives a simulated application restart",
    )
    generate_initial_tasks(p)
    p.research_question = ResearchQuestion(
        question_text="Does treatment X reduce outcome Y in population Z patients?"
    )
    p.study_design = StudyDesign(design_type=StudyDesignType.COHORT)
    p.population = Population(description="Adults aged 18-75 with condition Z")
    p.primary_outcome = Outcome(
        name="Primary endpoint",
        description="The main outcome measure for this study",
        is_primary=True,
    )
    p.inclusion_criteria = InclusionCriteria(
        criteria=["Age 18-75", "Condition Z"]
    )
    p.exclusion_criteria = ExclusionCriteria(criteria=["Pregnancy"])
    p.state = ResearchStateEnum.DESIGN_SELECTED
    complete_task(p, p.tasks[0].id)
    save_project(p, tmp)
    loaded = load_project(tmp)
    assert loaded.title == "Restart Survival Test"
    assert loaded.research_question.question_text == p.research_question.question_text
    assert loaded.study_design.design_type == StudyDesignType.COHORT
    assert loaded.population.description == "Adults aged 18-75 with condition Z"
    assert loaded.primary_outcome.name == "Primary endpoint"
    assert loaded.inclusion_criteria.criteria == ["Age 18-75", "Condition Z"]
    assert loaded.exclusion_criteria.criteria == ["Pregnancy"]
    assert loaded.state == ResearchStateEnum.DESIGN_SELECTED
    completed = [t for t in loaded.tasks if t.status.value == "COMPLETED"]
    assert len(completed) == 1


def test_research_question_create_and_edit():
    from core.models import ResearchProject, ResearchQuestion
    p = ResearchProject(
        title="RQ Test Project",
        idea="Testing research question creation and editing functionality in the project",
    )
    p.research_question = ResearchQuestion(
        question_text="Does treatment X reduce outcome Y in population Z?",
        background="Background rationale for the research question.",
    )
    assert p.research_question.question_text.startswith("Does")
    assert p.research_question.background is not None
    p.research_question = ResearchQuestion(
        question_text="Does revised treatment X reduce outcome Y more effectively in population Z?",
        background="Updated background rationale.",
    )
    assert "revised" in p.research_question.question_text


def test_study_design_select_and_save():
    from core.models import ResearchProject, StudyDesign, StudyDesignType
    p = ResearchProject(
        title="Design Test Project",
        idea="Testing study design selection and persistence for all available design types",
    )
    for design_type in StudyDesignType:
        p.study_design = StudyDesign(
            design_type=design_type, rationale="Selected because it fits."
        )
        assert p.study_design.design_type == design_type


def test_population_create_and_save():
    from core.models import ResearchProject, Population
    p = ResearchProject(
        title="Population Test",
        idea="Testing population definition and persistence in the research project",
    )
    p.population = Population(
        description="Adults aged 18-75 with type 2 diabetes",
        setting="Outpatient primary care",
    )
    assert p.population.description
    assert p.population.setting == "Outpatient primary care"


def test_exposure_create_and_save():
    from core.models import ResearchProject, Exposure
    p = ResearchProject(
        title="Exposure Test",
        idea="Testing exposure definition and persistence in the observational research project",
    )
    p.exposure = Exposure(
        description="Exposure to treatment X for at least six months duration",
        measurement_method="Prescription database records",
    )
    assert p.exposure.description
    assert p.exposure.measurement_method


def test_intervention_create_and_save():
    from core.models import ResearchProject, Intervention
    p = ResearchProject(
        title="Intervention Test",
        idea="Testing intervention definition and persistence in the experimental research project",
    )
    p.intervention = Intervention(
        description="Structured exercise program three times per week",
        dosage_or_protocol="60-minute sessions over 12 weeks",
    )
    assert p.intervention.description
    assert p.intervention.dosage_or_protocol


def test_comparator_create_and_save():
    from core.models import ResearchProject, Comparator
    p = ResearchProject(
        title="Comparator Test",
        idea="Testing comparator definition and persistence for the research study design",
    )
    p.comparator = Comparator(
        description="Placebo control group receiving no active treatment"
    )
    assert p.comparator.description


def test_primary_outcome_create_and_save():
    from core.models import ResearchProject, Outcome
    p = ResearchProject(
        title="Primary Outcome Test",
        idea="Testing primary outcome definition and persistence for the research project",
    )
    p.primary_outcome = Outcome(
        name="All-cause mortality",
        description="Death from any cause during the study follow-up period",
        measurement_method="National death registry linkage",
        time_point="At 5-year follow-up",
        is_primary=True,
    )
    assert p.primary_outcome.is_primary is True
    assert p.primary_outcome.name == "All-cause mortality"


def test_secondary_outcomes_create_and_save():
    from core.models import ResearchProject, Outcome
    p = ResearchProject(
        title="Secondary Outcomes Test",
        idea="Testing secondary outcome definition and persistence for the research project",
    )
    p.secondary_outcomes = [
        Outcome(
            name="Cardiovascular mortality",
            description="Death attributed to cardiovascular disease causes",
        ),
        Outcome(
            name="Hospital readmission",
            description="Unplanned hospital readmission within 30 days",
        ),
    ]
    assert len(p.secondary_outcomes) == 2
    assert all(not o.is_primary for o in p.secondary_outcomes)


def test_inclusion_criteria_create_and_save():
    from core.models import ResearchProject, InclusionCriteria
    p = ResearchProject(
        title="Inclusion Criteria Test",
        idea="Testing inclusion criteria definition and persistence for the research project",
    )
    p.inclusion_criteria = InclusionCriteria(
        criteria=[
            "Age 18-75 years",
            "Confirmed diagnosis of condition Z",
            "Ability to provide written informed consent",
        ]
    )
    assert len(p.inclusion_criteria.criteria) == 3


def test_exclusion_criteria_create_and_save():
    from core.models import ResearchProject, ExclusionCriteria
    p = ResearchProject(
        title="Exclusion Criteria Test",
        idea="Testing exclusion criteria definition and persistence for the research project",
    )
    p.exclusion_criteria = ExclusionCriteria(
        criteria=["Current pregnancy", "Severe hepatic impairment"]
    )
    assert len(p.exclusion_criteria.criteria) == 2


def test_sample_size_plan_create_and_save():
    from core.models import ResearchProject, SampleSizePlan
    p = ResearchProject(
        title="Sample Size Test",
        idea="Testing sample size plan definition and persistence for the research project",
    )
    p.sample_size_plan = SampleSizePlan(
        planned_n=450,
        rationale="Based on published effect size estimates and 80% statistical power",
        notes="Includes 10% dropout adjustment",
    )
    assert p.sample_size_plan.planned_n == 450
    assert p.sample_size_plan.rationale
    assert p.sample_size_plan.notes


def test_analysis_plan_create_and_save():
    from core.models import ResearchProject, AnalysisPlan
    p = ResearchProject(
        title="Analysis Plan Test",
        idea="Testing analysis plan definition and persistence for the research project",
    )
    p.analysis_plan = AnalysisPlan(
        primary_analysis_description=(
            "Intention-to-treat analysis using Cox proportional hazards"
        ),
        secondary_analyses=[
            "Per-protocol sensitivity analysis",
            "Subgroup analysis by age group",
        ],
        notes="Pre-registered analysis plan",
    )
    assert p.analysis_plan.primary_analysis_description
    assert len(p.analysis_plan.secondary_analyses) == 2


def test_task_completion():
    from core.models import ResearchProject, TaskStatus
    from core.task_engine import create_task, complete_task
    p = ResearchProject(
        title="Task Completion Test",
        idea="Testing that research tasks can be completed successfully without dependencies",
    )
    t = create_task(
        p, "Define population group", "Describe your population", "Core requirement"
    )
    assert t.status == TaskStatus.TODO
    result = complete_task(p, t.id)
    assert result.status == TaskStatus.COMPLETED
    assert result.completed_at is not None


def test_task_dependency_blocks_completion():
    from core.models import ResearchProject
    from core.task_engine import create_task, complete_task, TaskDependencyError
    p = ResearchProject(
        title="Dependency Block Test",
        idea="Testing that task dependencies are enforced and block premature completion",
    )
    t1 = create_task(
        p, "Task prerequisite one", "Must be done first", "It is required"
    )
    t2 = create_task(
        p,
        "Task dependent two",
        "Requires task one to be done first",
        "Logical dependency",
        dependencies=[t1.id],
    )
    with pytest.raises(TaskDependencyError):
        complete_task(p, t2.id)


def test_task_dependency_allows_completion_after_dep_met():
    from core.models import ResearchProject, TaskStatus
    from core.task_engine import create_task, complete_task
    p = ResearchProject(
        title="Dependency Allow Test",
        idea="Testing that dependent tasks can be completed once their dependencies are met",
    )
    t1 = create_task(
        p, "Task prerequisite one", "First required task description", "It is needed"
    )
    t2 = create_task(
        p,
        "Task dependent two",
        "Second task depends on the first one",
        "Follows logically",
        dependencies=[t1.id],
    )
    complete_task(p, t1.id)
    result = complete_task(p, t2.id)
    assert result.status == TaskStatus.COMPLETED


def test_initial_tasks_completable_independently():
    from core.models import ResearchProject
    from core.task_engine import generate_initial_tasks, can_complete_task
    p = ResearchProject(
        title="Initial Task Independence Test",
        idea="Verifying that all initial tasks can be completed without waiting on each other",
    )
    generate_initial_tasks(p)
    for task in p.tasks:
        assert task.dependencies == [], (
            f"Task '{task.title}' should have no dependencies"
        )
        assert can_complete_task(p, task.id) is True


def test_state_progression_idea_to_question():
    from core.models import ResearchProject, ResearchStateEnum
    from core.state import transition_state
    p = ResearchProject(
        title="State Progression Test",
        idea="Testing state machine transitions through the complete research workflow",
    )
    assert p.state == ResearchStateEnum.IDEA
    p.state = transition_state(p.state, ResearchStateEnum.QUESTION_DEFINED)
    assert p.state == ResearchStateEnum.QUESTION_DEFINED


def test_state_full_progression():
    from core.models import ResearchStateEnum
    from core.state import transition_state, all_states_in_order
    ordered = all_states_in_order()
    current = ordered[0]
    for next_state in ordered[1:]:
        current = transition_state(current, next_state)
    assert current == ResearchStateEnum.READY_FOR_SUBMISSION


def test_invalid_state_transition_blocked():
    from core.models import ResearchStateEnum
    from core.state import transition_state, InvalidStateTransitionError
    with pytest.raises(InvalidStateTransitionError):
        transition_state(
            ResearchStateEnum.IDEA, ResearchStateEnum.READY_FOR_SUBMISSION
        )


def test_state_progress_index():
    from core.models import ResearchStateEnum
    from core.state import state_progress_index
    idx, total = state_progress_index(ResearchStateEnum.IDEA)
    assert idx == 0
    assert total == 13
    idx2, total2 = state_progress_index(ResearchStateEnum.READY_FOR_SUBMISSION)
    assert idx2 == 13
    assert total2 == 13


def test_delete_project_clears_persistence():
    tmp = Path(tempfile.mkdtemp()) / "del_test.json"
    from core.models import ResearchProject
    from core.persistence import save_project, load_project, clear_project
    p = ResearchProject(
        title="Delete Test Project",
        idea="Testing that deleting a project correctly removes it from persistent storage",
    )
    save_project(p, tmp)
    assert load_project(tmp) is not None
    clear_project(tmp)
    assert load_project(tmp) is None


def test_new_project_after_delete():
    tmp = Path(tempfile.mkdtemp()) / "new_after_del.json"
    from core.models import ResearchProject
    from core.persistence import save_project, load_project, clear_project
    from core.task_engine import generate_initial_tasks
    p1 = ResearchProject(
        title="Original Project One",
        idea="First project that will be deleted before creating a replacement project",
    )
    save_project(p1, tmp)
    clear_project(tmp)
    p2 = ResearchProject(
        title="New Project Two Replacement",
        idea="Second project created after deleting the first one from persistent storage",
    )
    generate_initial_tasks(p2)
    save_project(p2, tmp)
    loaded = load_project(tmp)
    assert loaded.title == "New Project Two Replacement"
    assert len(loaded.tasks) == 8
    assert loaded.id != p1.id


def test_no_invented_scientific_content_in_tasks():
    from core.models import ResearchProject
    from core.task_engine import generate_initial_tasks
    forbidden = [
        "mmHg", "mg/dL", "p < 0.05", "95% CI", "hazard ratio",
        "relative risk", "odds ratio", "metformin", "aspirin",
        "ICD-10", "CONSORT", "STROBE",
    ]
    p = ResearchProject(
        title="No Scientific Content Test",
        idea="Testing that generated tasks contain no invented scientific content or claims",
    )
    generate_initial_tasks(p)
    for task in p.tasks:
        full_text = (task.title + task.description + task.why).lower()
        for term in forbidden:
            assert term.lower() not in full_text, (
                f"Invented content '{term}' found in task '{task.title}'"
            )


def test_audit_log_records_events():
    from core.audit import AuditLog
    log = AuditLog()
    log.record("PROJECT_CREATED", "Test project created")
    log.record("TASK_COMPLETED", "Task X completed")
    assert len(log.entries) == 2
    assert log.entries[0].event == "PROJECT_CREATED"


def test_audit_log_recent():
    from core.audit import AuditLog
    log = AuditLog()
    for i in range(25):
        log.record(f"EVENT_{i}", f"detail {i}")
    recent = log.recent(10)
    assert len(recent) == 10
    assert recent[-1].event == "EVENT_24"


def test_full_project_serialization_roundtrip():
    from core.models import (
        ResearchProject,
        ResearchQuestion,
        StudyDesign,
        StudyDesignType,
        Population,
        Exposure,
        Intervention,
        Comparator,
        Outcome,
        InclusionCriteria,
        ExclusionCriteria,
        SampleSizePlan,
        AnalysisPlan,
        ResearchStateEnum,
    )
    from core.task_engine import generate_initial_tasks, complete_task
    p = ResearchProject(
        title="Full Roundtrip Smoke Test",
        idea="Complete serialization roundtrip test covering every field in the project model",
    )
    generate_initial_tasks(p)
    p.research_question = ResearchQuestion(
        question_text="Does treatment X reduce outcome Y in population Z?",
        background="Established background rationale.",
    )
    p.study_design = StudyDesign(
        design_type=StudyDesignType.RCT, rationale="Gold standard"
    )
    p.population = Population(
        description="Adults 18-75 with condition Z", setting="Hospital"
    )
    p.exposure = Exposure(
        description="Exposure to treatment X", measurement_method="Records"
    )
    p.intervention = Intervention(
        description="Treatment X protocol", dosage_or_protocol="Once daily"
    )
    p.comparator = Comparator(description="Placebo control")
    p.primary_outcome = Outcome(
        name="Primary endpoint",
        description="Main outcome measured at follow-up",
        is_primary=True,
    )
    p.secondary_outcomes = [
        Outcome(
            name="Secondary endpoint",
            description="Supporting outcome measure",
        )
    ]
    p.inclusion_criteria = InclusionCriteria(
        criteria=["Age 18-75", "Condition Z"]
    )
    p.exclusion_criteria = ExclusionCriteria(criteria=["Pregnancy"])
    p.sample_size_plan = SampleSizePlan(planned_n=300)
    p.analysis_plan = AnalysisPlan(
        primary_analysis_description="Intention-to-treat"
    )
    p.state = ResearchStateEnum.DESIGN_SELECTED
    complete_task(p, p.tasks[0].id)
    json_str = p.model_dump_json(indent=2)
    restored = ResearchProject.model_validate_json(json_str)
    assert restored.id == p.id
    assert restored.title == p.title
    assert restored.research_question.question_text == p.research_question.question_text
    assert restored.study_design.design_type == StudyDesignType.RCT
    assert restored.population.description == p.population.description
    assert restored.primary_outcome.name == "Primary endpoint"
    assert len(restored.secondary_outcomes) == 1
    assert restored.inclusion_criteria.criteria == ["Age 18-75", "Condition Z"]
    assert restored.exclusion_criteria.criteria == ["Pregnancy"]
    assert restored.sample_size_plan.planned_n == 300
    assert restored.analysis_plan.primary_analysis_description == "Intention-to-treat"
    assert restored.state == ResearchStateEnum.DESIGN_SELECTED
    completed = [t for t in restored.tasks if t.status.value == "COMPLETED"]
    assert len(completed) == 1


# ══════════════════════════════════════════════
# SPRINT 2 SMOKE TESTS — 21 tests
# ══════════════════════════════════════════════

def test_s2_import_research_engine():
    from core import research_engine
    for fn in [
        "infer_framework_type",
        "build_framework",
        "validate_framework",
        "build_research_question",
        "recommend_study_design",
        "generate_framework_tasks",
        "generate_research_objectives",
        "check_question_defined_ready",
        "check_design_selected_ready",
    ]:
        assert hasattr(research_engine, fn)


def test_s2_import_research_framework_model():
    from core.models import (
        ResearchFramework,
        FrameworkCompleteness,
        StudyDesignRecommendation,
        FrameworkValidationResult,
    )
    assert ResearchFramework
    assert FrameworkCompleteness
    assert StudyDesignRecommendation
    assert FrameworkValidationResult


def test_s2_research_project_has_framework_field():
    from core.models import ResearchProject
    p = ResearchProject(
        title="Framework Field Test",
        idea="Testing that research project model has sprint 2 framework field",
    )
    assert hasattr(p, "research_framework")
    assert p.research_framework is None


def test_s2_pico_inferred_from_intervention():
    from core.models import ResearchProject, Intervention
    from core.research_engine import infer_framework_type
    p = ResearchProject(
        title="PICO Test",
        idea="Effect of drug treatment on outcomes in patients",
    )
    p.intervention = Intervention(description="Drug X treatment protocol")
    assert infer_framework_type(p) == "PICO"


def test_s2_peco_inferred_from_exposure():
    from core.models import ResearchProject, Exposure
    from core.research_engine import infer_framework_type
    p = ResearchProject(
        title="PECO Test",
        idea="Association between exposure and outcome in cohort",
    )
    p.exposure = Exposure(description="Environmental exposure to toxin")
    assert infer_framework_type(p) == "PECO"


def test_s2_build_framework_from_complete_pico_project():
    from core.models import ResearchProject, Population, Intervention, Comparator, Outcome
    from core.research_engine import build_framework
    p = ResearchProject(
        title="Full PICO Project",
        idea="Randomized trial of treatment in patients",
    )
    p.population = Population(description="Adults with condition Z aged 18-75")
    p.intervention = Intervention(description="Treatment X once daily")
    p.comparator = Comparator(description="Placebo control")
    p.primary_outcome = Outcome(
        name="Primary outcome",
        description="Outcome measured at follow-up",
        is_primary=True,
    )
    fw = build_framework(p)
    assert fw.framework_type == "PICO"
    assert fw.is_complete() is True


def test_s2_validate_framework_complete_status():
    from core.models import ResearchFramework, FrameworkCompleteness
    from core.research_engine import validate_framework
    fw = ResearchFramework(
        framework_type="PICO",
        population="Adults",
        intervention="Drug X",
        comparator="Placebo",
        outcome="Mortality",
    )
    result = validate_framework(fw)
    assert result.status == FrameworkCompleteness.COMPLETE
    assert result.completeness_score == 100


def test_s2_validate_framework_incomplete_status():
    from core.models import ResearchFramework, FrameworkCompleteness
    from core.research_engine import validate_framework
    fw = ResearchFramework(framework_type="PICO")
    result = validate_framework(fw)
    assert result.status == FrameworkCompleteness.INCOMPLETE
    assert result.completeness_score == 0


def test_s2_no_draft_question_when_incomplete():
    from core.models import ResearchFramework
    from core.research_engine import validate_framework
    fw = ResearchFramework(
        framework_type="PICO",
        population="Adults",
        intervention=None,
        comparator=None,
        outcome=None,
    )
    result = validate_framework(fw)
    assert result.draft_question is None


def test_s2_draft_question_generated_when_complete():
    from core.models import ResearchFramework
    from core.research_engine import validate_framework
    fw = ResearchFramework(
        framework_type="PICO",
        population="Adults with T2DM",
        intervention="Metformin",
        comparator="Placebo",
        outcome="All-cause mortality",
    )
    result = validate_framework(fw)
    assert result.draft_question is not None
    assert len(result.draft_question) > 20


def test_s2_pico_design_recommendation_is_rct():
    from core.models import ResearchFramework, StudyDesignType
    from core.research_engine import recommend_study_design
    fw = ResearchFramework(framework_type="PICO")
    rec = recommend_study_design(fw)
    assert rec.recommended_design == StudyDesignType.RCT
    assert rec.needs_expert_review is True


def test_s2_peco_design_recommendation_is_cohort():
    from core.models import ResearchFramework, StudyDesignType
    from core.research_engine import recommend_study_design
    fw = ResearchFramework(framework_type="PECO")
    rec = recommend_study_design(fw)
    assert rec.recommended_design == StudyDesignType.COHORT
    assert rec.needs_expert_review is True


def test_s2_missing_comparator_not_invented():
    from core.models import ResearchProject, Population, Intervention, Outcome
    from core.research_engine import build_framework
    p = ResearchProject(
        title="No Comparator Test",
        idea="Trial of drug treatment on outcomes in population of adults",
    )
    p.population = Population(description="Adults with condition Z")
    p.intervention = Intervention(description="Drug X")
    p.primary_outcome = Outcome(
        name="Mortality",
        description="Death from any cause",
        is_primary=True,
    )
    fw = build_framework(p)
    assert fw.comparator is None


def test_s2_task_generation_for_missing_fields():
    from core.models import ResearchProject, ResearchFramework
    from core.research_engine import generate_framework_tasks
    p = ResearchProject(
        title="Task Gen Test",
        idea="Testing framework task generation for missing fields",
    )
    fw = ResearchFramework(
        framework_type="PICO",
        population=None,
        intervention=None,
        comparator=None,
        outcome=None,
    )
    tasks = generate_framework_tasks(p, fw)
    assert len(tasks) > 0
    assert all(t.dependencies == [] for t in tasks)


def test_s2_no_duplicate_tasks():
    from core.models import ResearchProject, ResearchFramework
    from core.research_engine import generate_framework_tasks
    p = ResearchProject(
        title="No Duplicate Tasks Test",
        idea="Testing that framework does not generate duplicate task entries",
    )
    fw = ResearchFramework(
        framework_type="PICO",
        population=None,
        intervention=None,
        comparator=None,
        outcome=None,
    )
    tasks1 = generate_framework_tasks(p, fw)
    for t in tasks1:
        p.tasks.append(t)
    tasks2 = generate_framework_tasks(p, fw)
    assert len(tasks2) == 0


def test_s2_state_gate_blocks_idea_to_question_without_framework():
    from core.models import ResearchProject, ResearchStateEnum
    from core.state import StateGateError, transition_state_gated
    p = ResearchProject(
        title="Gate Test Project",
        idea="Testing that state gate blocks premature transition from idea state",
    )
    with pytest.raises(StateGateError):
        transition_state_gated(
            ResearchStateEnum.IDEA, ResearchStateEnum.QUESTION_DEFINED, p
        )


def test_s2_state_gate_allows_transition_when_ready():
    from core.models import (
        ResearchProject,
        ResearchStateEnum,
        ResearchQuestion,
        Population,
        Intervention,
        Comparator,
        Outcome,
    )
    from core.state import transition_state_gated
    from core.research_engine import build_framework
    p = ResearchProject(
        title="Gate Allow Test",
        idea="Effect of treatment X on outcomes in adults via randomized trial",
    )
    p.population = Population(description="Adults aged 18-75 with condition Z")
    p.intervention = Intervention(description="Treatment X once daily")
    p.comparator = Comparator(description="Placebo")
    p.primary_outcome = Outcome(
        name="Primary outcome",
        description="Outcome at follow-up",
        is_primary=True,
    )
    p.research_framework = build_framework(p)
    p.research_question = ResearchQuestion(
        question_text=(
            "Does treatment X reduce primary outcome in adults with condition Z?"
        )
    )
    result = transition_state_gated(
        ResearchStateEnum.IDEA, ResearchStateEnum.QUESTION_DEFINED, p
    )
    assert result == ResearchStateEnum.QUESTION_DEFINED


def test_s2_framework_serialization_roundtrip():
    from core.models import ResearchProject, ResearchState, Population, Intervention, Comparator, Outcome
    from core.research_engine import build_framework
    p = ResearchProject(
        title="Serialization Test",
        idea="Complete serialization test for sprint two framework integration",
    )
    p.population = Population(description="Adults with condition Z aged 18-75")
    p.intervention = Intervention(description="Treatment X protocol")
    p.comparator = Comparator(description="Placebo control")
    p.primary_outcome = Outcome(
        name="Primary outcome",
        description="Outcome at 12 months follow-up",
        is_primary=True,
    )
    p.research_framework = build_framework(p)
    state = ResearchState(project=p)
    json_str = state.model_dump_json()
    restored = ResearchState.model_validate_json(json_str)
    assert restored.project.research_framework is not None
    assert restored.project.research_framework.is_complete() is True


def test_s2_state_gate_import():
    from core.state import StateGateError, transition_state_gated
    assert StateGateError
    assert transition_state_gated


def test_s2_no_scientific_claims_in_recommendations():
    from core.models import ResearchFramework
    from core.research_engine import recommend_study_design
    forbidden = [
        "proven",
        "definitively correct",
        "guarantees",
        "will work",
        "is effective",
    ]
    for ft in ["PICO", "PECO"]:
        fw = ResearchFramework(framework_type=ft)
        rec = recommend_study_design(fw)
        full_text = (rec.rationale + " ".join(rec.limitations)).lower()
        for term in forbidden:
            assert term.lower() not in full_text, (
                f"Forbidden term '{term}' found in recommendation"
            )


def test_s2_schema_version_updated():
    from core.models import ResearchState
    # Schema version is 1.2.0 after Sprint 3
    assert ResearchState().schema_version == "1.2.0"


# ══════════════════════════════════════════════
# SPRINT 3 SMOKE TESTS — 18 tests
# ══════════════════════════════════════════════

def test_s3_import_literature_engine():
    from core import literature_engine
    for fn in [
        "build_search_strategy",
        "extract_search_terms",
        "build_boolean_query",
        "validate_search_strategy",
        "generate_literature_tasks",
    ]:
        assert hasattr(literature_engine, fn)


def test_s3_import_sprint3_models():
    from core.models import (
        LiteratureSearchStrategy,
        LiteratureRecord,
        ScreeningDecision,
        ScreeningDecisionEnum,
    )
    assert LiteratureSearchStrategy
    assert LiteratureRecord
    assert ScreeningDecision
    assert ScreeningDecisionEnum


def test_s3_project_has_sprint3_fields():
    from core.models import ResearchProject
    p = ResearchProject(
        title="Sprint 3 Fields Test",
        idea="Testing that research project model has all sprint 3 fields",
    )
    assert hasattr(p, "literature_search_strategy")
    assert p.literature_search_strategy is None
    assert hasattr(p, "literature_records")
    assert p.literature_records == []
    assert hasattr(p, "screening_decisions")
    assert p.screening_decisions == []


def test_s3_pico_strategy_builds_and_is_ready():
    from core.models import ResearchProject, ResearchFramework
    from core.literature_engine import build_search_strategy
    p = ResearchProject(
        title="PICO Strategy Test",
        idea="Testing PICO strategy generation with all required elements",
    )
    p.research_framework = ResearchFramework(
        framework_type="PICO",
        population="Adults with T2DM",
        intervention="Metformin",
        comparator="Placebo",
        outcome="Cardiovascular mortality",
    )
    strategy = build_search_strategy(p)
    assert strategy.ready_for_search is True
    assert strategy.framework_type == "PICO"


def test_s3_peco_strategy_builds_and_is_ready():
    from core.models import ResearchProject, ResearchFramework
    from core.literature_engine import build_search_strategy
    p = ResearchProject(
        title="PECO Strategy Test",
        idea="Testing PECO strategy generation with all required elements",
    )
    p.research_framework = ResearchFramework(
        framework_type="PECO",
        population="Adults aged 40-70",
        exposure="Smoking",
        comparator="Non-smokers",
        outcome="Lung cancer incidence",
    )
    strategy = build_search_strategy(p)
    assert strategy.ready_for_search is True
    assert strategy.framework_type == "PECO"


def test_s3_boolean_query_generated():
    from core.models import ResearchFramework
    from core.literature_engine import build_boolean_query
    fw = ResearchFramework(
        framework_type="PICO",
        population="Adults with T2DM",
        intervention="Metformin",
        comparator=None,
        outcome="Mortality",
    )
    query = build_boolean_query(fw)
    assert query is not None
    assert "AND" in query


def test_s3_no_boolean_query_when_incomplete():
    from core.models import ResearchFramework
    from core.literature_engine import build_boolean_query
    fw = ResearchFramework(
        framework_type="PICO",
        population=None,
        intervention="Metformin",
        comparator=None,
        outcome=None,
    )
    assert build_boolean_query(fw) is None


def test_s3_no_terms_invented_for_missing_fields():
    from core.models import ResearchFramework
    from core.literature_engine import extract_search_terms
    fw = ResearchFramework(
        framework_type="PICO",
        population=None,
        intervention="Metformin",
        comparator=None,
        outcome=None,
    )
    terms = extract_search_terms(fw)
    assert terms["population_terms"] == []
    assert terms["comparator_terms"] == []


def test_s3_no_fake_records_created():
    from core.models import ResearchProject, ResearchFramework
    from core.literature_engine import build_search_strategy
    p = ResearchProject(
        title="No Fake Records",
        idea="Testing that the engine never creates fake literature records automatically",
    )
    p.research_framework = ResearchFramework(
        framework_type="PICO",
        population="Adults",
        intervention="Drug X",
        comparator=None,
        outcome="Mortality",
    )
    build_search_strategy(p)
    assert p.literature_records == []


def test_s3_strategy_validation_complete():
    from core.models import ResearchProject, ResearchFramework
    from core.literature_engine import build_search_strategy, validate_search_strategy
    p = ResearchProject(
        title="Validation Complete Test",
        idea="Testing that a complete strategy passes validation successfully",
    )
    p.research_framework = ResearchFramework(
        framework_type="PICO",
        population="Adults with T2DM",
        intervention="Metformin",
        comparator="Placebo",
        outcome="Mortality",
    )
    strategy = build_search_strategy(p)
    is_valid, issues = validate_search_strategy(strategy)
    assert is_valid is True
    assert issues == []


def test_s3_strategy_validation_incomplete():
    from core.models import ResearchProject, ResearchFramework
    from core.literature_engine import build_search_strategy, validate_search_strategy
    p = ResearchProject(
        title="Validation Incomplete Test",
        idea="Testing that an incomplete strategy fails validation with informative messages",
    )
    p.research_framework = ResearchFramework(framework_type="PICO")
    strategy = build_search_strategy(p)
    is_valid, issues = validate_search_strategy(strategy)
    assert is_valid is False
    assert len(issues) > 0


def test_s3_generates_five_literature_tasks():
    from core.models import ResearchProject
    from core.literature_engine import generate_literature_tasks
    p = ResearchProject(
        title="Literature Tasks Test",
        idea="Testing that exactly five literature tasks are generated for a new project",
    )
    tasks = generate_literature_tasks(p)
    assert len(tasks) == 5


def test_s3_no_duplicate_literature_tasks():
    from core.models import ResearchProject
    from core.literature_engine import generate_literature_tasks
    p = ResearchProject(
        title="No Duplicate Lit Tasks",
        idea="Testing that literature task generation does not create duplicate tasks",
    )
    tasks1 = generate_literature_tasks(p)
    for t in tasks1:
        p.tasks.append(t)
    tasks2 = generate_literature_tasks(p)
    assert len(tasks2) == 0


def test_s3_strategy_serialization_roundtrip():
    from core.models import ResearchProject, ResearchFramework, ResearchState
    from core.literature_engine import build_search_strategy
    p = ResearchProject(
        title="Strategy Roundtrip Test",
        idea="Testing that literature search strategy survives a complete serialization roundtrip",
    )
    p.research_framework = ResearchFramework(
        framework_type="PICO",
        population="Adults with T2DM",
        intervention="Metformin",
        comparator="Placebo",
        outcome="Mortality",
    )
    p.literature_search_strategy = build_search_strategy(p)
    state = ResearchState(project=p)
    json_str = state.model_dump_json()
    restored = ResearchState.model_validate_json(json_str)
    assert restored.project.literature_search_strategy is not None
    assert restored.project.literature_search_strategy.ready_for_search is True


def test_s3_backward_compat_sprint1_project():
    from core.models import ResearchProject
    sprint1 = {
        "id": "old-1",
        "title": "Old Sprint 1 Project",
        "idea": "A legacy sprint one project without any sprint two or three fields",
        "created_at": "2024-01-01T00:00:00",
        "updated_at": "2024-01-01T00:00:00",
        "state": "IDEA",
        "tasks": [],
        "secondary_outcomes": [],
        "inclusion_criteria": {"criteria": []},
        "exclusion_criteria": {"criteria": []},
    }
    p = ResearchProject.model_validate(sprint1)
    assert p.research_framework is None
    assert p.literature_search_strategy is None
    assert p.literature_records == []


def test_s3_schema_version_is_1_2_0():
    from core.models import ResearchState
    assert ResearchState().schema_version == "1.2.0"


def test_s3_screening_decision_all_statuses():
    from core.models import ScreeningDecision, ScreeningDecisionEnum
    for dec in ScreeningDecisionEnum:
        d = ScreeningDecision(record_id="rec-test", decision=dec)
        assert d.decision == dec


def test_s3_literature_record_model_valid():
    from core.models import LiteratureRecord
    r = LiteratureRecord(
        title="A research study on outcomes",
        authors=["Author A"],
        journal="Journal X",
        pmid="99999999",
    )
    json_str = r.model_dump_json()
    restored = LiteratureRecord.model_validate_json(json_str)
    assert restored.title == "A research study on outcomes"
    assert restored.pmid == "99999999"


# ══════════════════════════════════════════════
# Test registry
# ══════════════════════════════════════════════

SPRINT1_TESTS = [
    ("S1-01. Import: config.settings", test_import_config_settings),
    ("S1-02. Import: core.models", test_import_core_models),
    ("S1-03. Import: core.state", test_import_core_state),
    ("S1-04. Import: core.task_engine", test_import_core_task_engine),
    ("S1-05. Import: core.persistence", test_import_core_persistence),
    ("S1-06. Import: core.audit", test_import_core_audit),
    ("S1-07. Import: ui.onboarding", test_import_ui_onboarding),
    ("S1-08. Import: ui.dashboard", test_import_ui_dashboard),
    ("S1-09. Import: app.py syntax", test_import_app_module),
    ("S1-10. Onboarding: creates project", test_onboarding_creates_project),
    ("S1-11. Onboarding: rejects short title", test_onboarding_rejects_short_title),
    ("S1-12. Onboarding: rejects short idea", test_onboarding_rejects_short_idea),
    ("S1-13. Tasks: exactly 8 initial tasks", test_exactly_eight_initial_tasks),
    ("S1-14. Tasks: all initial tasks TODO", test_initial_tasks_all_todo),
    ("S1-15. Tasks: critical priority present", test_initial_tasks_have_critical_priority),
    ("S1-16. Persistence: save and load", test_persistence_save_and_load),
    ("S1-17. Persistence: valid JSON output", test_persistence_file_is_valid_json),
    ("S1-18. Persistence: corrupt file → None", test_persistence_corrupt_file_returns_none),
    ("S1-19. Persistence: missing file → None", test_persistence_missing_file_returns_none),
    ("S1-20. Persistence: clear project", test_persistence_clear_project),
    ("S1-21. Persistence: survives restart", test_persistence_survives_restart),
    ("S1-22. Dashboard: research question", test_research_question_create_and_edit),
    ("S1-23. Dashboard: study design", test_study_design_select_and_save),
    ("S1-24. Dashboard: population", test_population_create_and_save),
    ("S1-25. Dashboard: exposure", test_exposure_create_and_save),
    ("S1-26. Dashboard: intervention", test_intervention_create_and_save),
    ("S1-27. Dashboard: comparator", test_comparator_create_and_save),
    ("S1-28. Dashboard: primary outcome", test_primary_outcome_create_and_save),
    ("S1-29. Dashboard: secondary outcomes", test_secondary_outcomes_create_and_save),
    ("S1-30. Dashboard: inclusion criteria", test_inclusion_criteria_create_and_save),
    ("S1-31. Dashboard: exclusion criteria", test_exclusion_criteria_create_and_save),
    ("S1-32. Dashboard: sample size plan", test_sample_size_plan_create_and_save),
    ("S1-33. Dashboard: analysis plan", test_analysis_plan_create_and_save),
    ("S1-34. Tasks: completion works", test_task_completion),
    ("S1-35. Tasks: dependency blocks completion", test_task_dependency_blocks_completion),
    ("S1-36. Tasks: completion after dep met", test_task_dependency_allows_completion_after_dep_met),
    ("S1-37. Tasks: initial tasks have no deps", test_initial_tasks_completable_independently),
    ("S1-38. State: IDEA → QUESTION_DEFINED", test_state_progression_idea_to_question),
    ("S1-39. State: full sequential chain", test_state_full_progression),
    ("S1-40. State: invalid transition blocked", test_invalid_state_transition_blocked),
    ("S1-41. State: progress index correct", test_state_progress_index),
    ("S1-42. Delete: clears persistence", test_delete_project_clears_persistence),
    ("S1-43. Delete: new project after delete", test_new_project_after_delete),
    ("S1-44. Safety: no invented science in tasks", test_no_invented_scientific_content_in_tasks),
    ("S1-45. Audit: records events", test_audit_log_records_events),
    ("S1-46. Audit: recent() slice", test_audit_log_recent),
    ("S1-47. Serialization: full roundtrip", test_full_project_serialization_roundtrip),
]

SPRINT2_TESTS = [
    ("S2-01. Import: core.research_engine", test_s2_import_research_engine),
    ("S2-02. Import: Sprint 2 models", test_s2_import_research_framework_model),
    ("S2-03. Model: research_framework field exists", test_s2_research_project_has_framework_field),
    ("S2-04. PICO: inferred from intervention field", test_s2_pico_inferred_from_intervention),
    ("S2-05. PECO: inferred from exposure field", test_s2_peco_inferred_from_exposure),
    ("S2-06. Framework: builds from complete PICO project", test_s2_build_framework_from_complete_pico_project),
    ("S2-07. Validation: complete status + score 100", test_s2_validate_framework_complete_status),
    ("S2-08. Validation: incomplete status + score 0", test_s2_validate_framework_incomplete_status),
    ("S2-09. Question: no draft when incomplete", test_s2_no_draft_question_when_incomplete),
    ("S2-10. Question: draft generated when complete", test_s2_draft_question_generated_when_complete),
    ("S2-11. Design: PICO → RCT suggestion", test_s2_pico_design_recommendation_is_rct),
    ("S2-12. Design: PECO → Cohort suggestion", test_s2_peco_design_recommendation_is_cohort),
    ("S2-13. Safety: missing comparator not invented", test_s2_missing_comparator_not_invented),
    ("S2-14. Tasks: generated for missing fields", test_s2_task_generation_for_missing_fields),
    ("S2-15. Tasks: no duplicates on second call", test_s2_no_duplicate_tasks),
    ("S2-16. State gate: blocks premature transition", test_s2_state_gate_blocks_idea_to_question_without_framework),
    ("S2-17. State gate: allows when ready", test_s2_state_gate_allows_transition_when_ready),
    ("S2-18. Serialization: framework roundtrip", test_s2_framework_serialization_roundtrip),
    ("S2-19. Import: StateGateError", test_s2_state_gate_import),
    ("S2-20. Safety: no scientific claims in design rec", test_s2_no_scientific_claims_in_recommendations),
    ("S2-21. Schema version is 1.2.0", test_s2_schema_version_updated),
]

SPRINT3_TESTS = [
    ("S3-01. Import: core.literature_engine", test_s3_import_literature_engine),
    ("S3-02. Import: Sprint 3 models", test_s3_import_sprint3_models),
    ("S3-03. Model: Sprint 3 fields on project", test_s3_project_has_sprint3_fields),
    ("S3-04. PICO: strategy builds and ready", test_s3_pico_strategy_builds_and_is_ready),
    ("S3-05. PECO: strategy builds and ready", test_s3_peco_strategy_builds_and_is_ready),
    ("S3-06. Boolean query generated", test_s3_boolean_query_generated),
    ("S3-07. No boolean query when incomplete", test_s3_no_boolean_query_when_incomplete),
    ("S3-08. Safety: no terms invented for missing", test_s3_no_terms_invented_for_missing_fields),
    ("S3-09. Safety: no fake records created", test_s3_no_fake_records_created),
    ("S3-10. Validation: complete strategy valid", test_s3_strategy_validation_complete),
    ("S3-11. Validation: incomplete strategy invalid", test_s3_strategy_validation_incomplete),
    ("S3-12. Tasks: exactly 5 literature tasks", test_s3_generates_five_literature_tasks),
    ("S3-13. Tasks: no duplicate literature tasks", test_s3_no_duplicate_literature_tasks),
    ("S3-14. Serialization: strategy roundtrip", test_s3_strategy_serialization_roundtrip),
    ("S3-15. Backward compat: Sprint 1 project loads", test_s3_backward_compat_sprint1_project),
    ("S3-16. Schema version is 1.2.0", test_s3_schema_version_is_1_2_0),
    ("S3-17. ScreeningDecision: all statuses valid", test_s3_screening_decision_all_statuses),
    ("S3-18. LiteratureRecord: model valid", test_s3_literature_record_model_valid),
]

ALL_TESTS = SPRINT1_TESTS + SPRINT2_TESTS + SPRINT3_TESTS


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("  SPRINT 1 + 2 + 3 PHASE 1 — STREAMLIT SMOKE TEST")
    print(
        f"  S1: {len(SPRINT1_TESTS)} | "
        f"S2: {len(SPRINT2_TESTS)} | "
        f"S3: {len(SPRINT3_TESTS)} | "
        f"Total: {len(ALL_TESTS)}"
    )
    print("=" * 70)

    for name, fn in ALL_TESTS:
        check(name, fn)

    passed = [r for r in results if r[0] == PASS]
    failed = [r for r in results if r[0] == FAIL]

    print()
    for status, name, detail in results:
        print(f"  {status}  {name}")
        if detail:
            for line in detail.strip().splitlines():
                print(f"         {line}")

    print()
    print("=" * 70)
    print(
        f"  TOTAL: {len(results)} | "
        f"PASSED: {len(passed)} | "
        f"FAILED: {len(failed)}"
    )
    print(
        f"  Sprint 1: {len(SPRINT1_TESTS)} | "
        f"Sprint 2: {len(SPRINT2_TESTS)} | "
        f"Sprint 3: {len(SPRINT3_TESTS)}"
    )
    print("=" * 70)

    if failed:
        sys.exit(1)
    else:
        print(
            "\n  🎉  All smoke tests passed. "
            "Sprint 3 Phase 1 is production-ready.\n"
        )
        sys.exit(0)
