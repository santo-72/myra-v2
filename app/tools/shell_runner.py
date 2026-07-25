import asyncio
import structlog
from pathlib import Path
from app.config import settings

logger = structlog.get_logger(__name__)

class ShellRunner:
    def __init__(self):
        self.workspace_root = Path(settings.workspace_dir).resolve()

    async def run_command(self, command: str) -> str:
        """Executes a shell command asynchronously within the sandboxed workspace."""
        logger.info("executing_shell_command", command=command)
        
        try:
            # We use asyncio.create_subprocess_shell to run non-blocking shell commands
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self.workspace_root)
            )
            
            stdout, stderr = await process.communicate()
            
            out_str = stdout.decode('utf-8').strip() if stdout else ""
            err_str = stderr.decode('utf-8').strip() if stderr else ""
            
            exit_code = process.returncode
            
            logger.info("shell_command_result", exit_code=exit_code)
            
            # Combine output for LLM consumption
            result = f"Exit Code: {exit_code}\n"
            if out_str:
                result += f"Stdout:\n{out_str}\n"
            if err_str:
                result += f"Stderr:\n{err_str}\n"
                
            return result
        except Exception as e:
            logger.error("shell_command_failed", error=str(e))
            return f"Error executing command: {str(e)}"
