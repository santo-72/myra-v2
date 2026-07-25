import re
import structlog
from typing import Callable, Awaitable
from app.core.state_machine import StateMachine, AssistantState
import asyncio

logger = structlog.get_logger(__name__)

class DestructiveActionGate:
    def __init__(self, state_machine: StateMachine):
        self.state_machine = state_machine
        
        # Regex for destructive or highly impactful commands
        # Covers rm, del, format, sudo, git push --force, etc.
        self.dangerous_patterns = [
            r'^\s*rm\s+.*',
            r'^\s*del\s+.*',
            r'^\s*rd\s+.*',
            r'^\s*format\s+.*',
            r'^\s*sudo\s+.*',
            r'.*git\s+push.*--force.*',
            r'^\s*mkfs\s+.*'
        ]
        self.compiled_patterns = [re.compile(p, re.IGNORECASE) for p in self.dangerous_patterns]

    def is_dangerous(self, command: str) -> bool:
        for pattern in self.compiled_patterns:
            if pattern.search(command):
                return True
        return False

    async def intercept_and_confirm(self, command: str, execute_callback: Callable[[], Awaitable[str]]) -> str:
        """
        Intercepts the command if dangerous. In a full implementation, this pauses 
        execution, transitions to ACTIVE_SPEAKING to request confirmation, and 
        awaits a WS event or STT response.
        For now, we simulate the block.
        """
        if self.is_dangerous(command):
            logger.warning("destructive_action_intercepted", command=command)
            # 1. Ask for confirmation
            self.state_machine.transition_to(AssistantState.ACTIVE_SPEAKING)
            
            # TODO: Integrate with audio/STT pipeline to actually wait for "yes"
            # For this phase's mock, we will automatically reject dangerous commands
            # until full STT verbal confirmation looping is integrated.
            return "Execution Blocked: Destructive action requires explicit verbal confirmation."
            
        # Proceed safely
        return await execute_callback()
