import structlog
from typing import Callable, Awaitable

logger = structlog.get_logger(__name__)

class SelfDebugRuntime:
    def __init__(self, max_retries: int = 2):
        self.max_retries = max_retries

    async def execute_with_debug(self, tool_name: str, args: dict, execute_callback: Callable[[], Awaitable[str]]) -> str:
        """
        Wraps a tool execution. If it fails (e.g., non-zero exit code or Exception),
        we can feed it back or format it cleanly for the LLM to auto-correct.
        """
        attempt = 0
        last_error = ""
        
        while attempt <= self.max_retries:
            try:
                result = await execute_callback()
                
                # Check for standard shell error markers if this was a shell command
                if "Exit Code:" in result and "Exit Code: 0" not in result:
                    logger.warning("tool_execution_failed", tool=tool_name, attempt=attempt)
                    last_error = result
                    # Instead of actually looping here (which blocks the LLM),
                    # we return the error back to the LLM immediately so IT can 
                    # do the reasoning and retrying. We just format it explicitly.
                    return f"COMMAND FAILED. Please review the error and retry or fix the code.\n{result}"
                    
                return result
                
            except Exception as e:
                logger.error("tool_exception", tool=tool_name, error=str(e))
                return f"CRITICAL ERROR EXECUTING TOOL:\n{str(e)}"
                
        return f"Failed after {self.max_retries} attempts. Last Error:\n{last_error}"
