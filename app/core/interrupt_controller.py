import asyncio
import structlog
from datetime import datetime
from typing import Optional, Dict, Any

logger = structlog.get_logger(__name__)

class InterruptController:
    """
    Centralized controller responsible for managing cooperative task cancellation and
    universal barge-in interdiction across all async tool operations in Myra AI v2.
    """
    def __init__(self):
        self._active_task: Optional[asyncio.Task] = None
        self._task_name: str = ""
        self._task_description: str = ""
        self._partial_effect_msg: str = ""
        self._interrupt_requested: bool = False

    @property
    def has_active_task(self) -> bool:
        return self._active_task is not None and not self._active_task.done()

    def register_active_task(self, task: asyncio.Task, name: str, description: str, partial_effect_msg: str = ""):
        """
        Registers an executing async tool task for barge-in monitoring.
        """
        self._active_task = task
        self._task_name = name
        self._task_description = description
        self._partial_effect_msg = partial_effect_msg
        self._interrupt_requested = False
        
        logger.info("task_registered_for_interruption_monitoring", name=name, description=description)
        
        def _cleanup(t):
            if self._active_task == t:
                self._active_task = None
                self._interrupt_requested = False
                
        task.add_done_callback(_cleanup)

    def mark_partial_effect(self, effect_description: str):
        """
        Records that an observable partial action was taken (e.g. file modification started),
        warranting a vocal acknowledgment if interrupted afterwards.
        """
        self._partial_effect_msg = effect_description
        logger.debug("task_partial_effect_recorded", effect=effect_description)

    def is_interrupt_requested(self) -> bool:
        """
        Checkpoint check method for cooperative loops to poll during lengthy steps.
        """
        if self._active_task and self._active_task.cancelled():
            return True
        return self._interrupt_requested

    async def request_interrupt(self, reason: str = "User vocal barge-in") -> Dict[str, Any]:
        """
        Cancels the currently active tool task cleanly, awaiting termination and capturing CancelledError
        to leave system states safe and consistent.
        """
        if not self.has_active_task:
            logger.debug("interrupt_requested_no_active_task", reason=reason)
            return {"interrupted": False, "reason": "No active task running"}
            
        task = self._active_task
        name = self._task_name
        desc = self._task_description
        effect = self._partial_effect_msg
        timestamp = datetime.now().isoformat()
        
        self._interrupt_requested = True
        logger.warning("task_interruption_requested", task=name, step=desc, reason=reason)
        
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            logger.info("task_cancelled_cleanly", task=name, step=desc)
        except Exception as e:
            logger.error("task_interruption_exception", task=name, error=str(e))
            
        self._active_task = None
        self._interrupt_requested = False
        
        return {
            "interrupted": True,
            "task_name": name,
            "step_description": desc,
            "partial_effect_msg": effect,
            "timestamp": timestamp,
            "reason": reason
        }

# Global singleton instance for system-wide interruption coordination
interrupt_controller = InterruptController()
