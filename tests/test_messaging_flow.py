import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from app.memory.database import LocalDatabase
from app.tools.messaging_automation import MessagingAutomation
from app.tools.messaging.utils import normalize_to_e164
from app.tools.destructive_gate import DestructiveActionGate
from app.core.state_machine import StateMachine, AssistantState
from app.tools.messaging.exceptions import (
    ContactSearchBoxNotFoundError,
    ContactResultNotFoundError,
    ComposeBoxNotFoundError,
    SendButtonNotFoundError
)

def test_e164_normalization_with_bengali_and_local():
    # Bengali digits with leading zero
    assert normalize_to_e164("০১৭০০০০০০০০") == "+8801700000000"
    # Local English digits with leading zero
    assert normalize_to_e164("01812345678") == "+8801812345678"
    # Already E.164
    assert normalize_to_e164("+8801912345678") == "+8801912345678"
    # Starting with 880 without plus
    assert normalize_to_e164("8801711223344") == "+8801711223344"
    # International number
    assert normalize_to_e164("+14155552671") == "+14155552671"

@pytest.mark.asyncio
async def test_native_desktop_app_flow(tmp_path):
    db_path = tmp_path / "test_native.db"
    db = LocalDatabase(str(db_path))
    db.add_contact("রহিম", "whatsapp", "+8801700000000", source="manual")

    sm = StateMachine()
    gate = DestructiveActionGate(sm)

    automator = MessagingAutomation(headless=True, db=db, gate=gate)

    mock_adapter = AsyncMock()
    mock_adapter.open.return_value = True
    mock_adapter.find_contact_by_name.return_value = True
    mock_adapter.type_message.return_value = True
    mock_adapter.send.return_value = True
    mock_adapter.confirm_sent.return_value = True

    async def mock_stt_confirm():
        return "হ্যাঁ পাঠাও"

    with patch("app.tools.messaging_automation.find_native_app_path", return_value="C:\\Program Files\\WhatsApp\\WhatsApp.exe"), \
         patch("app.tools.messaging_automation.NativeMessagingAdapter", return_value=mock_adapter):
        
        res = await automator.send_message("whatsapp", "রহিম", "কাল দেখা করব", stt_callback=mock_stt_confirm)
        assert res["status"] == "sent"
        assert "WhatsApp" in res["detail"]
        
        # Verify DB last_used_at timestamp was updated
        contact = db.resolve_contact("রহিম", app="whatsapp")
        assert contact["last_used_at"] is not None

@pytest.mark.asyncio
async def test_web_adapter_fallback_and_db_resolution(tmp_path):
    db_path = tmp_path / "test_web_fallback.db"
    db = LocalDatabase(str(db_path))
    db.add_contact("Karim", "telegram", "+8801800000000")

    automator = MessagingAutomation(headless=True, db=db, gate=None)

    mock_web_adapter = AsyncMock()
    mock_web_adapter.open.return_value = True
    mock_web_adapter.find_contact_by_name.return_value = True
    mock_web_adapter.type_message.return_value = True
    mock_web_adapter.send.return_value = True
    mock_web_adapter.confirm_sent.return_value = True

    with patch("app.tools.messaging_automation.find_native_app_path", return_value=None), \
         patch.object(automator, "_init_web_adapter", AsyncMock(return_value=mock_web_adapter)):
        
        res = await automator.send_message("telegram", "Karim", "Hi Karim!", require_confirmation=False)
        assert res["status"] == "sent"
        assert "Telegram" in res["detail"]
        mock_web_adapter.open.assert_called_once()
        mock_web_adapter.find_contact_by_name.assert_called_once_with("Karim")

@pytest.mark.asyncio
async def test_voice_prompt_for_missing_phone_and_auto_save(tmp_path):
    db_path = tmp_path / "test_voice_prompt.db"
    db = LocalDatabase(str(db_path))
    
    # Notice: "Sajid" is NOT in DB initially
    assert db.resolve_contact("Sajid", app="whatsapp") is None

    sm = StateMachine()
    gate = DestructiveActionGate(sm)
    automator = MessagingAutomation(headless=True, db=db, gate=gate)

    mock_adapter = AsyncMock()
    mock_adapter.open.return_value = True
    mock_adapter.find_contact_by_name.return_value = False # First name search fails!
    mock_adapter.find_contact_by_number.return_value = True # Second number search succeeds!
    mock_adapter.type_message.return_value = True
    mock_adapter.send.return_value = True
    mock_adapter.confirm_sent.return_value = True

    stt_calls = [0]
    async def mock_stt():
        stt_calls[0] += 1
        if stt_calls[0] == 1:
            return "০১৭৯৯৯৯৯৯৯৯" # User verbally responds with phone number in Bengali digits
        else:
            return "yes send" # User confirms sending at destructive gate

    tts_messages = []
    async def mock_tts(msg):
        tts_messages.append(msg)

    with patch("app.tools.messaging_automation.find_native_app_path", return_value=None), \
         patch.object(automator, "_init_web_adapter", AsyncMock(return_value=mock_adapter)):
        
        res = await automator.send_message(
            "whatsapp", "Sajid", "Meet me at 5 PM",
            stt_callback=mock_stt,
            tts_callback=mock_tts,
            require_confirmation=True
        )
        
        assert res["status"] == "sent"
        assert len(tts_messages) == 2
        assert "খুঁজে পাইনি" in tts_messages[0] # Verbally asked for number!
        assert "+8801799999999" in tts_messages[1] # Verbally asked for number confirmation readback!
        
        # Verify contact was saved with source='chat_auto_saved' and normalized E.164 number
        saved = db.resolve_contact("Sajid", app="whatsapp")
        assert saved is not None
        assert saved["identifier"] == "+8801799999999"
        assert saved["source"] == "chat_auto_saved"
        assert saved["last_used_at"] is not None

@pytest.mark.asyncio
async def test_destructive_gate_rejection_prevents_send(tmp_path):
    db_path = tmp_path / "test_gate_rejection.db"
    db = LocalDatabase(str(db_path))
    db.add_contact("Tanveer", "messenger", "tanveer.id")

    sm = StateMachine()
    gate = DestructiveActionGate(sm)
    automator = MessagingAutomation(headless=True, db=db, gate=gate)

    mock_adapter = AsyncMock()
    mock_adapter.open.return_value = True
    mock_adapter.find_contact_by_name.return_value = True
    mock_adapter.type_message.return_value = True
    
    # User rejects sending at the gate
    async def mock_stt_no():
        return "না পাঠিও না" # "No do not send"

    with patch("app.tools.messaging_automation.find_native_app_path", return_value=None), \
         patch.object(automator, "_init_web_adapter", AsyncMock(return_value=mock_adapter)):
        
        res = await automator.send_message("messenger", "Tanveer", "Secret message", stt_callback=mock_stt_no, require_confirmation=True)
        
        assert res["status"] == "failed"
        assert "not confirmed" in res["detail"]
        # Ensure send() was NEVER called!
        mock_adapter.send.assert_not_called()

@pytest.mark.asyncio
async def test_native_app_not_found_falls_back_to_browser():
    automator = MessagingAutomation(headless=True, db=None, gate=None)
    mock_web = AsyncMock()
    mock_web.open.return_value = True
    mock_web.find_contact_by_name.return_value = True
    mock_web.type_message.return_value = True
    mock_web.send.return_value = True
    mock_web.confirm_sent.return_value = True

    with patch("app.tools.messaging_automation.find_native_app_path", return_value=None), \
         patch.object(automator, "_init_web_adapter", AsyncMock(return_value=mock_web)):
        res = await automator.send_message("whatsapp", "Alice", "Hello World", require_confirmation=False)
        assert res["status"] == "sent"
        assert "WhatsApp" in res["detail"]
        mock_web.open.assert_called_once()
        mock_web.send.assert_called_once()

@pytest.mark.asyncio
async def test_native_app_launch_raises_exception_falls_back_to_browser():
    automator = MessagingAutomation(headless=True, db=None, gate=None)
    mock_web = AsyncMock()
    mock_web.open.return_value = True
    mock_web.find_contact_by_name.return_value = True
    mock_web.type_message.return_value = True
    mock_web.send.return_value = True
    mock_web.confirm_sent.return_value = True

    mock_native = AsyncMock()
    mock_native.open.side_effect = RuntimeError("Simulated UWP launch exception")

    with patch("app.tools.messaging_automation.find_native_app_path", return_value="shell:AppsFolder\\5319275A.WhatsAppDesktop!App"), \
         patch("app.tools.messaging_automation.NativeMessagingAdapter", return_value=mock_native), \
         patch.object(automator, "_init_web_adapter", AsyncMock(return_value=mock_web)):
        res = await automator.send_message("whatsapp", "Bob", "Testing exception fallback", require_confirmation=False)
        assert res["status"] == "sent"
        mock_native.open.assert_called_once()
        mock_web.open.assert_called_once()
        mock_web.send.assert_called_once()

@pytest.mark.asyncio
async def test_native_app_window_ready_timeout_falls_back_to_browser():
    automator = MessagingAutomation(headless=True, db=None, gate=None)
    mock_web = AsyncMock()
    mock_web.open.return_value = True
    mock_web.find_contact_by_name.return_value = True
    mock_web.type_message.return_value = True
    mock_web.send.return_value = True
    mock_web.confirm_sent.return_value = True

    mock_native = AsyncMock()
    # Simulates native adapter returning False after window polling timeout
    mock_native.open.return_value = False

    with patch("app.tools.messaging_automation.find_native_app_path", return_value="whatsapp:"), \
         patch("app.tools.messaging_automation.NativeMessagingAdapter", return_value=mock_native), \
         patch.object(automator, "_init_web_adapter", AsyncMock(return_value=mock_web)):
        res = await automator.send_message("whatsapp", "Charlie", "Timeout test", require_confirmation=False)
        assert res["status"] == "sent"
        mock_native.open.assert_called_once()
        mock_web.open.assert_called_once()
        mock_web.send.assert_called_once()

@pytest.mark.asyncio
async def test_no_unhandled_exception_escapes_send_message():
    automator = MessagingAutomation(headless=True, db=None, gate=None)

    # Catastrophic error in both native app check and web adapter initialization
    with patch("app.tools.messaging_automation.find_native_app_path", return_value="whatsapp:"), \
         patch("app.tools.messaging_automation.NativeMessagingAdapter", side_effect=RuntimeError("Native adapter crashed")), \
         patch.object(automator, "_init_web_adapter", side_effect=ValueError("Total crash of web driver")):
        res = await automator.send_message("whatsapp", "Dave", "Crash test", require_confirmation=False)
        assert res["status"] == "failed"
        assert "Total crash of web driver" in res["detail"] or "failed to initialize" in res["detail"] or "Error during messaging automation" in res["detail"]

@pytest.mark.asyncio
async def test_native_search_box_not_found_raises_and_falls_back_to_browser():
    automator = MessagingAutomation(headless=True, db=None, gate=None)
    mock_web = AsyncMock()
    mock_web.open.return_value = True
    mock_web.find_contact_by_name.return_value = True
    mock_web.type_message.return_value = True
    mock_web.send.return_value = True
    mock_web.confirm_sent.return_value = True

    mock_native = AsyncMock()
    mock_native.open.return_value = True
    mock_native.find_contact_by_name.side_effect = ContactSearchBoxNotFoundError("Search box not located")

    with patch("app.tools.messaging_automation.find_native_app_path", return_value="whatsapp:"), \
         patch("app.tools.messaging_automation.NativeMessagingAdapter", return_value=mock_native), \
         patch.object(automator, "_init_web_adapter", AsyncMock(return_value=mock_web)):
        res = await automator.send_message("whatsapp", "Eva", "Fallback search box test", require_confirmation=False)
        assert res["status"] == "sent"
        mock_native.open.assert_called_once()
        mock_web.open.assert_called_once()
        mock_web.send.assert_called_once()

@pytest.mark.asyncio
async def test_native_contact_result_not_found_raises_and_falls_back_to_browser():
    automator = MessagingAutomation(headless=True, db=None, gate=None)
    mock_web = AsyncMock()
    mock_web.open.return_value = True
    mock_web.find_contact_by_name.return_value = True
    mock_web.type_message.return_value = True
    mock_web.send.return_value = True
    mock_web.confirm_sent.return_value = True

    mock_native = AsyncMock()
    mock_native.open.return_value = True
    mock_native.find_contact_by_name.side_effect = ContactResultNotFoundError("Contact result not found")

    with patch("app.tools.messaging_automation.find_native_app_path", return_value="whatsapp:"), \
         patch("app.tools.messaging_automation.NativeMessagingAdapter", return_value=mock_native), \
         patch.object(automator, "_init_web_adapter", AsyncMock(return_value=mock_web)):
        res = await automator.send_message("whatsapp", "Frank", "Fallback result test", require_confirmation=False)
        assert res["status"] == "sent"
        mock_web.open.assert_called_once()

@pytest.mark.asyncio
async def test_native_compose_box_not_found_raises_and_falls_back_to_browser():
    automator = MessagingAutomation(headless=True, db=None, gate=None)
    mock_web = AsyncMock()
    mock_web.open.return_value = True
    mock_web.find_contact_by_name.return_value = True
    mock_web.type_message.return_value = True
    mock_web.send.return_value = True
    mock_web.confirm_sent.return_value = True

    mock_native = AsyncMock()
    mock_native.open.return_value = True
    mock_native.find_contact_by_name.return_value = True
    mock_native.type_message.side_effect = ComposeBoxNotFoundError("Compose box not found")

    with patch("app.tools.messaging_automation.find_native_app_path", return_value="whatsapp:"), \
         patch("app.tools.messaging_automation.NativeMessagingAdapter", return_value=mock_native), \
         patch.object(automator, "_init_web_adapter", AsyncMock(return_value=mock_web)):
        res = await automator.send_message("whatsapp", "Grace", "Fallback compose test", require_confirmation=False)
        assert res["status"] == "sent"
        mock_web.open.assert_called_once()
        mock_web.find_contact_by_name.assert_called_once()

@pytest.mark.asyncio
async def test_native_send_button_not_found_raises_and_falls_back_to_browser():
    automator = MessagingAutomation(headless=True, db=None, gate=None)
    mock_web = AsyncMock()
    mock_web.open.return_value = True
    mock_web.find_contact_by_name.return_value = True
    mock_web.type_message.return_value = True
    mock_web.send.return_value = True
    mock_web.confirm_sent.return_value = True

    mock_native = AsyncMock()
    mock_native.open.return_value = True
    mock_native.find_contact_by_name.return_value = True
    mock_native.type_message.return_value = True
    mock_native.send.side_effect = SendButtonNotFoundError("Send button not found")

    with patch("app.tools.messaging_automation.find_native_app_path", return_value="whatsapp:"), \
         patch("app.tools.messaging_automation.NativeMessagingAdapter", return_value=mock_native), \
         patch.object(automator, "_init_web_adapter", AsyncMock(return_value=mock_web)):
        res = await automator.send_message("whatsapp", "Henry", "Fallback send button test", require_confirmation=False)
        assert res["status"] == "sent"
        mock_web.open.assert_called_once()
        mock_web.send.assert_called_once()

@pytest.mark.asyncio
async def test_native_happy_path_step_by_step_logging_and_sent_confirmation():
    automator = MessagingAutomation(headless=True, db=None, gate=None)
    mock_native = AsyncMock()
    mock_native.open.return_value = True
    mock_native.find_contact_by_name.return_value = True
    mock_native.type_message.return_value = True
    mock_native.send.return_value = True
    mock_native.confirm_sent.return_value = True

    with patch("app.tools.messaging_automation.find_native_app_path", return_value="whatsapp:"), \
         patch("app.tools.messaging_automation.NativeMessagingAdapter", return_value=mock_native), \
         patch.object(automator, "_init_web_adapter", AsyncMock()) as mock_init_web:
        res = await automator.send_message("whatsapp", "Ivy", "Happy path native", require_confirmation=False)
        assert res["status"] == "sent"
        mock_native.open.assert_called_once()
        mock_native.find_contact_by_name.assert_called_once_with("Ivy")
        mock_native.type_message.assert_called_once_with("Happy path native")
        mock_native.send.assert_called_once()
        mock_native.confirm_sent.assert_called_once()
        mock_init_web.assert_not_called()
