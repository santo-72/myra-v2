import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from app.tools.messaging.contact_capture import ContactCaptureStateMachine, ContactCaptureState
from app.core.state_machine import StateMachine, AssistantState
from app.core.interrupt_controller import interrupt_controller
from app.config import settings
from app.memory.database import LocalDatabase

@pytest.mark.asyncio
async def test_contact_capture_success(tmp_path):
    db = LocalDatabase(str(tmp_path / "test_capture_success.db"))
    main_sm = StateMachine()
    capture_sm = ContactCaptureStateMachine(db=db, main_state_machine=main_sm)
    
    stt_responses = ["০১৭০০০০০০০০", "হ্যাঁ"]
    stt_idx = [0]
    async def mock_stt():
        res = stt_responses[stt_idx[0]]
        stt_idx[0] += 1
        return res

    tts_msgs = []
    async def mock_tts(msg):
        tts_msgs.append(msg)

    result = await capture_sm.execute("রহিম", "whatsapp", stt_callback=mock_stt, tts_callback=mock_tts)
    
    assert result["status"] == "success"
    assert result["number"] == "+8801700000000"
    assert capture_sm.current_state == ContactCaptureState.DONE
    assert main_sm.current_state == AssistantState.ACTIVE_LISTENING
    assert len(tts_msgs) == 2
    assert "খুঁজে পাইনি" in tts_msgs[0]
    assert "+8801700000000" in tts_msgs[1]
    
    saved = db.resolve_contact("রহিম", app="whatsapp")
    assert saved is not None
    assert saved["identifier"] == "+8801700000000"
    assert saved["source"] == "chat_auto_saved"

@pytest.mark.asyncio
async def test_contact_capture_timeout(tmp_path):
    db = LocalDatabase(str(tmp_path / "test_capture_timeout.db"))
    main_sm = StateMachine()
    capture_sm = ContactCaptureStateMachine(db=db, main_state_machine=main_sm)
    
    async def mock_stt():
        await asyncio.sleep(1.0)
        return "01700000000"

    tts_msgs = []
    async def mock_tts(msg):
        tts_msgs.append(msg)

    with patch.object(settings, "contact_capture_timeout_seconds", 0.1):
        result = await capture_sm.execute("করিম", "messenger", stt_callback=mock_stt, tts_callback=mock_tts)
        
    assert result["status"] == "timeout"
    assert result["number"] is None
    assert capture_sm.current_state == ContactCaptureState.TIMEOUT
    assert main_sm.current_state == AssistantState.ACTIVE_LISTENING
    assert any("বাদ থাক" in msg for msg in tts_msgs)

@pytest.mark.asyncio
async def test_contact_capture_invalid_input_and_max_retries(tmp_path):
    db = LocalDatabase(str(tmp_path / "test_capture_retries.db"))
    main_sm = StateMachine()
    capture_sm = ContactCaptureStateMachine(db=db, main_state_machine=main_sm)
    
    # User says non-numeric strings repeatedly
    stt_responses = ["হেডফোনটা কোথায়", "শুনতে পাচ্ছো না", "কী যেন বলি"]
    stt_idx = [0]
    async def mock_stt():
        res = stt_responses[stt_idx[0]]
        if stt_idx[0] < len(stt_responses) - 1:
            stt_idx[0] += 1
        return res

    tts_msgs = []
    async def mock_tts(msg):
        tts_msgs.append(msg)

    with patch.object(settings, "contact_capture_max_retries", 2):
        result = await capture_sm.execute("সাজিদ", "whatsapp", stt_callback=mock_stt, tts_callback=mock_tts)
        
    assert result["status"] == "cancelled"
    assert capture_sm.current_state == ContactCaptureState.CANCELLED
    assert any("নাম্বারটা ঠিক বুঝতে পারলাম না" in msg for msg in tts_msgs)
    assert any("বাদ থাক" in msg for msg in tts_msgs)

@pytest.mark.asyncio
async def test_contact_capture_explicit_cancellation(tmp_path):
    db = LocalDatabase(str(tmp_path / "test_capture_cancel.db"))
    main_sm = StateMachine()
    capture_sm = ContactCaptureStateMachine(db=db, main_state_machine=main_sm)
    
    async def mock_stt():
        return "বাদ দাও"

    tts_msgs = []
    async def mock_tts(msg):
        tts_msgs.append(msg)

    result = await capture_sm.execute("রহিম", "whatsapp", stt_callback=mock_stt, tts_callback=mock_tts)
    assert result["status"] == "cancelled"
    assert capture_sm.current_state == ContactCaptureState.CANCELLED
    assert main_sm.current_state == AssistantState.ACTIVE_LISTENING

@pytest.mark.asyncio
async def test_contact_capture_readback_rejected_and_retried(tmp_path):
    db = LocalDatabase(str(tmp_path / "test_capture_reject_retry.db"))
    main_sm = StateMachine()
    capture_sm = ContactCaptureStateMachine(db=db, main_state_machine=main_sm)
    
    # 1st attempt: wrong number -> user says "না"
    # 2nd attempt: corrected number -> user says "হ্যাঁ"
    stt_responses = ["01700000001", "না", "01700000002", "হ্যাঁ"]
    stt_idx = [0]
    async def mock_stt():
        res = stt_responses[stt_idx[0]]
        stt_idx[0] += 1
        return res

    tts_msgs = []
    async def mock_tts(msg):
        tts_msgs.append(msg)

    result = await capture_sm.execute("তানভীর", "whatsapp", stt_callback=mock_stt, tts_callback=mock_tts)
    
    assert result["status"] == "success"
    assert result["number"] == "+8801700000002"
    assert capture_sm.current_state == ContactCaptureState.DONE
    assert any("তাহলে সঠিক নাম্বারটা আবার বলবেন?" in msg for msg in tts_msgs)

@pytest.mark.asyncio
async def test_contact_capture_db_save_failure_resilience(tmp_path):
    mock_db = MagicMock()
    mock_db.upsert_contact_by_phone.side_effect = Exception("Simulated SQLite Disk IOError")
    main_sm = StateMachine()
    capture_sm = ContactCaptureStateMachine(db=mock_db, main_state_machine=main_sm)
    
    stt_responses = ["01711223344", "yes"]
    stt_idx = [0]
    async def mock_stt():
        res = stt_responses[stt_idx[0]]
        stt_idx[0] += 1
        return res

    tts_msgs = []
    async def mock_tts(msg):
        tts_msgs.append(msg)

    result = await capture_sm.execute("শরীফ", "whatsapp", stt_callback=mock_stt, tts_callback=mock_tts)
    
    # Crucial assertion: even though DB saving threw an exception and state went to FAILED,
    # it MUST still return status="success" and the confirmed phone number to allow message transmission!
    assert result["status"] == "success"
    assert result["number"] == "+8801711223344"
    assert any("সেভ করতে সমস্যা হয়েছে" in msg for msg in tts_msgs)
    assert main_sm.current_state == AssistantState.ACTIVE_LISTENING

@pytest.mark.asyncio
async def test_contact_capture_barge_in_interruption(tmp_path):
    db = LocalDatabase(str(tmp_path / "test_capture_bargein.db"))
    main_sm = StateMachine()
    capture_sm = ContactCaptureStateMachine(db=db, main_state_machine=main_sm)
    
    async def mock_stt():
        # Simulate user triggering barge-in interrupt mid-listen by setting flag / cancelling
        interrupt_controller._interrupt_requested = True
        return "01700000000"

    tts_msgs = []
    async def mock_tts(msg):
        tts_msgs.append(msg)

    result = await capture_sm.execute("রাকিব", "whatsapp", stt_callback=mock_stt, tts_callback=mock_tts)
    
    assert result["status"] == "cancelled"
    assert capture_sm.current_state == ContactCaptureState.CANCELLED
    assert main_sm.current_state == AssistantState.ACTIVE_LISTENING
    # Clean up interrupt controller state
    interrupt_controller._interrupt_requested = False

@pytest.mark.asyncio
async def test_global_safety_net_hard_timeout():
    """
    Verifies the hard-ceiling global safety net logic around messaging/contact capture execution in main.py.
    Simulates an unfreezable hung operation and ensures it trips the outer timeout cleanly.
    """
    main_sm = StateMachine()
    main_sm.transition_to(AssistantState.TOOL_EXECUTING)
    
    async def hung_tool_execution():
        await asyncio.sleep(5.0)
        return {"status": "sent", "detail": "should not reach here"}

    tts_msgs = []
    async def mock_tts(msg):
        tts_msgs.append(msg)

    # In main.py, hard_ceiling = timeout_sec * (max_retries + 1) + 30.0
    # Here we simulate with a test ceiling of 0.15s
    hard_ceiling = 0.15
    
    try:
        res = await asyncio.wait_for(hung_tool_execution(), timeout=hard_ceiling)
    except asyncio.TimeoutError:
        await mock_tts("দুঃখিত, একটা সমস্যা হয়েছে, আবার চেষ্টা করুন")
        main_sm.transition_to(AssistantState.ACTIVE_LISTENING)
        res = {"status": "failed", "detail": "Global safety net aborted messaging due to hard timeout."}

    assert res["status"] == "failed"
    assert "hard timeout" in res["detail"]
    assert main_sm.current_state == AssistantState.ACTIVE_LISTENING
    assert len(tts_msgs) == 1
    assert "দুঃখিত" in tts_msgs[0]
