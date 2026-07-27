import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from app.memory.database import LocalDatabase
from app.tools.messaging_automation import MessagingAutomation
from app.tools.destructive_gate import DestructiveActionGate
from app.core.state_machine import StateMachine, AssistantState

def test_contact_resolution_success_and_failure(tmp_path):
    db_path = tmp_path / "test_contacts.db"
    db = LocalDatabase(str(db_path))
    
    # 1. Add contacts
    db.add_contact("রহিম (Rahim)", "whatsapp", "+8801700000000")
    db.add_contact("Karim", "messenger", "karim.fb")
    
    # 2. Test resolution success (exact, substring, and fuzzy)
    contact1 = db.resolve_contact("রহিম")
    assert contact1 is not None
    assert contact1["app"] == "whatsapp"
    assert contact1["identifier"] == "+8801700000000"
    
    contact2 = db.resolve_contact("Karim", app="messenger")
    assert contact2 is not None
    assert contact2["identifier"] == "karim.fb"
    
    # 3. Test resolution failure
    not_found = db.resolve_contact("Unknown Person Who Does Not Exist")
    assert not_found is None

@pytest.mark.asyncio
async def test_send_success():
    automator = MessagingAutomation(headless=True)
    
    # Mock Playwright page interaction for WhatsApp
    mock_page = AsyncMock()
    mock_page.url = "https://web.whatsapp.com"
    
    async def mock_wait_for_selector(selector, timeout=None):
        if "Scan me!" in selector:
            return None # Assume logged in without QR code
        if "No chats" in selector or "No results" in selector:
            return None # Contact found successfully
        mock_elem = AsyncMock()
        return mock_elem
        
    mock_page.wait_for_selector = mock_wait_for_selector
    mock_context = MagicMock(pages=[mock_page])
    
    with patch("app.tools.messaging_automation.find_native_app_path", return_value=None), \
         patch.object(automator, "_get_context", AsyncMock(return_value=mock_context)):
        res = await automator.send_message("whatsapp", "+8801700000000", "কাল দেখা করব")
        assert res["status"] == "sent"
        assert "Successfully sent WhatsApp message" in res["detail"]
    await automator.close_all()

@pytest.mark.asyncio
async def test_send_failure_element_not_found():
    automator = MessagingAutomation(headless=True)
    
    mock_page = AsyncMock()
    mock_page.url = "https://web.whatsapp.com"
    
    async def mock_wait_for_selector(selector, timeout=None):
        if "Scan me!" in selector:
            return None
        return None # Search input or elements not found
        
    mock_page.wait_for_selector = mock_wait_for_selector
    mock_context = MagicMock(pages=[mock_page])
    
    with patch("app.tools.messaging_automation.find_native_app_path", return_value=None), \
         patch.object(automator, "_get_context", AsyncMock(return_value=mock_context)):
        res = await automator.send_message("whatsapp", "invalid_number", "test")
        assert res["status"] == "failed"
        assert "not found" in res["detail"].lower()
    await automator.close_all()

@pytest.mark.asyncio
async def test_destructive_gate_confirmation_flow():
    sm = StateMachine()
    gate = DestructiveActionGate(sm)
    
    # Simulate vocal affirmation ("হ্যাঁ পাঠাও" or "yes send")
    async def mock_stt_yes():
        return "হ্যাঁ পাঠাও"
        
    confirmed = await gate.request_confirmation("Send message to Rahim on WhatsApp", stt_source_callback=mock_stt_yes)
    assert confirmed is True
    assert sm.current_state == AssistantState.ACTIVE_SPEAKING
    
    # Simulate vocal rejection or silence
    async def mock_stt_no():
        return "না থামো"
        
    rejected = await gate.request_confirmation("Send message to Rahim", stt_source_callback=mock_stt_no)
    assert rejected is False
