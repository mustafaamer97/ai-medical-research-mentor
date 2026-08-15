"""
core/state.py
=============
Unified Research Lifecycle State Machine
----------------------------------------
Single source of truth:
    core.models.ResearchProject.state
    core.models.ResearchStateEnum
This module provides:
- ResearchState compatibility alias
- Canonical research lifecycle
- Explicit transition topology
- State validation
- State progress helpers
- Gate validation
- Audited transitions
- StateManager coordinator
- Sprint 1 / 2 / 3 compatible public helpers
IMPORTANT
---------
The state machine never invents research information.
Gate decisions are based only on fields actually present on the supplied
ResearchProject and its nested models.
The canonical state enum is ResearchStateEnum from core.models.
"""
from __future__ import annotations
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple
# ============================================================================
# Imports
# ============================================================================
try:
    from core.models import (
        ResearchProject,
        ResearchStateEnum,
        ResearchFramework,
        LiteratureSearchStrategy,
        ScreeningDecisionEnum,
    )
except ImportError:  # pragma: no cover
    ResearchProject = None  # type: ignore
    ResearchStateEnum = None  # type: ignore
    ResearchFramework = None  # type: ignore
    LiteratureSearchStrategy = None  # type: ignore
    ScreeningDecisionEnum = None  # type: ignore
# ============================================================================
# Compatibility
# ============================================================================
# The previous implementation exposed ResearchState.
# Keep that public name so existing imports do not immediately break.
ResearchState = ResearchStateEnum
# ============================================================================
# Exceptions
# ============================================================================
class StateGateError(Exception):
    """Raised when a state gate prevents a transition."""
    def __init__(
        self,
        message: str,
        reasons: Optional[List[str]] = None,
        from_state: Optional[str] = None,
        to_state: Optional[str] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.reasons = reasons or []
        self.from_state = from_state
        self.to_state = to_state
    def __str__(self) -> str:
        if self.reasons:
            return f"{self.message} | Reasons: {'; '.join(self.reasons)}"
        return self.message
    def to_dict(self) -> Dict[str, Any]:
        return {
            "error": "StateGateError",
            "message": self.message,
            "reasons": self.reasons,
            "from_state": self.from_state,
            "to_state": self.to_state,
        }
class InvalidStateTransitionError(Exception):
    """Raised when a transition is not allowed by the state topology."""
    def __init__(
        self,
        message: str,
        from_state: Optional[str] = None,
        to_state: Optional[str] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.from_state = from_state
        self.to_state = to_state
    def __str__(self) -> str:
        return (
            f"{self.message} "
            f"(from={self.from_state!r} -> to={self.to_state!r})"
        )
    def to_dict(self) -> Dict[str, Any]:
        return {
            "error": "InvalidStateTransitionError",
            "message": self.message,
            "from_state": self.from_state,
            "to_state": self.to_state,
        }
# ============================================================================
# Canonical lifecycle
# ============================================================================
all_states_in_order: List[ResearchStateEnum] = [
    ResearchStateEnum.IDEA,
    ResearchStateEnum.QUESTION_DEFINED,
    ResearchStateEnum.DESIGN_SELECTED,
    ResearchStateEnum.PROTOCOL_READY,
    ResearchStateEnum.LITERATURE_SEARCH,
    ResearchStateEnum.SCREENING,
    ResearchStateEnum.DATA_COLLECTION,
    ResearchStateEnum.DATA_READY,
    ResearchStateEnum.ANALYSIS_PLAN_LOCKED,
    ResearchStateEnum.ANALYSIS_COMPLETE,
    ResearchStateEnum.MANUSCRIPT_DRAFT,
    ResearchStateEnum.AUDIT,
    ResearchStateEnum.JOURNAL_SELECTION,
    ResearchStateEnum.READY_FOR_SUBMISSION,
]
# ============================================================================
# State topology
# ============================================================================
ALLOWED_TRANSITIONS: Dict[
    ResearchStateEnum,
    List[ResearchStateEnum],
] = {
    ResearchStateEnum.IDEA: [
        ResearchStateEnum.QUESTION_DEFINED,
    ],
    ResearchStateEnum.QUESTION_DEFINED: [
        ResearchStateEnum.DESIGN_SELECTED,
        ResearchStateEnum.IDEA,
    ],
    ResearchStateEnum.DESIGN_SELECTED: [
        ResearchStateEnum.PROTOCOL_READY,
        ResearchStateEnum.QUESTION_DEFINED,
    ],
    ResearchStateEnum.PROTOCOL_READY: [
        ResearchStateEnum.LITERATURE_SEARCH,
        ResearchStateEnum.DESIGN_SELECTED,
    ],
    ResearchStateEnum.LITERATURE_SEARCH: [
        ResearchStateEnum.SCREENING,
        ResearchStateEnum.PROTOCOL_READY,
    ],
    ResearchStateEnum.SCREENING: [
        ResearchStateEnum.DATA_COLLECTION,
        ResearchStateEnum.LITERATURE_SEARCH,
    ],
    ResearchStateEnum.DATA_COLLECTION: [
        ResearchStateEnum.DATA_READY,
        ResearchStateEnum.SCREENING,
    ],
    ResearchStateEnum.DATA_READY: [
        ResearchStateEnum.ANALYSIS_PLAN_LOCKED,
        ResearchStateEnum.DATA_COLLECTION,
    ],
    ResearchStateEnum.ANALYSIS_PLAN_LOCKED: [
        ResearchStateEnum.ANALYSIS_COMPLETE,
        ResearchStateEnum.DATA_READY,
    ],
    ResearchStateEnum.ANALYSIS_COMPLETE: [
        ResearchStateEnum.MANUSCRIPT_DRAFT,
        ResearchStateEnum.ANALYSIS_PLAN_LOCKED,
    ],
    ResearchStateEnum.MANUSCRIPT_DRAFT: [
        ResearchStateEnum.AUDIT,
        ResearchStateEnum.ANALYSIS_COMPLETE,
    ],
    ResearchStateEnum.AUDIT: [
        ResearchStateEnum.JOURNAL_SELECTION,
        ResearchStateEnum.MANUSCRIPT_DRAFT,
    ],
    ResearchStateEnum.JOURNAL_SELECTION: [
        ResearchStateEnum.READY_FOR_SUBMISSION,
        ResearchStateEnum.AUDIT,
    ],
    ResearchStateEnum.READY_FOR_SUBMISSION: [
        ResearchStateEnum.JOURNAL_SELECTION,
    ],
}
# ============================================================================
# Internal helpers
# ============================================================================
def _now_iso() -> str:
    """Return the current UTC timestamp as ISO-8601."""
    return datetime.now(timezone.utc).isoformat()
def _coerce_state(value: Any) -> ResearchStateEnum:
    """
    Convert supported state representations into ResearchStateEnum.
    Accepted:
        - ResearchStateEnum
        - ResearchState alias
        - enum-like objects with .value
        - state values such as "IDEA"
        - state values such as "idea"
    """
    if isinstance(value, ResearchStateEnum):
        return value
    if value is not None and hasattr(value, "value"):
        value = value.value
    if isinstance(value, str):
        raw = value.strip()
        # Exact enum value.
        for state in ResearchStateEnum:
            if raw == state.value:
                return state
        # Case-insensitive enum value.
        for state in ResearchStateEnum:
            if raw.lower() == state.value.lower():
                return state
        # Enum member name.
        try:
            return ResearchStateEnum[raw.upper()]
        except KeyError:
            pass
    raise ValueError(
        f"Cannot coerce {value!r} to ResearchStateEnum. "
        f"Valid values: {[state.value for state in ResearchStateEnum]}"
    )
def _get_project_state(project: Any) -> ResearchStateEnum:
    """Read the canonical state from project.state."""
    if not hasattr(project, "state"):
        raise InvalidStateTransitionError(
            "Project does not expose the canonical 'state' attribute."
        )
    try:
        return _coerce_state(project.state)
    except ValueError as exc:
        raise InvalidStateTransitionError(
            f"Project has an invalid state: {project.state!r}",
            from_state=str(project.state),
        ) from exc
def _apply_state(
    project: Any,
    target: ResearchStateEnum,
) -> None:
    """Apply the canonical state to project.state."""
    if not hasattr(project, "state"):
        raise InvalidStateTransitionError(
            "Project does not expose the canonical 'state' attribute."
        )
    project.state = target
    # ResearchProject exposes touch(), so keep updated_at synchronized.
    touch = getattr(project, "touch", None)
    if callable(touch):
        touch()
def _clean_text(value: Any) -> str:
    """Return a safely normalized non-empty string."""
    if value is None:
        return ""
    return str(value).strip()
def _has_non_empty_text(value: Any) -> bool:
    return bool(_clean_text(value))
# ============================================================================
# Progress helpers
# ============================================================================
def state_progress_index(state: Any) -> int:
    """
    Return the zero-based position in the canonical lifecycle.
    Returns -1 for invalid/special values.
    """
    try:
        coerced = _coerce_state(state)
    except ValueError:
        return -1
    try:
        return all_states_in_order.index(coerced)
    except ValueError:
        return -1
# ============================================================================
# Transition validation
# ============================================================================
def validate_transition(
    from_state: Any,
    to_state: Any,
) -> bool:
    """
    Validate a direct state transition.
    Raises InvalidStateTransitionError when invalid.
    """
    try:
        source = _coerce_state(from_state)
    except ValueError as exc:
        raise InvalidStateTransitionError(
            f"Invalid source state: {from_state!r}",
            from_state=str(from_state),
            to_state=str(to_state),
        ) from exc
    try:
        target = _coerce_state(to_state)
    except ValueError as exc:
        raise InvalidStateTransitionError(
            f"Invalid target state: {to_state!r}",
            from_state=source.value,
            to_state=str(to_state),
        ) from exc
    if target not in ALLOWED_TRANSITIONS.get(source, []):
        raise InvalidStateTransitionError(
            (
                f"Transition from '{source.value}' "
                f"to '{target.value}' is not permitted."
            ),
            from_state=source.value,
            to_state=target.value,
        )
    return True
def get_valid_next_states(
    current_state: Any,
) -> List[ResearchStateEnum]:
    """Return all topologically valid next states."""
    try:
        state = _coerce_state(current_state)
    except ValueError:
        return []
    return list(ALLOWED_TRANSITIONS.get(state, []))
def is_valid_transition(
    from_state: Any,
    to_state: Any,
) -> bool:
    """Boolean-only transition query. Never raises."""
    try:
        source = _coerce_state(from_state)
        target = _coerce_state(to_state)
    except ValueError:
        return False
    return target in ALLOWED_TRANSITIONS.get(source, [])
# ============================================================================
# Audit
# ============================================================================
class TransitionRecord:
    """Serializable state transition audit record."""
    def __init__(
        self,
        from_state: ResearchStateEnum,
        to_state: ResearchStateEnum,
        triggered_by: str = "system",
        note: str = "",
        gated: bool = False,
        gate_passed: bool = True,
        gate_reasons: Optional[List[str]] = None,
    ) -> None:
        self.from_state = from_state
        self.to_state = to_state
        self.triggered_by = triggered_by
        self.note = note
        self.gated = gated
        self.gate_passed = gate_passed
        self.gate_reasons = gate_reasons or []
        self.timestamp = _now_iso()
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event": "state_transition",
            "from_state": self.from_state.value,
            "to_state": self.to_state.value,
            "triggered_by": self.triggered_by,
            "note": self.note,
            "gated": self.gated,
            "gate_passed": self.gate_passed,
            "gate_reasons": list(self.gate_reasons),
            "timestamp": self.timestamp,
        }
def _write_audit(
    project: Any,
    record: TransitionRecord,
    external_log: Optional[List[Dict[str, Any]]] = None,
) -> None:
    """
    Write audit entry to an existing project audit collection if available.
    If the project does not expose one, only external_log is used.
    """
    entry = record.to_dict()
    # Preserve compatibility with future/older project models.
    for attr in ("audit_log", "audit_trail", "history"):
        trail = getattr(project, attr, None)
        if isinstance(trail, list):
            trail.append(entry)
            break
    if external_log is not None:
        external_log.append(entry)
# ============================================================================
# Core transitions
# ============================================================================
def transition_state(
    project: Any,
    to_state: Any,
    *,
    triggered_by: str = "system",
    note: str = "",
    _audit_log: Optional[List[Dict[str, Any]]] = None,
) -> Any:
    """
    Perform an unconditional topology-validated transition.
    This function does NOT perform research gates.
    """
    current = _get_project_state(project)
    try:
        target = _coerce_state(to_state)
    except ValueError as exc:
        raise InvalidStateTransitionError(
            f"Invalid target state: {to_state!r}",
            from_state=current.value,
            to_state=str(to_state),
        ) from exc
    validate_transition(current, target)
    record = TransitionRecord(
        from_state=current,
        to_state=target,
        triggered_by=triggered_by,
        note=note,
        gated=False,
        gate_passed=True,
    )
    _apply_state(project, target)
    _write_audit(project, record, _audit_log)
    return project
def transition_state_gated(
    project: Any,
    to_state: Any,
    gate_fn: Callable[[Any], Tuple[bool, List[str]]],
    *,
    triggered_by: str = "system",
    note: str = "",
    raise_on_fail: bool = True,
    _audit_log: Optional[List[Dict[str, Any]]] = None,
) -> Tuple[Any, bool, List[str]]:
    """
    Evaluate a supplied gate before performing a valid transition.
    Gate evaluation is entirely delegated to gate_fn.
    """
    current = _get_project_state(project)
    try:
        target = _coerce_state(to_state)
    except ValueError as exc:
        raise InvalidStateTransitionError(
            f"Invalid target state: {to_state!r}",
            from_state=current.value,
            to_state=str(to_state),
        ) from exc
    passed, reasons = gate_fn(project)
    reasons = list(reasons or [])
    record = TransitionRecord(
        from_state=current,
        to_state=target,
        triggered_by=triggered_by,
        note=note,
        gated=True,
        gate_passed=passed,
        gate_reasons=reasons,
    )
    if not passed:
        _write_audit(project, record, _audit_log)
        if raise_on_fail:
            raise StateGateError(
                (
                    f"Gate check failed: transition from "
                    f"'{current.value}' to '{target.value}' is blocked."
                ),
                reasons=reasons,
                from_state=current.value,
                to_state=target.value,
            )
        return project, False, reasons
    # Only after gate passes do we validate topology.
    validate_transition(current, target)
    _apply_state(project, target)
    _write_audit(project, record, _audit_log)
    return project, True, []
# ============================================================================
# StateManager
# ============================================================================
class StateManager:
    """
    Project-level coordinator around the canonical ResearchProject.state.
    """
    def __init__(self, project: Any) -> None:
        self._project = project
        self._audit: List[Dict[str, Any]] = []
    @property
    def project(self) -> Any:
        return self._project
    @property
    def current_state(self) -> ResearchStateEnum:
        return _get_project_state(self._project)
    @property
    def audit_trail(self) -> List[Dict[str, Any]]:
        for attr in ("audit_log", "audit_trail", "history"):
            trail = getattr(self._project, attr, None)
            if isinstance(trail, list):
                return trail
        return list(self._audit)
    def transition(
        self,
        to_state: Any,
        *,
        triggered_by: str = "system",
        note: str = "",
    ) -> "StateManager":
        transition_state(
            self._project,
            to_state,
            triggered_by=triggered_by,
            note=note,
            _audit_log=self._audit,
        )
        return self
    def transition_gated(
        self,
        to_state: Any,
        gate_fn: Callable[[Any], Tuple[bool, List[str]]],
        *,
        triggered_by: str = "system",
        note: str = "",
        raise_on_fail: bool = True,
    ) -> Tuple[bool, List[str]]:
        _, passed, reasons = transition_state_gated(
            self._project,
            to_state,
            gate_fn,
            triggered_by=triggered_by,
            note=note,
            raise_on_fail=raise_on_fail,
            _audit_log=self._audit,
        )
        return passed, reasons
    def allowed_next_states(self) -> List[ResearchStateEnum]:
        return get_valid_next_states(self.current_state)
    def can_transition_to(self, to_state: Any) -> bool:
        return is_valid_transition(self.current_state, to_state)
    def is_terminal(self) -> bool:
        return self.current_state == ResearchStateEnum.READY_FOR_SUBMISSION
    def is_error(self) -> bool:
        # ResearchStateEnum currently has no ERROR state.
        return False
    def state_index(self) -> int:
        return state_progress_index(self.current_state)
    def is_before(self, other: Any) -> bool:
        my_index = state_progress_index(self.current_state)
        try:
            other_index = state_progress_index(other)
        except Exception:
            return False
        return (
            my_index != -1
            and other_index != -1
            and my_index < other_index
        )
    def is_after(self, other: Any) -> bool:
        my_index = state_progress_index(self.current_state)
        try:
            other_index = state_progress_index(other)
        except Exception:
            return False
        return (
            my_index != -1
            and other_index != -1
            and my_index > other_index
        )
    def reset_to_idea(
        self,
        *,
        triggered_by: str = "system",
        note: str = "Manual reset to IDEA.",
    ) -> "StateManager":
        if self.current_state != ResearchStateEnum.QUESTION_DEFINED:
            raise InvalidStateTransitionError(
                (
                    "reset_to_idea() is only permitted from "
                    "QUESTION_DEFINED."
                ),
                from_state=self.current_state.value,
                to_state=ResearchStateEnum.IDEA.value,
            )
        return self.transition(
            ResearchStateEnum.IDEA,
            triggered_by=triggered_by,
            note=note,
        )
    def __repr__(self) -> str:
        return (
            "StateManager("
            f"project_id={getattr(self._project, 'id', 'unknown')!r}, "
            f"state={self.current_state.value!r})"
        )
# ============================================================================
# Gate helpers
# ============================================================================
def gate_question_defined(
    project: Any,
) -> Tuple[bool, List[str]]:
    """
    IDEA -> QUESTION_DEFINED
    Requires a populated ResearchQuestion object with question_text.
    """
    reasons: List[str] = []
    question = getattr(project, "research_question", None)
    if question is None:
        reasons.append(
            "A research question must be defined before leaving IDEA."
        )
        return False, reasons
    question_text = getattr(question, "question_text", None)
    if not _has_non_empty_text(question_text):
        reasons.append(
            "Research question text is required."
        )
    return not reasons, reasons
def gate_design_selected(
    project: Any,
) -> Tuple[bool, List[str]]:
    """
    QUESTION_DEFINED -> DESIGN_SELECTED
    Requires a StudyDesign object.
    """
    reasons: List[str] = []
    design = getattr(project, "study_design", None)
    if design is None:
        reasons.append(
            "A study design must be selected before advancing."
        )
    return not reasons, reasons
def gate_protocol_ready(
    project: Any,
) -> Tuple[bool, List[str]]:
    """
    DESIGN_SELECTED -> PROTOCOL_READY
    Validates the core protocol components that are explicitly represented
    in ResearchProject.
    """
    reasons: List[str] = []
    if getattr(project, "study_design", None) is None:
        reasons.append("Study design is required.")
    if getattr(project, "population", None) is None:
        reasons.append("Population is required.")
    if getattr(project, "primary_outcome", None) is None:
        reasons.append("Primary outcome is required.")
    if getattr(project, "inclusion_criteria", None) is None:
        reasons.append("Inclusion criteria object is required.")
    if getattr(project, "exclusion_criteria", None) is None:
        reasons.append("Exclusion criteria object is required.")
    return not reasons, reasons
def gate_literature_search(
    project: Any,
) -> Tuple[bool, List[str]]:
    """
    PROTOCOL_READY -> LITERATURE_SEARCH
    Requires a valid LiteratureSearchStrategy marked ready_for_search.
    """
    reasons: List[str] = []
    strategy = getattr(
        project,
        "literature_search_strategy",
        None,
    )
    if strategy is None:
        reasons.append(
            "A literature search strategy must be created."
        )
        return False, reasons
    ready = getattr(strategy, "ready_for_search", False)
    if ready is not True:
        reasons.append(
            "Literature search strategy is not ready for search."
        )
    boolean_query = getattr(strategy, "boolean_query", None)
    if not _has_non_empty_text(boolean_query):
        reasons.append(
            "A Boolean literature search query is required."
        )
    return not reasons, reasons
def gate_screening(
    project: Any,
) -> Tuple[bool, List[str]]:
    """
    LITERATURE_SEARCH -> SCREENING
    Requires actual literature records.
    No synthetic records are accepted.
    """
    reasons: List[str] = []
    records = getattr(project, "literature_records", None)
    if not isinstance(records, list) or len(records) == 0:
        reasons.append(
            "At least one retrieved literature record is required "
            "before screening."
        )
    return not reasons, reasons
def gate_data_collection(
    project: Any,
) -> Tuple[bool, List[str]]:
    """
    SCREENING -> DATA_COLLECTION
    Requires screening decisions to exist and contain at least one
    non-PENDING decision.
    """
    reasons: List[str] = []
    decisions = getattr(
        project,
        "screening_decisions",
        None,
    )
    if not isinstance(decisions, list) or len(decisions) == 0:
        reasons.append(
            "Screening decisions are required before data collection."
        )
        return False, reasons
    non_pending = 0
    for decision in decisions:
        value = getattr(decision, "decision", None)
        if value is None:
            continue
        try:
            normalized = (
                value.value
                if hasattr(value, "value")
                else str(value)
            )
            if normalized.upper() != "PENDING":
                non_pending += 1
        except Exception:
            continue
    if non_pending == 0:
        reasons.append(
            "At least one screening decision must be finalized."
        )
    return not reasons, reasons
def gate_data_ready(
    project: Any,
) -> Tuple[bool, List[str]]:
    """
    DATA_COLLECTION -> DATA_READY
    The current ResearchProject schema does not yet contain a dedicated
    extracted-data field.
    Therefore this gate only verifies that the project reached the state
    with screening decisions available. It does not fabricate or infer
    extracted data.
    """
    reasons: List[str] = []
    decisions = getattr(
        project,
        "screening_decisions",
        None,
    )
    if not isinstance(decisions, list) or len(decisions) == 0:
        reasons.append(
            "Screening decisions must be available before data can "
            "be marked ready."
        )
    return not reasons, reasons
def gate_analysis_plan_locked(
    project: Any,
) -> Tuple[bool, List[str]]:
    """
    DATA_READY -> ANALYSIS_PLAN_LOCKED
    Requires an AnalysisPlan with a primary analysis description.
    """
    reasons: List[str] = []
    analysis_plan = getattr(
        project,
        "analysis_plan",
        None,
    )
    if analysis_plan is None:
        reasons.append(
            "An analysis plan must be defined before it can be locked."
        )
        return False, reasons
    primary = getattr(
        analysis_plan,
        "primary_analysis_description",
        None,
    )
    if not _has_non_empty_text(primary):
        reasons.append(
            "Primary analysis description is required."
        )
    return not reasons, reasons
def gate_analysis_complete(
    project: Any,
) -> Tuple[bool, List[str]]:
    """
    ANALYSIS_PLAN_LOCKED -> ANALYSIS_COMPLETE
    The current ResearchProject model does not yet expose a dedicated
    analysis-results object.
    Therefore this gate checks that an analysis plan exists and has a
    primary analysis description. It does not claim that numerical
    analysis has actually been performed.
    """
    reasons: List[str] = []
    analysis_plan = getattr(
        project,
        "analysis_plan",
        None,
    )
    if analysis_plan is None:
        reasons.append(
            "Analysis plan must exist before analysis can be marked complete."
        )
        return False, reasons
    primary = getattr(
        analysis_plan,
        "primary_analysis_description",
        None,
    )
    if not _has_non_empty_text(primary):
        reasons.append(
            "Primary analysis description is required."
        )
    return not reasons, reasons
def gate_manuscript_draft(
    project: Any,
) -> Tuple[bool, List[str]]:
    """
    ANALYSIS_COMPLETE -> MANUSCRIPT_DRAFT
    The current ResearchProject schema does not yet have a manuscript
    field.
    This gate therefore requires the analysis plan and research question
    to exist, without pretending that a manuscript was generated.
    """
    reasons: List[str] = []
    if getattr(project, "research_question", None) is None:
        reasons.append(
            "Research question is required before manuscript drafting."
        )
    if getattr(project, "analysis_plan", None) is None:
        reasons.append(
            "Analysis plan is required before manuscript drafting."
        )
    return not reasons, reasons
def gate_audit(
    project: Any,
) -> Tuple[bool, List[str]]:
    """
    MANUSCRIPT_DRAFT -> AUDIT
    The current schema does not contain manuscript content or an audit
    result object, so this gate only verifies the upstream state data
    required to enter audit.
    """
    reasons: List[str] = []
    if getattr(project, "research_question", None) is None:
        reasons.append("Research question is missing.")
    if getattr(project, "analysis_plan", None) is None:
        reasons.append("Analysis plan is missing.")
    return not reasons, reasons
def gate_journal_selection(
    project: Any,
) -> Tuple[bool, List[str]]:
    """
    AUDIT -> JOURNAL_SELECTION
    No journal field currently exists in ResearchProject, so the gate
    does not fabricate one. It only verifies that the project contains
    the upstream research components.
    """
    reasons: List[str] = []
    if getattr(project, "research_question", None) is None:
        reasons.append("Research question is missing.")
    if getattr(project, "study_design", None) is None:
        reasons.append("Study design is missing.")
    return not reasons, reasons
def gate_ready_for_submission(
    project: Any,
) -> Tuple[bool, List[str]]:
    """
    JOURNAL_SELECTION -> READY_FOR_SUBMISSION
    Requires the core research artifacts represented by the current model.
    """
    reasons: List[str] = []
    if getattr(project, "research_question", None) is None:
        reasons.append("Research question is required.")
    if getattr(project, "study_design", None) is None:
        reasons.append("Study design is required.")
    if getattr(project, "research_framework", None) is None:
        reasons.append("Research framework is required.")
    if getattr(project, "primary_outcome", None) is None:
        reasons.append("Primary outcome is required.")
    return not reasons, reasons
# ============================================================================
# Gate registry
# ============================================================================
STATE_GATES: Dict[
    Tuple[ResearchStateEnum, ResearchStateEnum],
    Callable[[Any], Tuple[bool, List[str]]],
] = {
    (
        ResearchStateEnum.IDEA,
        ResearchStateEnum.QUESTION_DEFINED,
    ): gate_question_defined,
    (
        ResearchStateEnum.QUESTION_DEFINED,
        ResearchStateEnum.DESIGN_SELECTED,
    ): gate_design_selected,
    (
        ResearchStateEnum.DESIGN_SELECTED,
        ResearchStateEnum.PROTOCOL_READY,
    ): gate_protocol_ready,
    (
        ResearchStateEnum.PROTOCOL_READY,
        ResearchStateEnum.LITERATURE_SEARCH,
    ): gate_literature_search,
    (
        ResearchStateEnum.LITERATURE_SEARCH,
        ResearchStateEnum.SCREENING,
    ): gate_screening,
    (
        ResearchStateEnum.SCREENING,
        ResearchStateEnum.DATA_COLLECTION,
    ): gate_data_collection,
    (
        ResearchStateEnum.DATA_COLLECTION,
        ResearchStateEnum.DATA_READY,
    ): gate_data_ready,
    (
        ResearchStateEnum.DATA_READY,
        ResearchStateEnum.ANALYSIS_PLAN_LOCKED,
    ): gate_analysis_plan_locked,
    (
        ResearchStateEnum.ANALYSIS_PLAN_LOCKED,
        ResearchStateEnum.ANALYSIS_COMPLETE,
    ): gate_analysis_complete,
    (
        ResearchStateEnum.ANALYSIS_COMPLETE,
        ResearchStateEnum.MANUSCRIPT_DRAFT,
    ): gate_manuscript_draft,
    (
        ResearchStateEnum.MANUSCRIPT_DRAFT,
        ResearchStateEnum.AUDIT,
    ): gate_audit,
    (
        ResearchStateEnum.AUDIT,
        ResearchStateEnum.JOURNAL_SELECTION,
    ): gate_journal_selection,
    (
        ResearchStateEnum.JOURNAL_SELECTION,
        ResearchStateEnum.READY_FOR_SUBMISSION,
    ): gate_ready_for_submission,
}
def get_gate(
    from_state: Any,
    to_state: Any,
) -> Optional[Callable[[Any], Tuple[bool, List[str]]]]:
    """
    Return the registered gate for a transition, if one exists.
    """
    try:
        source = _coerce_state(from_state)
        target = _coerce_state(to_state)
    except ValueError:
        return None
    return STATE_GATES.get((source, target))
def validate_gate(
    project: Any,
    to_state: Any,
) -> Tuple[bool, List[str]]:
    """
    Validate the gate associated with the project's current state and
    requested target.
    If no gate is registered, the topology is still checked.
    """
    current = _get_project_state(project)
    try:
        target = _coerce_state(to_state)
    except ValueError as exc:
        return False, [str(exc)]
    if not is_valid_transition(current, target):
        return False, [
            (
                f"Transition from '{current.value}' "
                f"to '{target.value}' is not permitted."
            )
        ]
    gate_fn = get_gate(current, target)
    if gate_fn is None:
        return True, []
    return gate_fn(project)
# ============================================================================
# Public API
# ============================================================================
__all__ = [
    # Compatibility
    "ResearchState",
    "ResearchStateEnum",
    # Exceptions
    "StateGateError",
    "InvalidStateTransitionError",
    # Lifecycle
    "all_states_in_order",
    "ALLOWED_TRANSITIONS",
    "STATE_GATES",
    # Helpers
    "state_progress_index",
    "validate_transition",
    "get_valid_next_states",
    "is_valid_transition",
    "get_gate",
    "validate_gate",
    # Audit
    "TransitionRecord",
    # Transition functions
    "transition_state",
    "transition_state_gated",
    # Coordinator
    "StateManager",
    # Gates
    "gate_question_defined",
    "gate_design_selected",
    "gate_protocol_ready",
    "gate_literature_search",
    "gate_screening",
    "gate_data_collection",
    "gate_data_ready",
    "gate_analysis_plan_locked",
    "gate_analysis_complete",
    "gate_manuscript_draft",
    "gate_audit",
    "gate_journal_selection",
    "gate_ready_for_submission",
]
