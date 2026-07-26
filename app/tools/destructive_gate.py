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

    async def request_confirmation(self, action_description: str, stt_source_callback: Callable[[], Awaitable[str]] = None) -> bool:
        """
        Requests explicit spoken/verbal confirmation for external or destructive actions.
        """
        logger.warning("destructive_confirmation_requested", action=action_description)
        self.state_machine.transition_to(AssistantState.ACTIVE_SPEAKING)
        
        if stt_source_callback:
            try:
                response_text = await stt_source_callback()
                response_clean = response_text.strip().lower()
                affirmative_keywords = [
                    "yes", "হ্যাঁ", "হাঁ", "পাঠাও", "yes send", "ok", 
                    "send", "ঠিক আছে", "করো", "sure", "proceed", "approve"
                ]
                for kw in affirmative_keywords:
                    if kw in response_clean:
                        logger.info("destructive_action_confirmed", action=action_description, response=response_clean)
                        return True
                logger.warning("destructive_action_rejected_by_voice", action=action_description, response=response_clean)
                return False
            except Exception as e:
                logger.error("confirmation_stt_error", error=str(e))
                return False
        
        # When no real-time voice verification loop is attached, block by default for safety
        logger.warning(" destructive_action_blocked_no_stt_source", action=action_description)
        return False

    async def intercept_and_confirm(self, command: str, execute_callback: Callable[[], Awaitable[str]], stt_source_callback: Callable[[], Awaitable[str]] = None) -> str:
        """
        Intercepts the command if dangerous. Requires explicit verbal confirmation before execution.
        """
        if self.is_dangerous(command):
            logger.warning("destructive_action_intercepted", command=command)
            confirmed = await self.request_confirmation(f"Execute dangerous command: {command}", stt_source_callback=stt_source_callback)
            if not confirmed:
                return "Execution Blocked: Destructive action requires explicit verbal confirmation."
            
        # Proceed safely
        return await execute_callback()

