import structlog
from app.tools.shell_runner import ShellRunner
from app.core.self_debug import SelfDebugRuntime
import asyncio

logger = structlog.get_logger(__name__)

class DevAgent:
    def __init__(self, shell_runner: ShellRunner, self_debug: SelfDebugRuntime):
        self.shell_runner = shell_runner
        self.self_debug = self_debug

    async def build_and_test(self, setup_command: str, test_command: str) -> str:
        """
        Orchestrates an autonomous build-test loop.
        In a full implementation, if test_command fails, it feeds the output back
        to the LLM via self_debug to write a fix and retry.
        """
        logger.info("devagent_starting_build_test")
        
        # 1. Run Setup
        setup_result = await self.self_debug.execute_with_debug(
            "run_shell_command",
            {"command": setup_command},
            lambda: self.shell_runner.run_command(setup_command)
        )
        
        if "COMMAND FAILED" in setup_result or "CRITICAL ERROR" in setup_result:
            return f"Setup phase failed:\n{setup_result}"
            
        # 2. Run Tests
        test_result = await self.self_debug.execute_with_debug(
            "run_shell_command",
            {"command": test_command},
            lambda: self.shell_runner.run_command(test_command)
        )
        
        if "COMMAND FAILED" in test_result:
            return f"Test phase failed. Needs fix:\n{test_result}"
            
        return "Build and Test successful."
