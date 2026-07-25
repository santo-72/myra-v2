import pytest
import asyncio
from app.core.dev_agent import DevAgent
from app.core.self_debug import SelfDebugRuntime
from app.tools.shell_runner import ShellRunner

class MockShellRunner:
    def __init__(self):
        self.call_count = 0
        
    async def run_command(self, command: str) -> str:
        self.call_count += 1
        if command == "setup":
            return "Exit Code: 0\nStdout:\nSetup Done"
        elif command == "test":
            if self.call_count == 2:
                # First time test fails
                return "Exit Code: 1\nStderr:\nAssertionError"
            else:
                return "Exit Code: 0\nStdout:\nTests Pass"
        return "Exit Code: 1\nUnknown command"

@pytest.mark.asyncio
async def test_build_and_test():
    shell_runner = MockShellRunner()
    self_debug = SelfDebugRuntime(max_retries=1)
    agent = DevAgent(shell_runner, self_debug)
    
    # In this mock, the first time test fails, it immediately returns failure to the LLM
    result = await agent.build_and_test("setup", "test")
    
    # We expect it to fail and surface the error to the LLM to fix
    assert "Test phase failed" in result
    assert "Exit Code: 1" in result
    assert "AssertionError" in result
