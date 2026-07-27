from enum import Enum, auto
import structlog
from typing import Callable, List

logger = structlog.get_logger(__name__)

class AssistantState(Enum):
    DORMANT = auto()
    AUTHENTICATING = auto()
    ACTIVE_LISTENING = auto()
    ACTIVE_THINKING = auto()
    ACTIVE_SPEAKING = auto()
    TOOL_EXECUTING = auto()
    ALERT = auto()
    ERROR = auto()

class StateMachine:
    def __init__(self):
        self._state = AssistantState.DORMANT
        self._listeners: List[Callable[[AssistantState], None]] = []

    @property
    def current_state(self) -> AssistantState:
        return self._state

    def add_listener(self, callback: Callable[[AssistantState], None]):
        self._listeners.append(callback)

    def transition_to(self, new_state: AssistantState):
        if self._state == new_state:
            return
        
        logger.info("state_transition", old_state=self._state.name, new_state=new_state.name)
        self._state = new_state
        for listener in self._listeners:
            try:
                listener(new_state)
            except Exception as e:
                logger.error("state_listener_error", error=str(e))
