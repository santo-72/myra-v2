import structlog
from app.tools.messaging.adapters.base_adapter import BaseMessagingAdapter

logger = structlog.get_logger(__name__)

class WhatsAppWebAdapter(BaseMessagingAdapter):
    def __init__(self, page):
        self.page = page
        self.url = "https://web.whatsapp.com"

    async def open(self) -> bool:
        logger.info("whatsapp_adapter_open")
        if self.page.url == "about:blank" or "web.whatsapp.com" not in self.page.url:
            await self.page.goto(self.url, wait_until="domcontentloaded", timeout=30000)
            
        try:
            qr_element = await self.page.wait_for_selector('canvas[aria-label="Scan me!"], div[data-ref]', timeout=2000)
            if qr_element:
                logger.error("whatsapp_not_logged_in_qr_present")
                return False
        except Exception:
            pass
        return True

    async def find_contact_by_name(self, name: str) -> bool:
        logger.info("whatsapp_find_contact_by_name", name=name)
        try:
            search_input = await self.page.wait_for_selector('div[contenteditable="true"]', timeout=5000)
            if not search_input:
                logger.error("whatsapp_search_bar_not_found")
                return False

            await search_input.click()
            await search_input.fill(name)
            await self.page.keyboard.press("Enter")
            
            try:
                no_results = await self.page.wait_for_selector('span:has-text("No chats, contacts or messages found"), div:has-text("No chats, contacts or messages found")', timeout=1500)
                if no_results:
                    logger.warning("whatsapp_contact_not_found", name=name)
                    return False
            except Exception:
                pass
            return True
        except Exception as e:
            logger.error("whatsapp_find_by_name_error", error=str(e))
            return False

    async def find_contact_by_number(self, number: str) -> bool:
        logger.info("whatsapp_find_contact_by_number", number=number)
        clean_num = number.lstrip("+")
        try:
            target_url = f"https://web.whatsapp.com/send/?phone={clean_num}"
            await self.page.goto(target_url, wait_until="domcontentloaded", timeout=30000)
            
            try:
                invalid = await self.page.wait_for_selector('div:has-text("Phone number shared via url is invalid."), span:has-text("invalid")', timeout=2000)
                if invalid:
                    logger.warning("whatsapp_number_invalid", number=number)
                    return False
            except Exception:
                pass
            return True
        except Exception as e:
            logger.error("whatsapp_find_by_number_error", error=str(e))
            return False

    async def type_message(self, message: str) -> bool:
        try:
            compose_box = await self.page.wait_for_selector('div[aria-label="Type a message"], div[contenteditable="true"]:nth-of-type(1)', timeout=5000)
            if not compose_box:
                return False
            await compose_box.click()
            await compose_box.fill(message)
            return True
        except Exception as e:
            logger.error("whatsapp_type_message_error", error=str(e))
            return False

    async def send(self) -> bool:
        try:
            await self.page.keyboard.press("Enter")
            return True
        except Exception as e:
            logger.error("whatsapp_send_error", error=str(e))
            return False

    async def confirm_sent(self) -> bool:
        try:
            await self.page.wait_for_selector('span[data-icon="msg-check"], span[data-icon="msg-dblcheck"], span[data-icon="msg-time"]', timeout=3000)
            logger.info("whatsapp_delivery_confirmed")
            return True
        except Exception:
            logger.warning("whatsapp_delivery_confirmation_timeout")
            return True

    async def close(self):
        pass
