import os
import structlog
from typing import Dict, Any, Optional
from playwright.async_api import async_playwright

logger = structlog.get_logger(__name__)

APP_URLS = {
    "whatsapp": "https://web.whatsapp.com",
    "messenger": "https://www.messenger.com",
    "telegram": "https://web.telegram.org"
}

class MessagingAutomation:
    """Automates sending messages across web platforms using Playwright persistent contexts."""
    def __init__(self, headless: bool = False):
        self.headless = headless
        self.contexts = {}
        self.playwright = None

    async def _get_context(self, app_name: str):
        if not self.playwright:
            self.playwright = await async_playwright().start()
        
        user_data_dir = os.path.abspath(os.path.join("workspace", "browser_profile", app_name.lower()))
        os.makedirs(user_data_dir, exist_ok=True)
        
        if app_name not in self.contexts or self.contexts[app_name] is None:
            context = await self.playwright.chromium.launch_persistent_context(
                user_data_dir=user_data_dir,
                headless=self.headless,
                viewport={"width": 1280, "height": 720},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            self.contexts[app_name] = context
        return self.contexts[app_name]

    async def send_message(self, app: str, recipient_identifier: str, message: str) -> Dict[str, str]:
        app_clean = app.strip().lower()
        if app_clean not in APP_URLS:
            return {"status": "failed", "detail": f"Unsupported app: {app}. Supported apps are whatsapp, messenger, telegram."}
            
        url = APP_URLS[app_clean]
        logger.info("messaging_automation_start", app=app_clean, recipient=recipient_identifier)
        
        try:
            context = await self._get_context(app_clean)
            pages = context.pages
            page = pages[0] if pages else await context.new_page()
            if page.url == "about:blank" or url not in page.url:
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                
            # Delegate to app-specific handling
            if app_clean == "whatsapp":
                return await self._send_whatsapp(page, recipient_identifier, message)
            elif app_clean == "messenger":
                return await self._send_messenger(page, recipient_identifier, message)
            elif app_clean == "telegram":
                return await self._send_telegram(page, recipient_identifier, message)
            else:
                return {"status": "failed", "detail": "Unknown application target."}
        except Exception as e:
            logger.error("send_message_exception", app=app_clean, error=str(e))
            return {"status": "failed", "detail": f"Error during messaging automation: {str(e)}"}

    async def _send_whatsapp(self, page, recipient_identifier: str, message: str) -> Dict[str, str]:
        try:
            # Check login status (QR code presence means not logged in)
            try:
                qr_element = await page.wait_for_selector('canvas[aria-label="Scan me!"], div[data-ref]', timeout=2000)
                if qr_element:
                    return {"status": "failed", "detail": "app not logged in: WhatsApp is showing QR code. Please scan to log in once."}
            except Exception:
                pass # No QR code detected, assume logged in

            # Wait for search input box
            try:
                search_input = await page.wait_for_selector('div[contenteditable="true"]', timeout=5000)
            except Exception:
                search_input = None

            if not search_input:
                return {"status": "failed", "detail": "app not logged in: WhatsApp search bar not found."}

            # Type recipient identifier in search bar
            await search_input.click()
            await search_input.fill(recipient_identifier)
            await page.keyboard.press("Enter")
            
            # Check if contact was opened or not found
            try:
                no_results = await page.wait_for_selector('span:has-text("No chats, contacts or messages found"), div:has-text("No chats, contacts or messages found")', timeout=1500)
                if no_results:
                    return {"status": "failed", "detail": f"contact not found: Could not find {recipient_identifier} in WhatsApp."}
            except Exception:
                pass # Chat likely opened!

            # Locate compose box
            try:
                compose_box = await page.wait_for_selector('div[aria-label="Type a message"], div[contenteditable="true"]:nth-of-type(1)', timeout=3000)
            except Exception:
                compose_box = None

            if not compose_box:
                return {"status": "failed", "detail": "Could not find WhatsApp compose box."}
                
            await compose_box.click()
            await compose_box.fill(message)
            await page.keyboard.press("Enter")
            
            # Wait for delivery indicator
            try:
                await page.wait_for_selector('span[data-icon="msg-check"], span[data-icon="msg-dblcheck"], span[data-icon="msg-time"]', timeout=2000)
            except Exception:
                logger.warning("whatsapp_delivery_indicator_timeout")
                
            logger.info("whatsapp_message_sent", recipient=recipient_identifier)
            return {"status": "sent", "detail": f"Successfully sent WhatsApp message to {recipient_identifier}."}
        except Exception as e:
            logger.error("whatsapp_automation_error", error=str(e))
            return {"status": "failed", "detail": f"WhatsApp automation failed: {str(e)}"}

    async def _send_messenger(self, page, recipient_identifier: str, message: str) -> Dict[str, str]:
        try:
            # Check login status
            if "login" in page.url or await page.query_selector('input[name="email"]'):
                return {"status": "failed", "detail": "app not logged in: Messenger login page detected. Please log in once."}

            try:
                search_box = await page.wait_for_selector('input[type="search"], input[placeholder*="Search"]', timeout=5000)
            except Exception:
                search_box = None

            if not search_box:
                return {"status": "failed", "detail": "app not logged in: Messenger search bar not found."}

            await search_box.click()
            await search_box.fill(recipient_identifier)
            await page.keyboard.press("Enter")

            try:
                no_res = await page.wait_for_selector('span:has-text("No messages found"), span:has-text("No results")', timeout=1500)
                if no_res:
                    return {"status": "failed", "detail": f"contact not found: Could not locate {recipient_identifier} on Messenger."}
            except Exception:
                pass

            try:
                compose = await page.wait_for_selector('div[role="textbox"]', timeout=3000)
            except Exception:
                compose = None

            if not compose:
                return {"status": "failed", "detail": "Could not find Messenger text input."}

            await compose.click()
            await compose.fill(message)
            await page.keyboard.press("Enter")

            logger.info("messenger_message_sent", recipient=recipient_identifier)
            return {"status": "sent", "detail": f"Successfully sent Messenger message to {recipient_identifier}."}
        except Exception as e:
            logger.error("messenger_automation_error", error=str(e))
            return {"status": "failed", "detail": f"Messenger automation failed: {str(e)}"}

    async def _send_telegram(self, page, recipient_identifier: str, message: str) -> Dict[str, str]:
        try:
            # Check login status
            if await page.query_selector('button:has-text("Log in by QR Code"), input[name="phone_number"]'):
                return {"status": "failed", "detail": "app not logged in: Telegram login required."}

            try:
                search_input = await page.wait_for_selector('input[placeholder*="Search"], input[id="telegram-search-input"]', timeout=5000)
            except Exception:
                search_input = None

            if not search_input:
                return {"status": "failed", "detail": "app not logged in: Telegram search box not found."}

            await search_input.click()
            await search_input.fill(recipient_identifier)
            await page.keyboard.press("Enter")

            try:
                no_res = await page.wait_for_selector('div:has-text("No results"), span:has-text("Nothing found")', timeout=1500)
                if no_res:
                    return {"status": "failed", "detail": f"contact not found: Could not find {recipient_identifier} on Telegram."}
            except Exception:
                pass

            try:
                compose = await page.wait_for_selector('div[contenteditable="true"][id="editable-message-text"], div[role="textbox"]', timeout=3000)
            except Exception:
                compose = None

            if not compose:
                return {"status": "failed", "detail": "Could not find Telegram compose box."}

            await compose.click()
            await compose.fill(message)
            await page.keyboard.press("Enter")

            logger.info("telegram_message_sent", recipient=recipient_identifier)
            return {"status": "sent", "detail": f"Successfully sent Telegram message to {recipient_identifier}."}
        except Exception as e:
            logger.error("telegram_automation_error", error=str(e))
            return {"status": "failed", "detail": f"Telegram automation failed: {str(e)}"}

    async def close_all(self):
        for app_name, context in self.contexts.items():
            if context:
                try:
                    await context.close()
                except Exception:
                    pass
        self.contexts.clear()
        if self.playwright:
            try:
                await self.playwright.stop()
            except Exception:
                pass
            self.playwright = None
