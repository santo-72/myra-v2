import structlog
from app.tools.shell_runner import ShellRunner
from app.core.self_debug import SelfDebugRuntime
from app.core.interrupt_controller import interrupt_controller
import asyncio

logger = structlog.get_logger(__name__)

class DevAgent:
    def __init__(self, shell_runner: ShellRunner, self_debug: SelfDebugRuntime):
        self.shell_runner = shell_runner
        self.self_debug = self_debug

    async def build_and_test(self, setup_command: str, test_command: str) -> str:
        """
        Orchestrates an autonomous build-test loop with cooperative interruption checkpoints.
        """
        logger.info("devagent_starting_build_test")
        
        try:
            if interrupt_controller.is_interrupt_requested():
                raise asyncio.CancelledError("Task cancelled before setup phase.")
                
            # 1. Run Setup
            interrupt_controller.mark_partial_effect(f"Running setup: {setup_command}")
            setup_result = await self.self_debug.execute_with_debug(
                "run_shell_command",
                {"command": setup_command},
                lambda: self.shell_runner.run_command(setup_command)
            )
            
            if "COMMAND FAILED" in setup_result or "CRITICAL ERROR" in setup_result:
                return f"Setup phase failed:\n{setup_result}"
                
            if interrupt_controller.is_interrupt_requested():
                logger.warning("devagent_interrupted_between_setup_and_test")
                raise asyncio.CancelledError("Task cancelled between setup and test phases.")
                
            # 2. Run Tests
            interrupt_controller.mark_partial_effect(f"Running tests: {test_command}")
            test_result = await self.self_debug.execute_with_debug(
                "run_shell_command",
                {"command": test_command},
                lambda: self.shell_runner.run_command(test_command)
            )
            
            if "COMMAND FAILED" in test_result:
                return f"Test phase failed. Needs fix:\n{test_result}"
                
            return "Build and Test successful."
        except asyncio.CancelledError as ce:
            logger.warning("devagent_build_and_test_cancelled", reason=str(ce))
            raise
