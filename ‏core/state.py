from __future__ import annotations

from typing import Dict, List, Tuple

from core.models import ResearchStateEnum


VALID_TRANSITIONS: Dict[ResearchStateEnum, List[ResearchStateEnum]] = {
    ResearchStateEnum.IDEA: [
        ResearchStateEnum.QUESTION_DEFINED,
    ],
    ResearchStateEnum.QUESTION_DEFINED: [
        ResearchStateEnum.DESIGN_SELECTED,
    ],
    ResearchStateEnum.DESIGN_SELECTED: [
        ResearchStateEnum.PROTOCOL_READY,
    ],
    ResearchStateEnum.PROTOCOL_READY: [
        ResearchStateEnum.LITERATURE_SEARCH,
    ],
    ResearchStateEnum.LITERATURE_SEARCH: [
        ResearchStateEnum.SCREENING,
    ],
    ResearchStateEnum.SCREENING: [
        ResearchStateEnum.DATA_COLLECTION,
    ],
    ResearchStateEnum.DATA_COLLECTION: [
        ResearchStateEnum.DATA_READY,
    ],
    ResearchStateEnum.DATA_READY: [
        ResearchStateEnum.ANALYSIS_PLAN_LOCKED,
    ],
    ResearchStateEnum.ANALYSIS_PLAN_LOCKED: [
        ResearchStateEnum.ANALYSIS_COMPLETE,
    ],
    ResearchStateEnum.ANALYSIS_COMPLETE: [
        ResearchStateEnum.MANUSCRIPT_DRAFT,
    ],
    ResearchStateEnum.MANUSCRIPT_DRAFT: [
        ResearchStateEnum.AUDIT,
    ],
    ResearchStateEnum.AUDIT: [
        ResearchStateEnum.JOURNAL_SELECTION,
    ],
    ResearchStateEnum.JOURNAL_SELECTION: [
        ResearchStateEnum.READY_FOR_SUBMISSION,
    ],
    ResearchStateEnum.READY_FOR_SUBMISSION: [],
}


class InvalidStateTransitionError(Exception):
    pass


def get_valid_next_states(current: ResearchStateEnum) -> List[ResearchStateEnum]:
    return VALID_TRANSITIONS.get(current, [])


def validate_transition(
    current: ResearchStateEnum, target: ResearchStateEnum
) -> None:
    allowed = VALID_TRANSITIONS.get(current, [])
    if target not in allowed:
        raise InvalidStateTransitionError(
            f"Cannot transition from '{current.value}' to '{target.value}'. "
            f"Valid transitions from '{current.value}': "
            f"{[s.value for s in allowed] if allowed else 'none (terminal state)'}."
        )


def transition_state(
    current: ResearchStateEnum, target: ResearchStateEnum
) -> ResearchStateEnum:
    validate_transition(current, target)
    return target


def all_states_in_order() -> List[ResearchStateEnum]:
    return [
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


def state_progress_index(state: ResearchStateEnum) -> Tuple[int, int]:
    ordered = all_states_in_order()
    idx = ordered.index(state)
    return idx, len(ordered) - 1
