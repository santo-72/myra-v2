from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    gemini_api_key: str = ""
    huggingface_token: str = ""
    secret_wake_phrase: str = "myra wake up"
    voice_match_threshold: float = 0.75
    environment: str = "development"
    log_level: str = "INFO"
    workspace_dir: str = "workspace"
    github_token: str = ""
    vault_key: str = "" # Fallback if not set in .env
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_phone_number: str = ""
    ollama_model: str = "llama3"
    duress_password: str = "protocol zero"
    interrupt_acknowledge_verbosity: str = "minimal"
    partial_streaming_enabled: bool = True
    latency_instrumentation: bool = True
    
    # Voice Realism (TTS) & Recognition Accuracy (STT) configurations
    tts_voice_name: str = "Aoede" # Supported Gemini Live voices: Puck, Charon, Kore, Fenrir, Aoede
    tts_speaking_rate: float = 1.0 # Cadence speed tuning
    tts_pitch: float = 0.0         # Pitch tuning for natural conversational warmth
    stt_confidence_threshold: float = 0.70 # Threshold for generating clarifying questions
    stt_hotwords_enabled: bool = True
    default_country_code: str = "+880"
    contact_capture_timeout_seconds: float = 20.0
    contact_capture_max_retries: int = 2
    native_app_launch_wait_seconds: float = 5.0
    pyautogui_match_confidence: float = 0.8
    native_interaction_max_retries: int = 3

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
