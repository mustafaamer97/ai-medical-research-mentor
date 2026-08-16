# AI Research Co-Pilot

## Sprint 1 — Domain Foundation

---

### Product Vision

A domain-first Research Operating System that guides a researcher through
the lifecycle of a research project.

**Core philosophy:**
> AI assists, traces, validates, and recommends —  
> but the researcher remains the decision-maker and owner of the research.

The application does **not** autonomously conduct research or invent
scientific information. Every important research decision is attributable
to researcher-provided information or a clearly identified system
recommendation.

---

### Sprint 1 Scope

Sprint 1 establishes the **canonical domain foundation** only.

- ✅ Canonical domain model (`ResearchProject`)
- ✅ All supporting domain models
- ✅ Canonical enumerations (single source, no duplicates)
- ✅ Project domain service layer
- ✅ Comprehensive test suite
- ✅ Minimal Streamlit entry point

**Not in Sprint 1:**
- Full UI
- AI/LLM integration
- Persistence / database
- Literature management
- Statistical computation

---

### Architecture

```
research_copilot/
│
├── app.py                  # Streamlit entry point (Sprint 1: minimal)
│
├── core/
│   ├── __init__.py
│   ├── enums.py            # All canonical enums (ONE definition each)
│   ├── models.py           # All canonical domain models
│   └── project.py          # Project domain service layer
│
├── services/
│   └── __init__.py         # Reserved for Sprint 2+ service integrations
│
├── tests/
│   ├── test_models.py      # Domain model tests
│   └── test_project.py     # Project service tests
│
└── README.md
```

---

### Canonical Domain Model

#### Central object

```
ResearchProject
```

**Single source of truth.**  
Everything either belongs to, derives from, is associated with,
or represents an auditable action on a `ResearchProject`.

#### Lifecycle

Tracked by exactly **one** field: `state` (`ProjectState`).

There is no competing `status` field.

```
IDEA → QUESTION_DEFINED → DESIGN_SELECTED → PROTOCOL_READY
```

#### ResearchProject fields

| Field | Type | Notes |
|---|---|---|
| `id` | `str` (UUID) | Auto-generated, stable, protected |
| `title` | `str` | Min 5 chars |
| `idea` | `str` | Min 20 chars |
| `created_at` | `datetime` (UTC) | Auto-set, protected |
| `updated_at` | `datetime` (UTC) | Updated on every mutation |
| `state` | `ProjectState` | Single lifecycle field |
| `research_question` | `ResearchQuestion?` | None until researcher provides it |
| `study_design` | `StudyDesign?` | None until researcher selects it |
| `population` | `Population?` | None until researcher defines it |
| `exposure` | `Exposure?` | None until researcher defines it |
| `intervention` | `Intervention?` | None until researcher defines it |
| `comparator` | `Comparator?` | None until researcher defines it |
| `primary_outcome` | `Outcome?` | Must have `is_primary=True` |
| `secondary_outcomes` | `List[Outcome]` | Default empty |
| `inclusion_criteria` | `InclusionCriteria` | Default empty |
| `exclusion_criteria` | `ExclusionCriteria` | Default empty |
| `sample_size_plan` | `SampleSizePlan?` | None until researcher provides it |
| `analysis_plan` | `AnalysisPlan?` | None until researcher provides it |
| `tasks` | `List[ResearchTask]` | Default empty |

#### Supporting models

| Model | Key fields |
|---|---|
| `ResearchQuestion` | `question_text` (min 10 chars), `background?` |
| `StudyDesign` | `design_type` (`StudyDesignType`), `rationale?` |
| `Population` | `description`, `setting?` |
| `Exposure` | `description`, `measurement_method?` |
| `Intervention` | `description`, `dosage_or_protocol?` |
| `Comparator` | `description` |
| `Outcome` | `name`, `description`, `measurement_method?`, `time_point?`, `is_primary` |
| `InclusionCriteria` | `criteria: List[str]` (empty strings removed) |
| `ExclusionCriteria` | `criteria: List[str]` (empty strings removed) |
| `SampleSizePlan` | `planned_n?`, `rationale?`, `notes?` |
| `AnalysisPlan` | `primary_analysis_description?`, `secondary_analyses`, `notes?` |
| `ResearchTask` | `id`, `title`, `status`, `priority`, `why?`, `dependencies`, `created_at`, `completed_at?` |

#### Canonical enumerations

| Enum | Values |
|---|---|
| `ProjectState` | `IDEA`, `QUESTION_DEFINED`, `DESIGN_SELECTED`, `PROTOCOL_READY` |
| `StudyDesignType` | `CROSS_SECTIONAL`, `COHORT`, `CASE_CONTROL`, `RANDOMIZED_CONTROLLED_TRIAL`, `DIAGNOSTIC`, `OTHER` |
| `TaskStatus` | `TODO`, `IN_PROGRESS`, `COMPLETED`, `BLOCKED` |
| `TaskPriority` | `LOW`, `MEDIUM`, `HIGH`, `CRITICAL` |

Each enum is defined **once**. No aliases. No duplicates.

---

### No-Invention Principle

The system **never** silently invents:

- Population details
- Intervention details
- Comparator details
- Outcomes
- Study design
- Eligibility criteria
- Sample size figures
- Statistical methods
- Literature records
- Scientific conclusions

If information is missing, it is represented as `None`.

---

### Project Domain Service

```python
from research_copilot.core.project import create_project, update_project, touch

project = create_project(title="My Study", idea="...")
update_project(project, {"state": ProjectState.QUESTION_DEFINED, ...})
touch(project)  # refreshes updated_at only
```

Protected fields (`id`, `created_at`) cannot be modified via `update_project()`.

---

### Running Tests

```bash
pytest research_copilot/tests/ -v
```

Expected: **0 failures**

---

### Running the Application

```bash
streamlit run research_copilot/app.py
```

---

### Development Principles

1. **ResearchProject is the single source of truth**
2. **One lifecycle field: `state`** — no competing `status`
3. **One canonical enum per concept** — no duplicates
4. **No invention** — missing data is `None`
5. **Domain logic is independent of UI**
6. **Tests are deterministic**
7. **Sprint 1 is frozen** — Sprint 2 builds on top without refactoring Sprint 1

---

*AI Research Co-Pilot · Sprint 1 · Domain Foundation*
