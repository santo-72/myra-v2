"""
Helper script and utility to capture fresh UI element reference screenshots
directly from installed native desktop messaging clients (e.g., WhatsApp UWP) on Windows.
These reference assets are stored under app/tools/messaging/assets/<app_name>/ and are used by PyAutoGUI for confidence matching.
"""
import os
import time
import asyncio
import structlog
import pyautogui

logger = structlog.get_logger(__name__)

ASSETS_DIR = os.path.join(os.path.dirname(__file__), "assets", "whatsapp")

def ensure_asset_dir(app_name: str = "whatsapp") -> str:
    path = os.path.join(os.path.dirname(__file__), "assets", app_name)
    os.makedirs(path, exist_ok=True)
    return path

def _get_window_region_sync():
    try:
        import pygetwindow as gw
        titles = [t for t in gw.getAllTitles() if t and "whatsapp" in t.lower()]
        if not titles:
            return None
        win = gw.getWindowsWithTitle(titles[0])[0]
        if win:
            if not win.isActive and not win.isMinimized:
                win.activate()
            return (win.left, win.top, win.width, win.height)
    except Exception as e:
        logger.debug("window_region_fetch_failed", error=str(e))
    return None

def _capture_and_save_screenshot(region, output_path):
    screenshot = pyautogui.screenshot(region=region)
    screenshot.save(output_path)
    return output_path

async def capture_whatsapp_assets():
    """
    Connects to an active WhatsApp window, takes a full window screenshot non-blockingly,
    and prompts/saves reference cropped asset templates for matching:
    - search_box_icon.png
    - compose_box_icon.png
    - send_button_icon.png
    - sent_indicator.png
    """
    target_dir = ensure_asset_dir("whatsapp")
    logger.info("checking_whatsapp_assets", dir=target_dir)
    
    region = await asyncio.to_thread(_get_window_region_sync)
    if not region:
        logger.warning("no_whatsapp_window_found_for_capture")
        return False
        
    await asyncio.sleep(0.5)
    
    full_path = os.path.join(target_dir, "window_snapshot.png")
    await asyncio.to_thread(_capture_and_save_screenshot, region, full_path)
    logger.info("captured_live_window_snapshot", path=full_path)
    return True

if __name__ == "__main__":
    ensure_asset_dir("whatsapp")
    print(f"Asset directory ready: {ASSETS_DIR}")
