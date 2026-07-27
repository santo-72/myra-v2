import pytest
import asyncio
import os
from pathlib import Path
from app.memory.database import LocalDatabase
from app.audio.pipeline import AudioPipeline
from app.core.gemini_live_client import GeminiLiveClient

@pytest.fixture
def test_db(tmp_path):
    db_path = str(tmp_path / "test_stt.db")
    db = LocalDatabase(db_path=db_path)
    return db

def test_stt_corrections_table_upsert_and_retrieval(test_db):
    # Test initial insertion
    assert test_db.log_stt_correction("রোহিম", "রহিম") is True
    assert test_db.log_stt_correction("কোরিম", "করিম") is True
    
    # Test occurrence increment on identical correction
    test_db.log_stt_correction("রোহিম", "রহিম")
    
    corrections = test_db.get_stt_corrections(limit=10)
    assert len(corrections) == 2
    
    # Verify order by occurrences DESC
    assert corrections[0]["misheard_text"] == "রোহিম"
    assert corrections[0]["corrected_text"] == "রহিম"
    assert corrections[0]["occurrences"] == 2
    assert corrections[1]["misheard_text"] == "কোরিম"
    assert corrections[1]["occurrences"] == 1

def test_custom_hotword_building_from_contacts_and_corrections(test_db):
    # Add mock contacts
    test_db.add_contact("Santo Ghosh", "whatsapp", "+8801700000001")
    test_db.add_contact("Tanvir Hasan", "messenger", "tanvir_dev")
    
    # Add learned STT corrections
    test_db.log_stt_correction("প্লে রাইট", "Playwright")
    test_db.log_stt_correction("মাইরা", "Myra")
    
    hotwords = test_db.build_custom_hotwords()
    assert isinstance(hotwords, list)
    assert "Santo Ghosh" in hotwords
    assert "Tanvir Hasan" in hotwords
    assert "Playwright" in hotwords
    assert "Myra" in hotwords
    assert "WhatsApp" in hotwords
    assert "Python" in hotwords

def test_stt_confidence_clarification_trigger():
    candidate_terms = ["Rahim", "Karim", "Tanvir"]
    
    # 1. High confidence -> No clarification needed
    res_high = AudioPipeline.evaluate_stt_confidence_and_clarify("Rahim is calling", candidate_terms, confidence_score=0.95)
    assert res_high["clarify"] is False
    assert res_high["question"] is None

    # 2. Low confidence with ambiguous matching -> Trigger polite Bengali clarifying question
    res_ambiguous = AudioPipeline.evaluate_stt_confidence_and_clarify("Please message rahim or karim", candidate_terms, confidence_score=0.55)
    assert res_ambiguous["clarify"] is True
    assert res_ambiguous["question"] is not None
    assert "রহিম বললেন, নাকি করিম?" in res_ambiguous["question"] or "স্যার," in res_ambiguous["question"]
    assert len(res_ambiguous["candidates"]) > 0

def test_detect_and_log_speech_correction_loop(test_db):
    # Test conversational correction utterance detection
    sample_text = "না রোহিম নয় রহিম"
    pair = AudioPipeline.detect_and_log_speech_correction(sample_text, db=test_db)
    assert pair is not None
    assert pair == ("রোহিম", "রহিম")
    
    # Ensure correction was logged directly to database
    corrections = test_db.get_stt_corrections()
    assert len(corrections) > 0
    assert corrections[0]["corrected_text"] == "রহিম"

@pytest.mark.asyncio
async def test_gemini_live_client_voice_config_dynamic_env(monkeypatch):
    from app.config import settings
    
    # Mock settings with an alternate valid voice name (e.g., Fenrir or Aoede)
    test_voice_name = "Fenrir"
    monkeypatch.setattr(settings, "tts_voice_name", test_voice_name)
    monkeypatch.setattr(settings, "gemini_api_key", "mock_api_key_for_test")
    
    captured_config = [None]
    
    class MockLiveCtx:
        async def __aenter__(self):
            return "mock_session_active"
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    class MockLive:
        def connect(self, model, config):
            captured_config[0] = config
            return MockLiveCtx()
            
    class MockAio:
        live = MockLive()

    class MockClient:
        aio = MockAio()

    live_client = GeminiLiveClient()
    live_client.client = MockClient()
    
    success = await live_client.connect()
    assert success is True
    assert captured_config[0] is not None
    
    speech_cfg = captured_config[0].speech_config
    assert speech_cfg is not None
    assert speech_cfg.voice_config.prebuilt_voice_config.voice_name == test_voice_name
