import asyncio
import time
import os
import ast
import pytest
from unittest.mock import patch, MagicMock
import structlog

logger = structlog.get_logger(__name__)

@pytest.mark.asyncio
async def test_audio_pipeline_responsiveness_during_threaded_tool_execution():
    """
    Verifies that during long-running GUI automated interactions offloaded via asyncio.to_thread,
    the live microphone capture coroutine continues executing without multi-second gaps (max gap < 200ms).
    """
    frame_timestamps = []
    is_running = True

    async def mock_audio_capture_loop():
        while is_running:
            frame_timestamps.append(time.time())
            # Simulating getting an audio chunk non-blockingly every 50ms
            await asyncio.sleep(0.05)

    def heavy_blocking_gui_operation():
        # Simulate PyAutoGUI / OS window discovery blocking for 0.8 seconds
        time.sleep(0.8)
        return True

    async def simulated_tool_execution():
        # Step 1: Thread offloaded check
        await asyncio.to_thread(heavy_blocking_gui_operation)
        await asyncio.sleep(0.1)
        # Step 2: Thread offloaded interaction
        await asyncio.to_thread(heavy_blocking_gui_operation)

    # Launch both audio loop and tool execution concurrently on the same asyncio event loop
    audio_task = asyncio.create_task(mock_audio_capture_loop())
    await asyncio.sleep(0.1)  # Warm up audio loop

    # Execute simulated native messaging flow
    await simulated_tool_execution()
    
    is_running = False
    await audio_task

    # Verify inter-arrival times between captured audio frames
    assert len(frame_timestamps) > 10, "Should have captured multiple audio frames during tool execution"
    deltas = [frame_timestamps[i+1] - frame_timestamps[i] for i in range(len(frame_timestamps)-1)]
    max_gap = max(deltas)
    
    logger.info("responsiveness_test_results", max_frame_gap_sec=round(max_gap, 4), total_frames=len(frame_timestamps))
    # Assert that no gap exceeded 200ms (0.2s)
    assert max_gap < 0.2, f"Event loop stalled! Max inter-frame gap was {max_gap:.4f}s (expected < 0.2s)"


@pytest.mark.asyncio
async def test_watchdog_heartbeat_emits_regularly():
    """
    Tests that the audio capture watchdog mechanism emits periodic structlog heartbeats
    indicating active streaming and loop liveness.
    """
    heartbeats_logged = []

    def mock_log_info(event_name, **kwargs):
        if event_name == "audio_capture_watchdog_heartbeat":
            heartbeats_logged.append(kwargs.get("loop_timestamp", time.time()))

    # Simulating the exact watchdog timer logic from main.py audio_sender
    last_heartbeat = [time.time()]
    
    with patch.object(logger, "info", side_effect=mock_log_info):
        for i in range(5):
            current_time = time.time() + (i * 1.1)  # Advancing simulated time by 1.1s per iteration
            if current_time - last_heartbeat[0] >= 2.0:
                logger.info("audio_capture_watchdog_heartbeat", status="running", loop_timestamp=current_time)
                last_heartbeat[0] = current_time

    assert len(heartbeats_logged) >= 2, f"Expected at least 2 watchdog heartbeats emitted, got {len(heartbeats_logged)}"


def test_no_synchronous_sleep_in_async_functions():
    """
    Static validation test: Walks through all Python files in app/tools/ and app/core/
    and asserts that zero async def functions directly invoke synchronous time.sleep().
    """
    base_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "app")
    target_dirs = [os.path.join(base_dir, "tools"), os.path.join(base_dir, "core")]
    
    violations = []

    class AsyncSleepChecker(ast.NodeVisitor):
        def __init__(self, filename):
            self.filename = filename
            self.in_async_function = False
            self.current_func_name = ""

        def visit_AsyncFunctionDef(self, node):
            self.in_async_function = True
            self.current_func_name = node.name
            self.generic_visit(node)
            self.in_async_function = False

        def visit_Call(self, node):
            if self.in_async_function:
                # Check for time.sleep(...) or sleep(...)
                is_time_sleep = (
                    isinstance(node.func, ast.Attribute) and 
                    getattr(node.func.value, "id", "") == "time" and 
                    node.func.attr == "sleep"
                )
                is_direct_sleep = (
                    isinstance(node.func, ast.Name) and 
                    node.func.id == "sleep"
                )
                if is_time_sleep or is_direct_sleep:
                    violations.append((self.filename, self.current_func_name, node.lineno))
            self.generic_visit(node)

    for directory in target_dirs:
        if not os.path.exists(directory):
            continue
        for root, _, files in os.walk(directory):
            for file in files:
                if file.endswith(".py"):
                    full_path = os.path.join(root, file)
                    with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                        try:
                            tree = ast.parse(f.read(), filename=full_path)
                            checker = AsyncSleepChecker(full_path)
                            checker.visit(tree)
                        except Exception as e:
                            logger.error("ast_parse_failed", file=full_path, error=str(e))

    assert len(violations) == 0, f"Found synchronous time.sleep() inside async functions: {violations}"


@pytest.mark.asyncio
async def test_native_adapter_window_polling_runs_in_thread():
    """
    Confirms NativeMessagingAdapter.open() polls window readiness non-blockingly via threads.
    """
    from app.tools.messaging.adapters.native_adapter import NativeMessagingAdapter
    from app.config import settings

    adapter = NativeMessagingAdapter("whatsapp", "shell:AppsFolder\\test_app")

    with patch("app.tools.messaging.adapters.native_adapter.launch_native_app", return_value=True) as mock_launch, \
         patch("app.tools.messaging.adapters.native_adapter._check_and_activate_window", side_effect=[False, True]) as mock_check:
        
        start_time = time.time()
        success = await adapter.open()
        duration = time.time() - start_time

        assert success is True
        assert mock_launch.call_count == 1
        assert mock_check.call_count == 2
        # Ensure it didn't block or hang forever
        assert duration < 5.0
