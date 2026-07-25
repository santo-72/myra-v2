import pytest
import numpy as np
from app.audio.pipeline import AudioPipeline
from app.audio.wake_word import WakeWordDetector

def test_audio_pipeline_init():
    pipeline = AudioPipeline(sample_rate=16000, frame_duration_ms=30)
    assert pipeline.sample_rate == 16000
    assert pipeline.frame_size == 480

def test_vad_is_speech_false_on_silence():
    pipeline = AudioPipeline()
    # 30ms of silence at 16000Hz (480 samples * 2 bytes/sample)
    silence = b'\x00' * 960 
    is_speech = pipeline.is_speech(silence)
    assert is_speech is False

def test_wake_word_init():
    # Only test initialization to avoid downloading large models during simple CI test
    detector = WakeWordDetector(model_size="tiny", secret_phrase="test phrase")
    assert detector.secret_phrase == "test phrase"
