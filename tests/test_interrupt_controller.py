import pytest
import asyncio
import os
from pathlib import Path
from app.core.interrupt_controller import InterruptController
from app.core.state_machine import StateMachine, AssistantState
from app.tools.file_system import FileSystemTools
from app.tools.destructive_gate import DestructiveActionGate

@pytest.mark.asyncio
async def test_interrupt_controller_cancellation():
    controller = InterruptController()
    checkpoint_reached = [False]
    cancelled_handled = [False]

    async def mock_long_running_tool():
        try:
            await asyncio.sleep(0.05)
            checkpoint_reached[0] = True
            if controller.is_interrupt_requested():
                raise asyncio.CancelledError("Cooperative checkpoint cancel")
            await asyncio.sleep(1.0)
            return "Success"
        except asyncio.CancelledError:
            cancelled_handled[0] = True
            raise

    task = asyncio.create_task(mock_long_running_tool())
    controller.register_active_task(task, name="mock_tool", description="Testing mid-execution cancellation")
    controller.mark_partial_effect("Modified 5 records")

    # Give task enough time to start
    await asyncio.sleep(0.02)
    assert controller.has_active_task is True

    # Trigger interruption
    audit_res = await controller.request_interrupt(reason="User barge-in test")
    assert audit_res["interrupted"] is True
    assert audit_res["task_name"] == "mock_tool"
    assert audit_res["partial_effect_msg"] == "Modified 5 records"
    assert cancelled_handled[0] is True
    assert controller.has_active_task is False

def test_state_transitions_on_interrupt():
    sm = StateMachine()
    
    # Verify transition from TOOL_EXECUTING -> ACTIVE_LISTENING
    sm.transition_to(AssistantState.TOOL_EXECUTING)
    assert sm.current_state == AssistantState.TOOL_EXECUTING
    sm.transition_to(AssistantState.ACTIVE_LISTENING)
    assert sm.current_state == AssistantState.ACTIVE_LISTENING
    
    # Verify transition from ACTIVE_THINKING -> ACTIVE_LISTENING
    sm.transition_to(AssistantState.ACTIVE_THINKING)
    assert sm.current_state == AssistantState.ACTIVE_THINKING
    sm.transition_to(AssistantState.ACTIVE_LISTENING)
    assert sm.current_state == AssistantState.ACTIVE_LISTENING

def test_safe_state_atomic_file_write(tmp_path, monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "workspace_dir", str(tmp_path))
    fs = FileSystemTools()
    
    target_file = "test_atomic.txt"
    content = "Atomic write demonstration"
    
    # Verify atomic write success
    res = fs.write_file(target_file, content)
    assert "Successfully wrote to" in res
    
    file_path = tmp_path / target_file
    assert file_path.exists()
    assert file_path.read_text(encoding="utf-8") == content
    
    # No lingering temporary files should remain
    tmp_files = list(tmp_path.glob("test_atomic.txt.tmp_*"))
    assert len(tmp_files) == 0

@pytest.mark.asyncio
async def test_destructive_gate_interruption_abort():
    sm = StateMachine()
    gate = DestructiveActionGate(sm)
    execute_called = [False]

    async def dangerous_action():
        execute_called[0] = True
        return "Formatted disk"

    async def stt_source_interrupt():
        # Simulate user speech arriving and cancelling the verbal confirmation prompt mid-await
        raise asyncio.CancelledError("Prompt interrupted by new conversational turn")

    res = await gate.intercept_and_confirm("rm -rf /workspace/data", execute_callback=dangerous_action, stt_source_callback=stt_source_interrupt)
    assert "Execution Aborted: Action interrupted before confirmation" in res
    assert execute_called[0] is False
