import pyautogui
import structlog

logger = structlog.get_logger(__name__)

class GUIAutomation:
    """Provides desktop GUI automation using PyAutoGUI for M.Y.R.A"""
    def __init__(self):
        # Configure fail-safe (moving mouse to corner will abort)
        pyautogui.FAILSAFE = True
        logger.info("GUIAutomation initialized")

    def move_mouse(self, x: int, y: int, duration: float = 0.5):
        try:
            pyautogui.moveTo(x, y, duration)
        except Exception as e:
            logger.error("Failed to move mouse", error=str(e))

    def click(self, x: int = None, y: int = None):
        try:
            if x is not None and y is not None:
                pyautogui.click(x, y)
            else:
                pyautogui.click()
        except Exception as e:
            logger.error("Failed to click", error=str(e))

    def type_text(self, text: str, interval: float = 0.05):
        try:
            pyautogui.write(text, interval)
        except Exception as e:
            logger.error("Failed to type text", error=str(e))
            
    def press_key(self, key: str):
        try:
            pyautogui.press(key)
        except Exception as e:
            logger.error(f"Failed to press key {key}", error=str(e))
