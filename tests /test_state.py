from __future__ import annotations

import pytest

from core.models import ResearchStateEnum
from core.state import (
    InvalidStateTransitionError,
    all_states_in_order,
    get_valid_next_states,
    state_progress_index,
    transition_state,
    validate_transition,
)


class TestValidTransitions:
    def test_idea_to_question_defined(self):
        result = transition_state(
            ResearchStateEnum.IDEA, ResearchStateEnum.QUESTION_DEFINED
        )
        assert result == ResearchStateEnum.QUESTION_DEFINED

    def test_question_defined_to_design_selected(self):
        result = transition_state(
            ResearchStateEnum.QUESTION_DEFINED, ResearchStateEnum.DESIGN_SELECTED
        )
        assert result == ResearchStateEnum.DESIGN_SELECTED

    def test_design_selected_to_protocol_ready(self):
        result = transition_state(
            ResearchStateEnum.DESIGN_SELECTED, ResearchStateEnum.PROTOCOL_READY
        )
        assert result == ResearchStateEnum.PROTOCOL_READY

    def test_protocol_ready_to_literature_search(self):
        result = transition_state(
            ResearchStateEnum.PROTOCOL_READY, ResearchStateEnum.LITERATURE_SEARCH
        )
        assert result == ResearchStateEnum.LITERATURE_SEARCH

    def test_full_sequential_chain(self):
        ordered = all_states_in_order()
        current = ordered[0]
        for next_state in ordered[1:]:
            current = transition_state(current, next_state)
        assert current == ResearchStateEnum.READY_FOR_SUBMISSION


class TestInvalidTransitions:
    def test_idea_to_analysis_complete_raises(self):
        with pytest.raises(InvalidStateTransitionError):
            transition_state(
                ResearchStateEnum.IDEA, ResearchStateEnum.ANALYSIS_COMPLETE
            )

    def test_idea_to_manuscript_raises(self):
        with pytest.raises(InvalidStateTransitionError):
            transition_state(
                ResearchStateEnum.IDEA, ResearchStateEnum.MANUSCRIPT_DRAFT
            )

    def test_idea_to_ready_for_submission_raises(self):
        with pytest.raises(InvalidStateTransitionError):
            transition_state(
                ResearchStateEnum.IDEA, ResearchStateEnum.READY_FOR_SUBMISSION
            )

    def test_idea_to_idea_raises(self):
        with pytest.raises(InvalidStateTransitionError):
            transition_state(ResearchStateEnum.IDEA, ResearchStateEnum.IDEA)

    def test_question_defined_to_idea_raises(self):
        with pytest.raises(InvalidStateTransitionError):
            transition_state(
                ResearchStateEnum.QUESTION_DEFINED, ResearchStateEnum.IDEA
            )

    def test_terminal_state_raises(self):
        with pytest.raises(InvalidStateTransitionError):
            transition_state(
                ResearchStateEnum.READY_FOR_SUBMISSION, ResearchStateEnum.IDEA
            )

    def test_skip_states_raises(self):
        with pytest.raises(InvalidStateTransitionError):
            transition_state(
                ResearchStateEnum.IDEA, ResearchStateEnum.DESIGN_SELECTED
            )

    def test_validate_transition_raises(self):
        with pytest.raises(InvalidStateTransitionError) as exc_info:
            validate_transition(
                ResearchStateEnum.IDEA, ResearchStateEnum.ANALYSIS_COMPLETE
            )
        assert "IDEA" in str(exc_info.value)
        assert "ANALYSIS_COMPLETE" in str(exc_info.value)


class TestStateHelpers:
    def test_get_valid_next_states_idea(self):
        nexts = get_valid_next_states(ResearchStateEnum.IDEA)
        assert ResearchStateEnum.QUESTION_DEFINED in nexts
        assert len(nexts) == 1

    def test_get_valid_next_states_terminal(self):
        nexts = get_valid_next_states(ResearchStateEnum.READY_FOR_SUBMISSION)
        assert nexts == []

    def test_all_states_in_order_count(self):
        states = all_states_in_order()
        assert len(states) == 14

    def test_all_states_in_order_starts_with_idea(self):
        states = all_states_in_order()
        assert states[0] == ResearchStateEnum.IDEA

    def test_all_states_in_order_ends_with_submission(self):
        states = all_states_in_order()
        assert states[-1] == ResearchStateEnum.READY_FOR_SUBMISSION

    def test_state_progress_index_idea(self):
        idx, total = state_progress_index(ResearchStateEnum.IDEA)
        assert idx == 0
        assert total == 13

    def test_state_progress_index_terminal(self):
        idx, total = state_progress_index(ResearchStateEnum.READY_FOR_SUBMISSION)
        assert idx == 13
        assert total == 13
