import sounddevice as sd
import webrtcvad
import queue
import numpy as np
import structlog

logger = structlog.get_logger(__name__)

class AudioPipeline:
    def __init__(self, sample_rate=16000, frame_duration_ms=30):
        self.sample_rate = sample_rate
        self.frame_duration_ms = frame_duration_ms
        self.frame_size = int(sample_rate * (frame_duration_ms / 1000.0))
        self.vad = webrtcvad.Vad(3) # Aggressiveness mode 3
        self.audio_queue = queue.Queue()
        self.stream = None

    def _audio_callback(self, indata, frames, time, status):
        if status:
            logger.warning("audio_stream_status", status=status)
        self.audio_queue.put(bytes(indata))

    def start_listening(self):
        self.stream = sd.RawInputStream(
            samplerate=self.sample_rate,
            blocksize=self.frame_size,
            dtype='int16',
            channels=1,
            callback=self._audio_callback
        )
        self.stream.start()
        logger.info("audio_pipeline_started")

    def stop_listening(self):
        if self.stream:
            self.stream.stop()
            self.stream.close()
        logger.info("audio_pipeline_stopped")

    def get_audio_chunk(self, timeout=None) -> bytes:
        return self.audio_queue.get(timeout=timeout)

    def is_speech(self, pcm_data: bytes) -> bool:
        try:
            return self.vad.is_speech(pcm_data, self.sample_rate)
        except Exception as e:
            logger.error("vad_error", error=str(e))
            return False

    def get_rms_amplitude(self, pcm_data: bytes) -> float:
        try:
            # Convert to float32 between -1.0 and 1.0
            audio_array = np.frombuffer(pcm_data, dtype=np.int16).astype(np.float32) / 32768.0
            rms = np.sqrt(np.mean(np.square(audio_array)))
            return float(rms)
        except Exception:
            return 0.0
