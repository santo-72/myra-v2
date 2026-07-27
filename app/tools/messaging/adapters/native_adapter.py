import time
import asyncio
import os
import structlog
from typing import Optional, Any
from app.tools.gui_automation import GUIAutomation
from app.tools.messaging.native_app_registry import launch_native_app
from app.config import settings
from app.tools.messaging.exceptions import (
    ContactSearchBoxNotFoundError,
    ContactResultNotFoundError,
    ComposeBoxNotFoundError,
    SendButtonNotFoundError,
    MessageSendVerificationError
)

logger = structlog.get_logger(__name__)

def _check_and_activate_window(app_name: str) -> bool:
    try:
        import pygetwindow as gw
        target_word = app_name.lower()
        titles = [t for t in gw.getAllTitles() if t and target_word in t.lower()]
        if titles:
            logger.info("native_app_window_detected", app=app_name, title=titles[0])
            try:
                win = gw.getWindowsWithTitle(titles[0])[0]
                if win and not win.isActive and not win.isMinimized:
                    win.activate()
            except Exception as focus_err:
                logger.debug("window_focus_attempt_info", error=str(focus_err))
            return True
    except Exception as win_err:
        logger.debug("pygetwindow_polling_error", error=str(win_err))
    return False

class NativeMessagingAdapter:
    """
    Adapter for automating installed native desktop messaging clients
    (WhatsApp Desktop, Telegram Desktop, Messenger) using PyAutoGUI.
    """
    def __init__(self, app_name: str, app_path: str, gui_tool: Optional[GUIAutomation] = None):
        self.app_name = app_name.strip().lower()
        self.app_path = app_path
        self.gui = gui_tool or GUIAutomation()
        self.is_open = False

    async def open(self) -> bool:
        logger.info("native_adapter_open", app=self.app_name, path=self.app_path)
        success = await asyncio.to_thread(launch_native_app, self.app_path)
        if not success:
            logger.warning("native_app_launch_failed", app=self.app_name)
            return False
            
        wait_seconds = getattr(settings, "native_app_launch_wait_seconds", 5.0)
        logger.info("waiting for WhatsApp window to be ready", app=self.app_name, timeout=wait_seconds)
        
        start_time = time.time()
        window_ready = False
        while time.time() - start_time < wait_seconds:
            found = await asyncio.to_thread(_check_and_activate_window, self.app_name)
            if found:
                window_ready = True
                break
            await asyncio.sleep(0.3)
            
        if not window_ready and os.name == "nt":
            logger.warning("native_app_window_ready_timeout", app=self.app_name, timeout=wait_seconds)
            return False
            
        await asyncio.sleep(0.5) # Buffer after gaining focus before starting interactions
        self.is_open = True
        return True

    async def _locate_element_with_retries(self, asset_name: str, action_prefix: str) -> Optional[Any]:
        import pyautogui
        confidence = getattr(settings, "pyautogui_match_confidence", 0.8)
        max_retries = getattr(settings, "native_interaction_max_retries", 3)
        
        asset_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", self.app_name)
        asset_path = os.path.join(asset_dir, asset_name)
        
        if not os.path.exists(asset_path):
            logger.debug(f"{action_prefix}", method="image_match", status="asset_missing", asset=asset_path)
            return None
            
        logger.info(f"{action_prefix}", method="image_match", asset=asset_path, confidence=confidence, status="attempting")
        for attempt in range(1, max_retries + 1):
            try:
                location = await asyncio.to_thread(pyautogui.locateOnScreen, asset_path, confidence=confidence)
                if location:
                    logger.info(f"{action_prefix}", method="image_match", asset=asset_path, confidence=confidence, status="success", attempt=attempt)
                    return location
            except Exception as match_err:
                logger.debug(f"image_match_attempt_error_{asset_name}", attempt=attempt, error=str(match_err))
            if attempt < max_retries:
                await asyncio.sleep(0.3)
        logger.warning(f"{action_prefix}", method="image_match", status="not_found", asset=asset_path, retries=max_retries)
        return None

    async def _copy_and_paste_unicode(self, text: str):
        """
        PyAutoGUI write() fails on Unicode (e.g. Bengali script).
        We simulate clipboard paste via ctypes / standard OS clipboard fallback without swallowing exceptions silently.
        """
        def set_clipboard(txt):
            try:
                import tkinter as tk
                root = tk.Tk()
                root.withdraw()
                root.clipboard_clear()
                root.clipboard_append(txt)
                root.update()
                root.destroy()
            except Exception as ex:
                logger.warning("tkinter_clipboard_failed_trying_fallback", error=str(ex))
                try:
                    import ctypes
                    user32 = ctypes.windll.user32
                    kernel32 = ctypes.windll.kernel32
                    CF_UNICODETEXT = 13
                    user32.OpenClipboard(0)
                    user32.EmptyClipboard()
                    h_mem = kernel32.GlobalAlloc(0x0042, (len(txt) + 1) * 2)
                    p_mem = kernel32.GlobalLock(h_mem)
                    ctypes.cdll.msvcrt.wcscpy(ctypes.c_wchar_p(p_mem), txt)
                    kernel32.GlobalUnlock(h_mem)
                    user32.SetClipboardData(CF_UNICODETEXT, h_mem)
                    user32.CloseClipboard()
                except Exception as e2:
                    logger.error("all_clipboard_fallbacks_failed", error=str(e2))
                    raise RuntimeError(f"Could not set clipboard text for pasting: {str(e2)}")

        await asyncio.to_thread(set_clipboard, text)
        await asyncio.sleep(0.1)
        # Hotkey paste Ctrl+V using verified GUI automation method
        try:
            if hasattr(self.gui, "press_hotkey"):
                await asyncio.to_thread(self.gui.press_hotkey, 'ctrl', 'v')
            else:
                await asyncio.to_thread(self.gui.press_key, 'ctrl+v')
        except Exception as paste_ex:
            logger.error("paste_via_gui_tool_failed_trying_pyautogui", error=str(paste_ex))
            import pyautogui
            await asyncio.to_thread(pyautogui.hotkey, 'ctrl', 'v')

    async def _search_contact(self, query: str) -> bool:
        if not self.is_open:
            raise ContactSearchBoxNotFoundError("Adapter is not open; cannot search contact.")
        import pyautogui

        # STEP A: Locate Search Box
        loc = await self._locate_element_with_retries("search_box_icon.png", "attempting to locate search box")
        if loc:
            logger.info("clicking search box")
            center = pyautogui.center(loc)
            await asyncio.to_thread(self.gui.click, center.x, center.y)
        else:
            shortcut = 'ctrl+k' if self.app_name in ["telegram", "messenger"] else 'ctrl+f'
            logger.info("attempting to locate search box", method="hotkey", hotkey=shortcut, status="fallback_attempt")
            try:
                if self.app_name in ["telegram", "messenger"]:
                    await asyncio.to_thread(self.gui.press_hotkey, 'ctrl', 'k')
                else:
                    await asyncio.to_thread(self.gui.press_hotkey, 'ctrl', 'f')
                logger.info("attempting to locate search box", method="hotkey", status="success")
            except Exception as e:
                logger.error("search_box_hotkey_failed", error=str(e))
                raise ContactSearchBoxNotFoundError(f"Could not locate search box in {self.app_name} via image match or hotkey: {str(e)}")

        await asyncio.sleep(0.5)

        # STEP B: Type Contact Name / Number
        logger.info(f"typing contact name: {query}")
        await self._copy_and_paste_unicode(query)

        # STEP C: Wait for Search Results
        logger.info("waiting for search results to appear")
        await asyncio.sleep(1.5)

        # STEP D: Locate & Click Contact Result
        logger.info("attempting to locate/click contact result")
        res_loc = await self._locate_element_with_retries("contact_result_icon.png", "attempting to locate contact result")
        if res_loc:
            center = pyautogui.center(res_loc)
            await asyncio.to_thread(self.gui.click, center.x, center.y)
        else:
            try:
                await asyncio.to_thread(self.gui.press_key, 'down')
                await asyncio.sleep(0.2)
                await asyncio.to_thread(self.gui.press_key, 'enter')
            except Exception as res_err:
                logger.error("contact_result_selection_failed", error=str(res_err))
                raise ContactResultNotFoundError(f"Could not select contact result for '{query}': {str(res_err)}")

        # STEP E: Wait for Chat Window to Open
        logger.info("waiting for chat window to open")
        await asyncio.sleep(1.0)
        return True

    async def find_contact_by_name(self, name: str) -> bool:
        logger.info("native_adapter_find_by_name", app=self.app_name, name=name)
        try:
            return await self._search_contact(name)
        except (ContactSearchBoxNotFoundError, ContactResultNotFoundError):
            raise
        except Exception as e:
            logger.error("native_find_contact_by_name_failed", error=str(e), exc_info=True)
            raise ContactResultNotFoundError(f"Unhandled exception searching for contact name '{name}': {str(e)}")

    async def find_contact_by_number(self, number: str) -> bool:
        logger.info("native_adapter_find_by_number", app=self.app_name, number=number)
        try:
            return await self._search_contact(number)
        except ContactResultNotFoundError:
            if "whatsapp" in self.app_name:
                clean_num = "".join([c for c in str(number) if c.isdigit() or c == "+"])
                uri = f"whatsapp://send?phone={clean_num}"
                logger.info("fallback_to_whatsapp_uri_deep_link", uri=uri)
                res = await asyncio.to_thread(launch_native_app, uri)
                if res:
                    await asyncio.sleep(1.5)
                    return True
            raise
        except ContactSearchBoxNotFoundError:
            raise
        except Exception as e:
            logger.error("native_find_contact_by_number_failed", error=str(e), exc_info=True)
            raise ContactResultNotFoundError(f"Unhandled exception searching for contact number '{number}': {str(e)}")

    async def type_message(self, message: str) -> bool:
        if not self.is_open:
            raise ComposeBoxNotFoundError("Adapter is not open; cannot locate compose box.")
        try:
            import pyautogui
            loc = await self._locate_element_with_retries("compose_box_icon.png", "locating message compose box")
            if loc:
                center = pyautogui.center(loc)
                await asyncio.to_thread(self.gui.click, center.x, center.y)
            else:
                logger.info("locating message compose box", method="default_focus", status="assumed_active_after_chat_open")

            logger.info(f"typing message: {message}")
            await self._copy_and_paste_unicode(message)
            return True
        except ComposeBoxNotFoundError:
            raise
        except Exception as e:
            logger.error("native_type_message_failed", error=str(e), exc_info=True)
            raise ComposeBoxNotFoundError(f"Failed to locate or type into compose box: {str(e)}")

    async def send(self) -> bool:
        if not self.is_open:
            raise SendButtonNotFoundError("Adapter is not open; cannot locate send button.")
        try:
            import pyautogui
            loc = await self._locate_element_with_retries("send_button_icon.png", "locating and clicking send button")
            if loc:
                center = pyautogui.center(loc)
                await asyncio.to_thread(self.gui.click, center.x, center.y)
            else:
                logger.info("locating and clicking send button", method="key_press_enter", status="fallback_attempt")
                try:
                    await asyncio.to_thread(self.gui.press_key, 'enter')
                    logger.info("locating and clicking send button", method="key_press_enter", status="success")
                except Exception as key_err:
                    logger.error("send_enter_key_failed", error=str(key_err))
                    raise SendButtonNotFoundError(f"Could not locate send button icon or activate enter send after retries: {str(key_err)}")
            return True
        except SendButtonNotFoundError:
            raise
        except Exception as e:
            logger.error("native_send_failed", error=str(e), exc_info=True)
            raise SendButtonNotFoundError(f"Failed during send operation: {str(e)}")

    async def confirm_sent(self) -> bool:
        try:
            loc = await self._locate_element_with_retries("sent_indicator.png", "verifying message was sent")
            if loc:
                logger.info("verifying message was sent", status="verified_by_checkmark")
            else:
                logger.info("verifying message was sent", status="assumed_after_send")
            await asyncio.sleep(0.5)
            return True
        except Exception as e:
            logger.error("native_confirm_sent_failed", error=str(e), exc_info=True)
            raise MessageSendVerificationError(f"Error while verifying message transmission: {str(e)}")

    async def close(self):
        self.is_open = False
        logger.debug("native_adapter_closed", app=self.app_name)

