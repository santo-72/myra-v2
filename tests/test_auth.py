import pytest
import numpy as np
from app.auth.voice_auth import VoiceAuthenticator
import tempfile
import os

def test_authenticator_init_no_file():
    auth = VoiceAuthenticator(owner_embedding_path="non_existent.npy")
    assert auth.owner_embedding is None

def test_authenticator_rejects_without_profile():
    auth = VoiceAuthenticator(owner_embedding_path="non_existent.npy")
    # Provide random audio bytes
    result = auth.verify(b'\x00' * 960)
    assert result is False

def test_authenticator_loads_embedding():
    # Create a mock embedding
    mock_emb = np.random.rand(512)
    with tempfile.NamedTemporaryFile(suffix=".npy", delete=False) as tmp:
        np.save(tmp.name, mock_emb)
        tmp_name = tmp.name
        
    try:
        auth = VoiceAuthenticator(owner_embedding_path=tmp_name)
        assert auth.owner_embedding is not None
        assert auth.owner_embedding.shape == (512,)
    finally:
        os.remove(tmp_name)
