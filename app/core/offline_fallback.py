import ollama
import structlog
from app.config import settings

logger = structlog.get_logger(__name__)

class OfflineFallback:
    """Provides offline LLM fallback capabilities when internet is down"""
    def __init__(self):
        self.model = settings.ollama_model
        logger.info(f"OfflineFallback initialized with model: {self.model}")

    def query_offline_model(self, prompt: str) -> str:
        """
        Sends a prompt to the local Ollama instance.
        """
        try:
            logger.info("Routing query to local offline model")
            response = ollama.chat(model=self.model, messages=[
                {'role': 'user', 'content': prompt}
            ])
            return response['message']['content']
        except Exception as e:
            logger.error("Offline model query failed. Is Ollama running?", error=str(e))
            return "Error: Cannot reach local offline model. Ensure Ollama is running."
