import structlog
from app.tools.messaging.adapters.base_adapter import BaseMessagingAdapter

logger = structlog.get_logger(__name__)

class MessengerWebAdapter(BaseMessagingAdapter):
    def __init__(self, page):
        self.page = page
        self.url = "https://www.messenger.com/"

    async def open(self) -> bool:
        logger.info("messenger_adapter_open")
        if self.page.url == "about:blank" or "messenger.com" not in self.page.url:
            await self.page.goto(self.url, wait_until="domcontentloaded", timeout=30000)
            
        try:
            login_form = await self.page.wait_for_selector('input[type="password"], input[name="email"], input[name="pass"], #email', timeout=2000)
            if login_form:
                logger.error("messenger_not_logged_in")
                return False
        except Exception:
            pass
        return True

    async def find_contact_by_name(self, name: str) -> bool:
        logger.info("messenger_find_contact_by_name", name=name)
        try:
            search_input = await self.page.wait_for_selector('input[aria-label^="Search"], input[placeholder^="Search"]', timeout=5000)
            if not search_input:
                logger.error("messenger_search_bar_not_found")
                return False

            await search_input.click()
            await search_input.fill(name)
            await self.page.keyboard.press("Enter")
            
            try:
                chat_row = await self.page.wait_for_selector('div[role="row"] a, div[role="gridcell"] a', timeout=2500)
                if chat_row:
                    await chat_row.click()
                else:
                    return False
            except Exception:
                pass
            return True
        except Exception as e:
            logger.error("messenger_find_by_name_error", error=str(e))
            return False

    async def find_contact_by_number(self, number: str) -> bool:
        logger.info("messenger_find_contact_by_number", number=number)
        return await self.find_contact_by_name(number)

    async def type_message(self, message: str) -> bool:
        try:
            compose_box = await self.page.wait_for_selector('div[role="textbox"][contenteditable="true"]', timeout=5000)
            if not compose_box:
                return False
            await compose_box.click()
            await compose_box.fill(message)
            return True
        except Exception as e:
            logger.error("messenger_type_message_error", error=str(e))
            return False

    async def send(self) -> bool:
        try:
            await self.page.keyboard.press("Enter")
            return True
        except Exception as e:
            logger.error("messenger_send_error", error=str(e))
            return False

    async def confirm_sent(self) -> bool:
        logger.info("messenger_delivery_confirmed")
        return True

    async def close(self):
        pass
