"""
core/state.py
=============
Sprint 2 — State Machine & Gate Validation Engine

Provides:
- ResearchState enumeration (all project lifecycle states)
- StateGateError (raised when a gate check blocks a transition)
- InvalidStateTransitionError (raised for illegal state transitions)
- transition_state() (unconditional state transition with audit)
- transition_state_gated() (gate-checked state transition)
- StateManager (project-level state coordinator)

No-Invention Rule: All state transitions and gate evaluations are
determined solely from the data present in the supplied project /
framework objects. Nothing is assumed or fabricated.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Internal imports — tolerant of partial model availability
# ---------------------------------------------------------------------------
try:
    from core.models import ResearchProject, ProjectStatus
except ImportError:  # pragma: no cover
    ResearchProject = None   # type: ignore[assignment,misc]
    ProjectStatus = None     # type: ignore[assignment,misc]


# ===========================================================================
# Custom Exceptions
# ===========================================================================

class StateGateError(Exception):
    """
    Raised when a state gate check prevents a project from advancing to
    the next lifecycle phase.

    Attributes
    ----------
    message   : Human-readable explanation of why the gate failed.
    reasons   : List of individual failure reasons (may be empty).
    from_state: The state the project was in when the gate was evaluated.
    to_state  : The target state that was blocked.
    """

    def __init__(
        self,
        message: str,
        reasons: Optional[List[str]] = None,
        from_state: Optional[str] = None,
        to_state: Optional[str] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.reasons: List[str] = reasons or []
        self.from_state = from_state
        self.to_state = to_state

    def __str__(self) -> str:
        base = self.message
        if self.reasons:
            base += " | Reasons: " + "; ".join(self.reasons)
        return base

    def to_dict(self) -> Dict[str, Any]:
        return {
            "error": "StateGateError",
            "message": self.message,
            "reasons": self.reasons,
            "from_state": self.from_state,
            "to_state": self.to_state,
        }


class InvalidStateTransitionError(Exception):
    """
    Raised when a requested state transition is not permitted by the
    defined state machine topology.

    Attributes
    ----------
    message   : Human-readable explanation.
    from_state: The current (source) state.
    to_state  : The requested (target) state.
    """

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
            f"(from={self.from_state!r} → to={self.to_state!r})"
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "error": "InvalidStateTransitionError",
            "message": self.message,
            "from_state": self.from_state,
            "to_state": self.to_state,
        }


# ===========================================================================
# ResearchState Enumeration
# ===========================================================================

class ResearchState(str, Enum):
    """
    Ordered lifecycle states for a research project.

    The canonical forward progression is:

        DRAFT
          → QUESTION_DEFINED
          → FRAMEWORK_BUILT
          → DESIGN_SELECTED
          → LITERATURE_SEARCH
          → LITERATURE_SCREENED
          → DATA_EXTRACTION
          → ANALYSIS
          → REPORTING
          → COMPLETE

    Backward transitions and lateral moves are explicitly prohibited
    except where noted in ALLOWED_TRANSITIONS.
    """

    DRAFT = "draft"
    QUESTION_DEFINED = "question_defined"
    FRAMEWORK_BUILT = "framework_built"
    DESIGN_SELECTED = "design_selected"
    LITERATURE_SEARCH = "literature_search"
    LITERATURE_SCREENED = "literature_screened"
    DATA_EXTRACTION = "data_extraction"
    ANALYSIS = "analysis"
    REPORTING = "reporting"
    COMPLETE = "complete"
    ARCHIVED = "archived"
    ERROR = "error"


# ===========================================================================
# State Machine Topology
# ===========================================================================

# Maps each state to the set of states it is permitted to transition into.
# The ERROR state is reachable from any state (handled programmatically).
# ARCHIVED is reachable from COMPLETE only.
ALLOWED_TRANSITIONS: Dict[ResearchState, List[ResearchState]] = {
    ResearchState.DRAFT: [
        ResearchState.QUESTION_DEFINED,
        ResearchState.ERROR,
    ],
    ResearchState.QUESTION_DEFINED: [
        ResearchState.FRAMEWORK_BUILT,
        ResearchState.DRAFT,          # allow revision
        ResearchState.ERROR,
    ],
    ResearchState.FRAMEWORK_BUILT: [
        ResearchState.DESIGN_SELECTED,
        ResearchState.QUESTION_DEFINED,  # allow revision
        ResearchState.ERROR,
    ],
    ResearchState.DESIGN_SELECTED: [
        ResearchState.LITERATURE_SEARCH,
        ResearchState.FRAMEWORK_BUILT,   # allow revision
        ResearchState.ERROR,
    ],
    ResearchState.LITERATURE_SEARCH: [
        ResearchState.LITERATURE_SCREENED,
        ResearchState.DESIGN_SELECTED,   # allow revision
        ResearchState.ERROR,
    ],
    ResearchState.LITERATURE_SCREENED: [
        ResearchState.DATA_EXTRACTION,
        ResearchState.LITERATURE_SEARCH,  # allow re-search
        ResearchState.ERROR,
    ],
    ResearchState.DATA_EXTRACTION: [
        ResearchState.ANALYSIS,
        ResearchState.LITERATURE_SCREENED,  # allow re-screening
        ResearchState.ERROR,
    ],
    ResearchState.ANALYSIS: [
        ResearchState.REPORTING,
        ResearchState.DATA_EXTRACTION,  # allow re-extraction
        ResearchState.ERROR,
    ],
    ResearchState.REPORTING: [
        ResearchState.COMPLETE,
        ResearchState.ANALYSIS,   # allow revision
        ResearchState.ERROR,
    ],
    ResearchState.COMPLETE: [
        ResearchState.ARCHIVED,
        ResearchState.REPORTING,  # allow late revision
        ResearchState.ERROR,
    ],
    ResearchState.ARCHIVED: [
        # Terminal — no further transitions permitted
    ],
    ResearchState.ERROR: [
        ResearchState.DRAFT,    # allow reset to draft for recovery
        ResearchState.ERROR,
    ],
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _coerce_state(value: Any) -> ResearchState:
    """
    Coerce a string, ProjectStatus, or ResearchState value into a
    ResearchState.  Raises ValueError if not recognisable.
    """
    if isinstance(value, ResearchState):
        return value

    # Accept ProjectStatus if available and it has a .value attribute
    if value is not None and hasattr(value, "value"):
        value = value.value

    if isinstance(value, str):
        try:
            return ResearchState(value.lower())
        except ValueError:
            pass
        # Try matching by name (e.g. "DRAFT" → ResearchState.DRAFT)
        try:
            return ResearchState[value.upper()]
        except KeyError:
            pass

    raise ValueError(
        f"Cannot coerce {value!r} to ResearchState. "
        f"Valid values: {[s.value for s in ResearchState]}"
    )


# ===========================================================================
# Transition Audit Record
# ===========================================================================

class TransitionRecord:
    """
    Immutable record of a state transition event, written to the project
    audit trail.
    """

    def __init__(
        self,
        from_state: ResearchState,
        to_state: ResearchState,
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
        self.gate_reasons: List[str] = gate_reasons or []
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
            "gate_reasons": self.gate_reasons,
            "timestamp": self.timestamp,
        }


# ===========================================================================
# Core Transition Functions
# ===========================================================================

def transition_state(
    project: Any,
    to_state: Any,
    *,
    triggered_by: str = "system",
    note: str = "",
    _audit_log: Optional[List[Dict[str, Any]]] = None,
) -> Any:
    """
    Unconditionally transition a project to *to_state* if the move is
    permitted by the state machine topology.

    Parameters
    ----------
    project      : Object with a `status` attribute representing the current
                   state.  The attribute is updated in-place.
    to_state     : Target ResearchState (or coercible value).
    triggered_by : Identifier of the actor requesting the transition.
    note         : Optional human-readable annotation for the audit trail.
    _audit_log   : Optional list to append the TransitionRecord dict to
                   (used when project has no built-in audit trail).

    Returns
    -------
    The mutated project object.

    Raises
    ------
    InvalidStateTransitionError
        If the transition from the current state to *to_state* is not
        listed in ALLOWED_TRANSITIONS.

    No-Invention Rule: transition validity is determined solely from the
    ALLOWED_TRANSITIONS map; no external assumptions are made.
    """
    current_raw = getattr(project, "status", None)
    try:
        current = _coerce_state(current_raw)
    except ValueError as exc:
        raise InvalidStateTransitionError(
            f"Project has unrecognisable current state: {current_raw!r}",
            from_state=str(current_raw),
            to_state=str(to_state),
        ) from exc

    try:
        target = _coerce_state(to_state)
    except ValueError as exc:
        raise InvalidStateTransitionError(
            f"Target state is not a valid ResearchState: {to_state!r}",
            from_state=current.value,
            to_state=str(to_state),
        ) from exc

    allowed = ALLOWED_TRANSITIONS.get(current, [])
    if target not in allowed:
        raise InvalidStateTransitionError(
            f"Transition from '{current.value}' to '{target.value}' is not permitted.",
            from_state=current.value,
            to_state=target.value,
        )

    record = TransitionRecord(
        from_state=current,
        to_state=target,
        triggered_by=triggered_by,
        note=note,
        gated=False,
        gate_passed=True,
    )

    # Apply the new state — support both string-valued and enum-valued status
    if hasattr(project, "status"):
        # Prefer to keep the same type as the original value
        if isinstance(current_raw, ResearchState):
            project.status = target
        elif hasattr(current_raw, "__class__") and current_raw.__class__.__name__ == "ProjectStatus":
            # ProjectStatus from core.models — set by string value
            try:
                project.status = current_raw.__class__(target.value)
            except (ValueError, TypeError):
                project.status = target.value
        else:
            project.status = target.value

    # Write to audit trail if the project supports it
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
    Validate a state gate before transitioning a project to *to_state*.

    Parameters
    ----------
    project      : Object with a `status` attribute.
    to_state     : Target ResearchState (or coercible value).
    gate_fn      : Callable that accepts *project* and returns
                   ``(passed: bool, reasons: List[str])``.
    triggered_by : Identifier of the actor requesting the transition.
    note         : Optional annotation for the audit trail.
    raise_on_fail: If True (default), raises StateGateError when the gate
                   check fails.  If False, returns without transitioning.
    _audit_log   : Optional external audit list.

    Returns
    -------
    (project, passed, reasons)
        project  — mutated if the gate passed, unchanged otherwise.
        passed   — True if the gate passed and the transition occurred.
        reasons  — List of failure reasons (empty on success).

    Raises
    ------
    StateGateError
        If raise_on_fail is True and the gate check fails.
    InvalidStateTransitionError
        If the topology does not permit the transition (checked after gate).

    No-Invention Rule: gate evaluation is delegated entirely to *gate_fn*;
    this function introduces no additional criteria.
    """
    current_raw = getattr(project, "status", None)
    try:
        current = _coerce_state(current_raw)
    except ValueError as exc:
        raise InvalidStateTransitionError(
            f"Project has unrecognisable current state: {current_raw!r}",
            from_state=str(current_raw),
            to_state=str(to_state),
        ) from exc

    try:
        target = _coerce_state(to_state)
    except ValueError as exc:
        raise InvalidStateTransitionError(
            f"Target state is not a valid ResearchState: {to_state!r}",
            from_state=current.value,
            to_state=str(to_state),
        ) from exc

    # --- Run the gate function ---
    passed, reasons = gate_fn(project)

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
                f"Gate check failed: transition from '{current.value}' "
                f"to '{target.value}' is blocked.",
                reasons=reasons,
                from_state=current.value,
                to_state=target.value,
            )
        return project, False, reasons

    # --- Gate passed: check topology ---
    allowed = ALLOWED_TRANSITIONS.get(current, [])
    if target not in allowed:
        _write_audit(project, record, _audit_log)
        raise InvalidStateTransitionError(
            f"Transition from '{current.value}' to '{target.value}' "
            f"is not permitted by the state machine.",
            from_state=current.value,
            to_state=target.value,
        )

    # --- Apply transition ---
    if hasattr(project, "status"):
        if isinstance(current_raw, ResearchState):
            project.status = target
        elif hasattr(current_raw, "__class__") and current_raw.__class__.__name__ == "ProjectStatus":
            try:
                project.status = current_raw.__class__(target.value)
            except (ValueError, TypeError):
                project.status = target.value
        else:
            project.status = target.value

    _write_audit(project, record, _audit_log)

    return project, True, []


# ===========================================================================
# Audit Trail Helper
# ===========================================================================

def _write_audit(
    project: Any,
    record: TransitionRecord,
    external_log: Optional[List[Dict[str, Any]]],
) -> None:
    """
    Write a TransitionRecord to the project's audit trail and / or an
    external log list.

    Supports projects that expose:
    - audit_log   : List[Dict]
    - audit_trail : List[Dict]
    - history     : List[Dict]

    If none of these attributes exist the record is silently discarded
    (the caller may pass _audit_log to capture it externally).
    """
    entry = record.to_dict()

    for attr in ("audit_log", "audit_trail", "history"):
        trail = getattr(project, attr, None)
        if isinstance(trail, list):
            trail.append(entry)
            break

    if external_log is not None:
        external_log.append(entry)


# ===========================================================================
# StateManager
# ===========================================================================

class StateManager:
    """
    Project-level coordinator for state transitions.

    Wraps transition_state() and transition_state_gated() with a
    consistent interface and maintains an internal audit trail for
    projects that do not expose their own.

    Usage
    -----
    >>> sm = StateManager(project)
    >>> sm.transition(ResearchState.QUESTION_DEFINED)
    >>> sm.transition_gated(ResearchState.FRAMEWORK_BUILT, gate_fn)
    """

    def __init__(self, project: Any) -> None:
        self._project = project
        self._audit: List[Dict[str, Any]] = []

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def project(self) -> Any:
        return self._project

    @property
    def current_state(self) -> ResearchState:
        return _coerce_state(getattr(self._project, "status", ResearchState.DRAFT))

    @property
    def audit_trail(self) -> List[Dict[str, Any]]:
        """Combined audit trail (project-level + internal)."""
        project_trail: List[Dict[str, Any]] = []
        for attr in ("audit_log", "audit_trail", "history"):
            trail = getattr(self._project, attr, None)
            if isinstance(trail, list):
                project_trail = trail
                break
        # Merge without duplication (internal _audit is only used as fallback)
        if project_trail:
            return project_trail
        return list(self._audit)

    # ------------------------------------------------------------------
    # Transition helpers
    # ------------------------------------------------------------------

    def transition(
        self,
        to_state: Any,
        *,
        triggered_by: str = "system",
        note: str = "",
    ) -> "StateManager":
        """
        Unconditional transition.  Returns self for fluent chaining.

        Raises InvalidStateTransitionError if the move is illegal.
        """
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
        """
        Gate-checked transition.

        Returns (passed, reasons).  If raise_on_fail is True (default),
        StateGateError is raised on gate failure.
        """
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

    # ------------------------------------------------------------------
    # Introspection helpers
    # ------------------------------------------------------------------

    def allowed_next_states(self) -> List[ResearchState]:
        """Return the list of states reachable from the current state."""
        return list(ALLOWED_TRANSITIONS.get(self.current_state, []))

    def can_transition_to(self, to_state: Any) -> bool:
        """Return True if a direct transition to *to_state* is topologically valid."""
        try:
            target = _coerce_state(to_state)
        except ValueError:
            return False
        return target in ALLOWED_TRANSITIONS.get(self.current_state, [])

    def is_terminal(self) -> bool:
        """Return True if the project is in a terminal state (ARCHIVED)."""
        return self.current_state == ResearchState.ARCHIVED

    def is_error(self) -> bool:
        """Return True if the project is in the ERROR state."""
        return self.current_state == ResearchState.ERROR

    def reset_to_draft(
        self,
        *,
        triggered_by: str = "system",
        note: str = "Manual reset to draft.",
    ) -> "StateManager":
        """
        Forcibly move an ERROR-state project back to DRAFT.

        Only permitted from the ERROR state.  Raises
        InvalidStateTransitionError otherwise.
        """
        if self.current_state != ResearchState.ERROR:
            raise InvalidStateTransitionError(
                "reset_to_draft() is only permitted from the ERROR state.",
                from_state=self.current_state.value,
                to_state=ResearchState.DRAFT.value,
            )
        return self.transition(
            ResearchState.DRAFT,
            triggered_by=triggered_by,
            note=note,
        )

    def __repr__(self) -> str:
        return (
            f"StateManager("
            f"project_id={getattr(self._project, 'id', 'unknown')!r}, "
            f"state={self.current_state.value!r})"
        )


# ===========================================================================
# Standalone gate helpers (used by research_engine and task_engine)
# ===========================================================================

def gate_question_defined(project: Any) -> Tuple[bool, List[str]]:
    """
    Minimal gate: verify that the project carries a non-empty research
    question before advancing from DRAFT to QUESTION_DEFINED.

    No-Invention Rule: only inspects attributes present on *project*.
    """
    reasons: List[str] = []

    question = (
        getattr(project, "research_question", None)
        or getattr(project, "question", None)
        or ""
    )
    if not str(question).strip():
        reasons.append(
            "A research question must be defined before leaving the DRAFT state."
        )

    return len(reasons) == 0, reasons


def gate_framework_built(project: Any) -> Tuple[bool, List[str]]:
    """
    Gate: verify that the project has a populated research framework
    before advancing from QUESTION_DEFINED to FRAMEWORK_BUILT.
    """
    reasons: List[str] = []

    framework = getattr(project, "framework", None)
    if framework is None:
        reasons.append(
            "A research framework (PICO/PECO) must be built before advancing."
        )
        return False, reasons

    # Check mandatory framework fields
    fw_type = getattr(framework, "framework_type", "")
    population = str(getattr(framework, "population", "")).strip()
    outcome = str(getattr(framework, "outcome", "")).strip()

    if not population:
        reasons.append("Framework: Population (P) is required.")
    if not outcome:
        reasons.append("Framework: Outcome (O) is required.")

    # For PICO: intervention required; for PECO: exposure required
    if str(fw_type).upper() == "PECO":
        exposure = str(getattr(framework, "exposure", "")).strip()
        if not exposure:
            reasons.append("Framework: Exposure (E) is required for PECO.")
    else:
        intervention = str(getattr(framework, "intervention", "")).strip()
        if not intervention:
            reasons.append("Framework: Intervention (I) is required for PICO.")

    return len(reasons) == 0, reasons


def gate_design_selected(project: Any) -> Tuple[bool, List[str]]:
    """
    Gate: verify that a study design has been selected before advancing
    from FRAMEWORK_BUILT to DESIGN_SELECTED.
    """
    reasons: List[str] = []

    design = (
        getattr(project, "study_design", None)
        or getattr(project, "design", None)
    )
    if design is None:
        reasons.append(
            "A study design must be selected before advancing to DESIGN_SELECTED."
        )
        return False, reasons

    design_value = str(
        getattr(design, "recommended_design", None)
        or getattr(design, "value", None)
        or design
    ).strip()

    if not design_value or design_value.lower() in ("unknown", "unknown / insufficient information"):
        reasons.append(
            "Study design is UNKNOWN; a specific design must be confirmed."
        )

    return len(reasons) == 0, reasons


def gate_literature_searched(project: Any) -> Tuple[bool, List[str]]:
    """
    Gate: verify that a literature search has been initiated / completed
    before advancing from DESIGN_SELECTED to LITERATURE_SEARCH.
    """
    reasons: List[str] = []

    lit = (
        getattr(project, "literature_strategy", None)
        or getattr(project, "search_strategy", None)
        or getattr(project, "literature_results", None)
    )
    if lit is None:
        reasons.append(
            "A literature search strategy must be defined before advancing."
        )

    return len(reasons) == 0, reasons


# ===========================================================================
# Public re-exports
# ===========================================================================

__all__ = [
    # Exceptions
    "StateGateError",
    "InvalidStateTransitionError",
    # Enumeration
    "ResearchState",
    # Topology
    "ALLOWED_TRANSITIONS",
    # Core transition functions
    "transition_state",
    "transition_state_gated",
    # State manager class
    "StateManager",
    # Audit record
    "TransitionRecord",
    # Standalone gate helpers
    "gate_question_defined",
    "gate_framework_built",
    "gate_design_selected",
    "gate_literature_searched",
]
