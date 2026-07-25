import numpy as np
from faster_whisper import WhisperModel
import structlog

logger = structlog.get_logger(__name__)

class WakeWordDetector:
    def __init__(self, model_size="tiny", secret_phrase="myra wake up"): # nosec B107
        self.secret_phrase = secret_phrase.lower().strip()
        # Initialize faster-whisper model
        self.model = WhisperModel(model_size, device="cpu", compute_type="int8")
        logger.info("wake_word_model_loaded", model_size=model_size)

    def process_audio(self, pcm_data: bytes, sample_rate: int = 16000) -> bool:
        # Convert PCM bytes to float32 numpy array
        audio_data = np.frombuffer(pcm_data, dtype=np.int16).astype(np.float32) / 32768.0
        
        try:
            segments, info = self.model.transcribe(audio_data, beam_size=5)
            transcription = " ".join([segment.text for segment in segments]).lower().strip()
            
            if transcription:
                logger.debug("stt_transcription", text=transcription)
            
            # Simple substring match for the secret phrase
            if self.secret_phrase in transcription:
                logger.info("wake_word_detected")
                return True
            return False
        except Exception as e:
            logger.error("transcription_error", error=str(e))
            return False
