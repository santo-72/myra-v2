import pytest
import asyncio
import time
from unittest.mock import patch, MagicMock, AsyncMock

from app.tools.messaging_automation import MessagingAutomation
from app.tools.messaging.adapters.native_adapter import NativeMessagingAdapter
from app.tools.messaging.adapters.whatsapp_adapter import WhatsAppWebAdapter
from app.tools.messaging.contact_capture import ContactCaptureStateMachine, ContactCaptureState
from app.core.state_machine import StateMachine, AssistantState
from app.memory.database import LocalDatabase

@pytest.fixture
def memory_db(tmp_path):
    db = LocalDatabase(str(tmp_path / "test_whatsapp_native.db"))
    return db

@pytest.fixture
def state_machine():
    return StateMachine()

@pytest.fixture
def messaging_automator(memory_db, state_machine):
    return MessagingAutomation(headless=True, db=memory_db, state_machine=state_machine)

@pytest.mark.asyncio
async def test_whatsapp_native_send_success_by_name(messaging_automator):
    """1. Successful send when contact found by name via native app."""
    mock_native = AsyncMock(spec=NativeMessagingAdapter)
    mock_native.open.return_value = True
    mock_native.find_contact_by_name.return_value = True
    mock_native.type_message.return_value = True
    mock_native.send.return_value = True
    mock_native.confirm_sent.return_value = True
    mock_native.close.return_value = None

    with patch("app.tools.messaging_automation.find_native_app_path", return_value="shell:AppsFolder\\whatsapp_uwp"), \
         patch("app.tools.messaging_automation.NativeMessagingAdapter", return_value=mock_native):
         
        res = await messaging_automator.send_message(
            app="whatsapp",
            recipient_identifier="রহিম",
            message="কাল দেখা করব",
            require_confirmation=False
        )
        
        assert res.get("status") == "sent"
        assert "native" in res.get("delivery_method", "") or "native" in res.get("path_attempted", "")
        mock_native.open.assert_awaited_once()
        mock_native.find_contact_by_name.assert_awaited_once_with("রহিম")
        mock_native.type_message.assert_awaited_once_with("কাল দেখা করব")
        mock_native.send.assert_awaited_once()

@pytest.mark.asyncio
async def test_whatsapp_native_contact_not_found_number_captured_and_saved(messaging_automator, memory_db, state_machine):
    """2. Contact not found -> number requested -> confirmed -> sent -> saved to DB."""
    mock_native = AsyncMock(spec=NativeMessagingAdapter)
    mock_native.open.return_value = True
    # Name search fails (contact not found)
    mock_native.find_contact_by_name.return_value = False
    # Number search succeeds when tried later
    mock_native.find_contact_by_number.return_value = True
    mock_native.type_message.return_value = True
    mock_native.send.return_value = True
    mock_native.confirm_sent.return_value = True
    mock_native.close.return_value = None

    # Also make sure web fallback search returns false initially so it prompts for number
    mock_web = AsyncMock(spec=WhatsAppWebAdapter)
    mock_web.open.return_value = True
    mock_web.find_contact_by_name.return_value = False
    mock_web.find_contact_by_number.return_value = True
    mock_web.type_message.return_value = True
    mock_web.send.return_value = True
    mock_web.confirm_sent.return_value = True
    mock_web.close.return_value = None

    stt_responses = ["01711223344", "হ্যাঁ"]
    async def mock_stt_callback(timeout_sec=20.0):
        if stt_responses:
            return stt_responses.pop(0)
        return ""

    tts_msgs = []
    async def mock_tts_callback(text):
        tts_msgs.append(text)

    with patch("app.tools.messaging_automation.find_native_app_path", return_value="shell:AppsFolder\\whatsapp_uwp"), \
         patch("app.tools.messaging_automation.NativeMessagingAdapter", return_value=mock_native), \
         patch.object(messaging_automator, "_init_web_adapter", return_value=mock_web):
         
        res = await messaging_automator.send_message(
            app="whatsapp",
            recipient_identifier="রহিম",
            message="কাল দেখা করব",
            stt_callback=mock_stt_callback,
            tts_callback=mock_tts_callback,
            require_confirmation=False
        )

        assert res.get("status") == "sent"
        # Verify contact was auto-saved in DB under Rahim
        saved = memory_db.resolve_contact("রহিম", "whatsapp")
        if not saved:
            saved = memory_db.resolve_contact("রহিম")
        assert saved is not None
        assert "+8801711223344" in saved["identifier"] or "01711223344" in saved["identifier"]

@pytest.mark.asyncio
async def test_whatsapp_native_number_request_timeout(messaging_automator, state_machine):
    """3. Timeout on number request -> clean cancellation without hanging."""
    mock_native = AsyncMock(spec=NativeMessagingAdapter)
    mock_native.open.return_value = True
    mock_native.find_contact_by_name.return_value = False

    mock_web = AsyncMock(spec=WhatsAppWebAdapter)
    mock_web.open.return_value = True
    mock_web.find_contact_by_name.return_value = False

    async def mock_stt_timeout(timeout_sec=20.0):
        raise asyncio.TimeoutError("User did not speak in time")

    tts_msgs = []
    async def mock_tts(text):
        tts_msgs.append(text)

    with patch("app.tools.messaging_automation.find_native_app_path", return_value="shell:AppsFolder\\whatsapp_uwp"), \
         patch("app.tools.messaging_automation.NativeMessagingAdapter", return_value=mock_native), \
         patch.object(messaging_automator, "_init_web_adapter", return_value=mock_web):
         
        res = await messaging_automator.send_message(
            app="whatsapp",
            recipient_identifier="রহিম",
            message="কাল দেখা করব",
            stt_callback=mock_stt_timeout,
            tts_callback=mock_tts,
            require_confirmation=False
        )

        assert res.get("status") == "timeout" or res.get("status") == "cancelled"
        assert any("বাদ থাক" in m for m in tts_msgs)

@pytest.mark.asyncio
async def test_whatsapp_native_invalid_number_retry_then_cancel(memory_db, state_machine):
    """4. Invalid number retry then cancellation cleanly in ContactCaptureStateMachine."""
    flow = ContactCaptureStateMachine(db=memory_db, main_state_machine=state_machine)
    
    stt_responses = ["invalid", "invalid_again", "still_invalid", "more_invalid"]
    async def mock_stt(timeout_sec=20.0):
        if stt_responses:
            return stt_responses.pop(0)
        return ""
        
    tts_msgs = []
    async def mock_tts(text):
        tts_msgs.append(text)

    res = await flow.execute("রহিম", "whatsapp", mock_stt, mock_tts)
    
    assert res.get("status") == "cancelled"
    assert flow.current_state == ContactCaptureState.CANCELLED

@pytest.mark.asyncio
async def test_whatsapp_native_launch_failure_browser_fallback(messaging_automator):
    """5. Native app launch failure -> web browser fallback path succeeds."""
    mock_web = AsyncMock(spec=WhatsAppWebAdapter)
    mock_web.open.return_value = True
    mock_web.find_contact_by_name.return_value = True
    mock_web.type_message.return_value = True
    mock_web.send.return_value = True
    mock_web.confirm_sent.return_value = True

    # find_native_app_path returns None (or app fail to launch)
    with patch("app.tools.messaging_automation.find_native_app_path", return_value=None), \
         patch.object(messaging_automator, "_init_web_adapter", return_value=mock_web):
         
        res = await messaging_automator.send_message(
            app="whatsapp",
            recipient_identifier="রহিম",
            message="কাল দেখা করব",
            require_confirmation=False
        )
        
        assert res.get("status") == "sent"
        assert "browser" in res.get("delivery_method", "") or "browser" in res.get("path_attempted", "")
        mock_web.open.assert_awaited_once()
        mock_web.find_contact_by_name.assert_awaited_once_with("রহিম")

@pytest.mark.asyncio
async def test_whatsapp_native_non_blocking_event_loop_responsiveness(messaging_automator):
    """6. Non-blocking/event-loop-responsiveness requirement from section E."""
    frame_timestamps = []
    is_capturing = True

    async def mock_audio_capture():
        while is_capturing:
            frame_timestamps.append(time.time())
            await asyncio.sleep(0.05)

    mock_native = AsyncMock(spec=NativeMessagingAdapter)
    
    async def simulated_threaded_open():
        await asyncio.sleep(0.1)
        await asyncio.to_thread(lambda: time.sleep(0.4))
        return True

    mock_native.open = simulated_threaded_open
    mock_native.find_contact_by_name.return_value = True
    mock_native.type_message.return_value = True
    mock_native.send.return_value = True
    mock_native.confirm_sent.return_value = True

    capture_task = asyncio.create_task(mock_audio_capture())
    await asyncio.sleep(0.05)

    with patch("app.tools.messaging_automation.find_native_app_path", return_value="shell:AppsFolder\\whatsapp_uwp"), \
         patch("app.tools.messaging_automation.NativeMessagingAdapter", return_value=mock_native):
         
        await messaging_automator.send_message(
            app="whatsapp",
            recipient_identifier="রহিম",
            message="কাল দেখা করব",
            require_confirmation=False
        )

    is_capturing = False
    await capture_task

    assert len(frame_timestamps) > 5
    deltas = [frame_timestamps[i+1] - frame_timestamps[i] for i in range(len(frame_timestamps)-1)]
    max_gap = max(deltas)
    
    assert max_gap < 0.2, f"Audio loop stalled! Max inter-frame gap was {max_gap:.4f}s during WhatsApp messaging"
