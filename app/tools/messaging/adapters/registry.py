import structlog
from typing import Optional
from app.tools.messaging.adapters.base_adapter import BaseMessagingAdapter
from app.tools.messaging.adapters.whatsapp_adapter import WhatsAppWebAdapter
from app.tools.messaging.adapters.messenger_adapter import MessengerWebAdapter
from app.tools.messaging.adapters.telegram_adapter import TelegramWebAdapter

logger = structlog.get_logger(__name__)

ADAPTER_MAPPING = {
    "whatsapp": WhatsAppWebAdapter,
    "messenger": MessengerWebAdapter,
    "telegram": TelegramWebAdapter,
}

def get_web_adapter(app_name: str, page) -> Optional[BaseMessagingAdapter]:
    """
    Factory function to retrieve an appropriate Web messaging adapter instance
    based on platform name and playwright page.
    """
    clean_name = app_name.strip().lower()
    adapter_cls = ADAPTER_MAPPING.get(clean_name)
    if not adapter_cls:
        logger.error("unsupported_messaging_platform", app=app_name)
        return None
    return adapter_cls(page)
