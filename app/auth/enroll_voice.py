import os
import sounddevice as sd
import scipy.io.wavfile as wav
from pyannote.audio import Model, Inference
from typing import Optional
import numpy as np
import structlog
from app.config import settings

logger = structlog.get_logger(__name__)

def record_audio(duration=5, fs=16000, filename="data/owner_voice.wav"):
    logger.info("recording_start", duration=duration)
    print(f"Recording for {duration} seconds... Please speak naturally.")
    recording = sd.rec(int(duration * fs), samplerate=fs, channels=1, dtype='int16')
    sd.wait()
    
    os.makedirs("data", exist_ok=True)
    wav.write(filename, fs, recording)
    logger.info("recording_saved", filename=filename)
    return filename

def generate_embedding(audio_file: str) -> Optional[np.ndarray]:
    try:
        model = Model.from_pretrained("pyannote/embedding", use_auth_token=settings.huggingface_token)
        inference = Inference(model, window="whole")
        embedding = inference(audio_file)
        return embedding
    except Exception as e:
        logger.error("embedding_generation_failed", error=str(e))
        return None

if __name__ == "__main__":
    if not settings.huggingface_token:
        print("Please set your HuggingFace token in the .env file to download the embedding model.")
        exit(1)
        
    audio_file = record_audio(duration=5)
    print("Generating voice embedding...")
    emb = generate_embedding(audio_file)
    if emb is not None:
        np.save("data/owner_embedding.npy", emb)
        print("Voice profile successfully enrolled and saved to data/owner_embedding.npy")
    else:
        print("Failed to generate voice profile.")
