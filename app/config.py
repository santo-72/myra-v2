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

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
