import numpy as np
import structlog
from typing import Optional
from pyannote.audio import Model, Inference
from scipy.spatial.distance import cosine
from app.config import settings
import scipy.io.wavfile as wav
import os
import tempfile

logger = structlog.get_logger(__name__)

class VoiceAuthenticator:
    def __init__(self, owner_embedding_path="data/owner_embedding.npy"):
        self.owner_embedding = None
        self.model = None
        self.inference = None
        
        if os.path.exists(owner_embedding_path):
            self.owner_embedding = np.load(owner_embedding_path)
            logger.info("owner_embedding_loaded")
        else:
            logger.warning("owner_embedding_not_found")
            
    def _init_model(self):
        if not self.model and settings.huggingface_token:
            try:
                self.model = Model.from_pretrained("pyannote/embedding", use_auth_token=settings.huggingface_token)
                self.inference = Inference(self.model, window="whole")
            except Exception as e:
                logger.error("model_init_failed", error=str(e))

    def verify(self, pcm_data: bytes, sample_rate: int = 16000) -> bool:
        if self.owner_embedding is None:
            logger.warning("no_owner_profile_enrolled")
            return False
            
        self._init_model()
        if not self.inference:
            return False
            
        # Write temporary wav file for pyannote (it expects file paths or specific structures)
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_name = tmp.name
            audio_array = np.frombuffer(pcm_data, dtype=np.int16)
            wav.write(tmp_name, sample_rate, audio_array)
            
        try:
            current_embedding = self.inference(tmp_name)
            
            # Ensure dimensions match
            if current_embedding.ndim > 1:
                current_embedding = current_embedding.flatten()
            owner_emb_flat = self.owner_embedding.flatten()
            
            similarity = 1 - cosine(owner_emb_flat, current_embedding)
            logger.info("voice_similarity_score", score=similarity)
            
            return similarity >= settings.voice_match_threshold
        except Exception as e:
            logger.error("verification_error", error=str(e))
            return False
        finally:
            if os.path.exists(tmp_name):
                os.remove(tmp_name)
