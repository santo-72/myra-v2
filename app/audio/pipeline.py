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
        self.vad = webrtcvad.Vad(1) # Lower aggressiveness to pick up speech easier
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

    def clear_queue(self):
        """Instantly purges buffered audio packets during barge-in interruptions."""
        while not self.audio_queue.empty():
            try:
                self.audio_queue.get_nowait()
            except queue.Empty:
                break
        logger.debug("audio_pipeline_queue_purged")

    def is_speech(self, pcm_data: bytes) -> bool:
        try:
            return self.vad.is_speech(pcm_data, self.sample_rate)
        except Exception as e:
            logger.error("vad_error", error=str(e))
            return False

    def is_owner_speech(self, pcm_data: bytes, authenticator=None) -> bool:
        """
        Leverages PyAnnote speaker diarization/verification to actively filter out
        secondary speakers or ambient room cross-talk from triggering commands.
        """
        if not self.is_speech(pcm_data):
            return False
        if authenticator and hasattr(authenticator, "owner_embedding") and authenticator.owner_embedding is not None:
            try:
                verified = authenticator.verify(pcm_data, sample_rate=self.sample_rate)
                if not verified:
                    logger.warning("secondary_speaker_cross_talk_filtered")
                    return False
            except Exception as e:
                logger.error("speaker_diarization_filter_error", error=str(e))
        return True

    def get_rms_amplitude(self, pcm_data: bytes) -> float:
        try:
            # Convert to float32 between -1.0 and 1.0
            audio_array = np.frombuffer(pcm_data, dtype=np.int16).astype(np.float32) / 32768.0
            rms = np.sqrt(np.mean(np.square(audio_array)))
            return float(rms)
        except Exception:
            return 0.0

    @staticmethod
    def evaluate_stt_confidence_and_clarify(transcription: str, candidate_terms: list, confidence_score: float = 1.0) -> dict:
        """
        Evaluates recognition confidence against known contacts/terms. When confidence is below threshold
        or phonetic/string matching is ambiguous, generates a polite Bengali clarifying question instead of guessing.
        """
        import difflib
        from app.config import settings
        
        threshold = getattr(settings, "stt_confidence_threshold", 0.70)
        words = transcription.strip().split()
        if not words:
            return {"clarify": False, "confidence": confidence_score, "question": None}

        # Check explicit low acoustic confidence score from STT engine
        if confidence_score < threshold:
            # Check if any words vaguely match candidate terms
            matches = []
            for term in candidate_terms:
                sim_ratios = [difflib.SequenceMatcher(None, w.lower(), term.lower()).ratio() for w in words]
                max_sim = max(sim_ratios) if sim_ratios else 0.0
                if 0.35 <= max_sim <= 0.85:
                    matches.append((term, max_sim))
            
            matches.sort(key=lambda x: x[1], reverse=True)
            if len(matches) >= 2:
                q = f"স্যার, অডিও সংকেতের কারণে কথাটি ঠিক স্পষ্ট বুঝতে পারিনি। আপনি কি {matches[0][0]} বললেন, নাকি {matches[1][0]}? দয়া করে আরেকবার বলবেন কি?"
                logger.info("stt_clarification_triggered", reason="low_confidence_ambiguous_matches", matches=[m[0] for m in matches[:2]])
                return {"clarify": True, "confidence": confidence_score, "question": q, "candidates": [m[0] for m in matches[:2]]}
            elif len(matches) == 1:
                q = f"স্যার, কথাটি কিছুটা অস্পষ্ট শোনাল। আপনি কি {matches[0][0]} বলতে চেয়েছেন?"
                logger.info("stt_clarification_triggered", reason="low_confidence_single_match", candidate=matches[0][0])
                return {"clarify": True, "confidence": confidence_score, "question": q, "candidates": [matches[0][0]]}
            else:
                q = "স্যার, কথাটি স্পষ্ট বুঝতে পারিনি। দয়া করে আরেকবার বলবেন কি?"
                return {"clarify": True, "confidence": confidence_score, "question": q, "candidates": []}
                
        return {"clarify": False, "confidence": confidence_score, "question": None}

    @staticmethod
    def detect_and_log_speech_correction(transcription: str, db=None) -> tuple:
        """
        Detects real-time conversational correction patterns in utterances
        (e.g., 'না আমি বলেছি করিম', 'not X I meant Y') and logs correction pairs to LocalDatabase.
        """
        import re
        if not db or not hasattr(db, "log_stt_correction"):
            return None
            
        text = transcription.strip()
        # Pattern 1: Bengali correction pattern "না [misheard] নয়/না, [corrected] বা আমি বলেছি [corrected]"
        # Pattern 2: Simple English correction "not X, I meant Y" or "not X meant Y"
        patterns = [
            r"(?:না|no)[\s,]+([^\s,]+)[\s,]+(?:নয়|না|not)[\s,]+(?:আমি বলেছি|বলছি|হবে|meant|but)[\s,]+([^\s,]+)",
            r"(?:not)[\s,]+([^\s,]+)[\s,]+(?:I meant|meant|it is)[\s,]+([^\s,]+)",
            r"(?:না)[\s,]+([^\s,]+)[\s,]+(?:নয়)[\s,]+([^\s,]+)"
        ]
        
        for pat in patterns:
            match = re.search(pat, text, re.IGNORECASE)
            if match and len(match.groups()) == 2:
                misheard, corrected = match.group(1), match.group(2)
                db.log_stt_correction(misheard, corrected)
                logger.info("detected_conversational_stt_correction", misheard=misheard, corrected=corrected)
                return (misheard, corrected)
                
        return None

