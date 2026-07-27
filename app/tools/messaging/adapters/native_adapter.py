import time
import asyncio
import os
import structlog
from typing import Optional
from app.tools.gui_automation import GUIAutomation
from app.tools.messaging.native_app_registry import launch_native_app
from app.config import settings

logger = structlog.get_logger(__name__)

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
        logger.debug("waiting_for_window_readiness", app=self.app_name, timeout=wait_seconds)
        
        start_time = time.time()
        window_ready = False
        while time.time() - start_time < wait_seconds:
            try:
                import pygetwindow as gw
                target_word = self.app_name.lower()
                titles = [t for t in gw.getAllTitles() if t and target_word in t.lower()]
                if titles:
                    logger.info("native_app_window_detected", app=self.app_name, title=titles[0])
                    try:
                        win = gw.getWindowsWithTitle(titles[0])[0]
                        if win and not win.isActive and not win.isMinimized:
                            win.activate()
                    except Exception as focus_err:
                        logger.debug("window_focus_attempt_info", error=str(focus_err))
                    window_ready = True
                    break
            except Exception as win_err:
                logger.debug("pygetwindow_polling_error", error=str(win_err))
            await asyncio.sleep(0.3)
            
        if not window_ready and os.name == "nt":
            logger.warning("native_app_window_ready_timeout", app=self.app_name, timeout=wait_seconds)
            return False
            
        await asyncio.sleep(0.5) # Buffer after gaining focus before starting interactions
        self.is_open = True
        return True

    async def _copy_and_paste_unicode(self, text: str):
        """
        PyAutoGUI write() fails on Unicode (e.g. Bengali script).
        We simulate clipboard paste via ctypes / standard OS clipboard fallback.
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

        await asyncio.to_thread(set_clipboard, text)
        await asyncio.sleep(0.1)
        # Hotkey paste Ctrl+V
        await asyncio.to_thread(self.gui.press_key, 'ctrl+v' if hasattr(self.gui, "press_key") else 'v') # Fallback handling
        try:
            import pyautogui
            pyautogui.hotkey('ctrl', 'v')
        except Exception:
            pass

    async def find_contact_by_name(self, name: str) -> bool:
        if not self.is_open:
            return False
        logger.info("native_adapter_find_by_name", app=self.app_name, name=name)
        try:
            import pyautogui
            # Common search shortcut in desktop messaging clients (Ctrl+F or Ctrl+K)
            if self.app_name in ["telegram", "messenger"]:
                await asyncio.to_thread(pyautogui.hotkey, 'ctrl', 'k')
            else:
                await asyncio.to_thread(pyautogui.hotkey, 'ctrl', 'f')
                
            await asyncio.sleep(0.5)
            await self._copy_and_paste_unicode(name)
            await asyncio.sleep(1.0)
            
            # Press enter to open the first matched contact
            await asyncio.to_thread(self.gui.press_key, 'enter')
            await asyncio.sleep(0.5)
            return True
        except Exception as e:
            logger.warning("native_find_contact_by_name_failed", error=str(e))
            return False

    async def find_contact_by_number(self, number: str) -> bool:
        if not self.is_open:
            return False
        logger.info("native_adapter_find_by_number", app=self.app_name, number=number)
        try:
            import pyautogui
            if self.app_name in ["telegram", "messenger"]:
                await asyncio.to_thread(pyautogui.hotkey, 'ctrl', 'k')
            else:
                await asyncio.to_thread(pyautogui.hotkey, 'ctrl', 'f')
                
            await asyncio.sleep(0.5)
            await self._copy_and_paste_unicode(number)
            await asyncio.sleep(1.0)
            await asyncio.to_thread(self.gui.press_key, 'enter')
            await asyncio.sleep(0.5)
            return True
        except Exception as e:
            logger.warning("native_find_contact_by_number_failed", error=str(e))
            return False

    async def type_message(self, message: str) -> bool:
        try:
            logger.debug("native_adapter_type_message", app=self.app_name)
            await self._copy_and_paste_unicode(message)
            return True
        except Exception as e:
            logger.error("native_type_message_failed", error=str(e))
            return False

    async def send(self) -> bool:
        try:
            logger.info("native_adapter_send", app=self.app_name)
            await asyncio.to_thread(self.gui.press_key, 'enter')
            return True
        except Exception as e:
            logger.error("native_send_failed", error=str(e))
            return False

    async def confirm_sent(self) -> bool:
        # In simple GUI automation, give brief pause and assume sent if no exception
        await asyncio.sleep(0.5)
        return True

    async def close(self):
        self.is_open = False
        logger.debug("native_adapter_closed", app=self.app_name)
