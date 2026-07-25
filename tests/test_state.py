import pytest
from app.core.state_machine import StateMachine, AssistantState

def test_initial_state():
    sm = StateMachine()
    assert sm.current_state == AssistantState.DORMANT

def test_state_transition():
    sm = StateMachine()
    sm.transition_to(AssistantState.AUTHENTICATING)
    assert sm.current_state == AssistantState.AUTHENTICATING

def test_state_listener():
    sm = StateMachine()
    states_recorded = []
    
    def listener(state):
        states_recorded.append(state)
        
    sm.add_listener(listener)
    sm.transition_to(AssistantState.ACTIVE_LISTENING)
    
    assert len(states_recorded) == 1
    assert states_recorded[0] == AssistantState.ACTIVE_LISTENING

def test_no_transition_on_same_state():
    sm = StateMachine()
    states_recorded = []
    
    def listener(state):
        states_recorded.append(state)
        
    sm.add_listener(listener)
    sm.transition_to(AssistantState.DORMANT)
    
    # Should be no new event because it's already in DORMANT
    assert len(states_recorded) == 0
