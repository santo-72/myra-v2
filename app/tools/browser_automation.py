from playwright.async_api import async_playwright
import structlog
from typing import Optional

logger = structlog.get_logger(__name__)

class BrowserAutomation:
    """Provides web browser automation using Playwright for M.Y.R.A"""
    def __init__(self, headless: bool = True):
        self.headless = headless
        self.playwright = None
        self.browser = None
        
    async def start(self):
        try:
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(headless=self.headless)
            logger.info("BrowserAutomation started")
        except Exception as e:
            logger.error("Failed to start browser automation", error=str(e))
            
    async def get_page_content(self, url: str) -> Optional[str]:
        if not self.browser:
            logger.error("Browser not started")
            return None
        
        try:
            page = await self.browser.new_page()
            await page.goto(url)
            content = await page.content()
            await page.close()
            return content
        except Exception as e:
            logger.error(f"Failed to get content for {url}", error=str(e))
            return None

    async def take_screenshot(self, url: str, output_path: str) -> bool:
        if not self.browser:
            logger.error("Browser not started")
            return False
            
        try:
            page = await self.browser.new_page()
            await page.goto(url)
            await page.screenshot(path=output_path)
            await page.close()
            return True
        except Exception as e:
            logger.error(f"Failed to take screenshot for {url}", error=str(e))
            return False
            
    async def stop(self):
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        logger.info("BrowserAutomation stopped")
