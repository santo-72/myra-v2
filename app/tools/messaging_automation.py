import os
import asyncio
import structlog
from typing import Dict, Any, Optional
from playwright.async_api import async_playwright
from app.tools.messaging.native_app_registry import find_native_app_path
from app.tools.messaging.adapters.native_adapter import NativeMessagingAdapter
from app.tools.messaging.adapters.registry import get_web_adapter
from app.tools.messaging.utils import normalize_to_e164
from app.tools.messaging.contact_capture import ContactCaptureStateMachine

logger = structlog.get_logger(__name__)

APP_URLS = {
    "whatsapp": "https://web.whatsapp.com",
    "messenger": "https://www.messenger.com",
    "telegram": "https://web.telegram.org"
}

APP_DISPLAY_NAMES = {
    "whatsapp": "WhatsApp",
    "messenger": "Messenger",
    "telegram": "Telegram"
}

class MessagingAutomation:
    """
    Automates sending messages across messaging platforms using a 6-step flow:
    native desktop app detection with PyAutoGUI fallback to Playwright web browser profile resumption,
    database contact name/phone resolution, conversational STT phone prompt with E.164 normalization,
    and voice-confirmed destructive action gate.
    """
    def __init__(self, headless: bool = False, db: Optional[Any] = None, gate: Optional[Any] = None, state_machine: Optional[Any] = None):
        self.headless = headless
        self.db = db
        self.gate = gate
        self.state_machine = state_machine
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

    async def _init_web_adapter(self, app_clean: str):
        context = await self._get_context(app_clean)
        pages = context.pages
        page = pages[0] if pages else await context.new_page()
        url = APP_URLS[app_clean]
        if page.url == "about:blank" or url not in page.url:
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        adapter = get_web_adapter(app_clean, page)
        return adapter

    async def send_message(
        self,
        app: str,
        recipient_identifier: str,
        message: str,
        stt_callback: Optional[Any] = None,
        tts_callback: Optional[Any] = None,
        require_confirmation: bool = True
    ) -> Dict[str, str]:
        # STEP 1 — PARSE AND VALIDATE COMMAND
        app_clean = app.strip().lower()
        if app_clean not in APP_URLS:
            return {"status": "failed", "detail": f"Unsupported app: {app}. Supported apps are whatsapp, messenger, telegram."}

        display_name = APP_DISPLAY_NAMES.get(app_clean, app_clean.capitalize())
        logger.info("messaging_automation_start", app=app_clean, recipient=recipient_identifier)

        adapter = None
        use_native = False
        path_attempted = "browser"
        native_failure_reason = None
        res = {"status": "failed", "detail": "Messaging automation terminated unexpectedly."}

        try:
            try:
                # STEP 2 — CHECK FOR A NATIVE DESKTOP APP FIRST
                native_path = find_native_app_path(app_clean)
                if native_path:
                    logger.info("attempting_native_adapter", app=app_clean, path=native_path)
                    path_attempted = "native"
                    native_adapter = NativeMessagingAdapter(app_clean, native_path)
                    if await native_adapter.open():
                        adapter = native_adapter
                        use_native = True
                    else:
                        native_failure_reason = "window_ready_timeout_or_open_failed"
                        logger.warning("native_adapter_failed_to_open_falling_back", app=app_clean, reason=native_failure_reason)
                        path_attempted = "native_then_browser"
                        adapter = None
                else:
                    native_failure_reason = "not_found"
                    path_attempted = "browser"
            except Exception as native_ex:
                native_failure_reason = f"launch_exception: {str(native_ex)}"
                logger.error("native_app_attempt_exception_falling_back", app=app_clean, error=str(native_ex), exc_info=True)
                path_attempted = "native_then_browser"
                adapter = None
                use_native = False

            # STEP 3 — FALL BACK TO MODULAR WEB AUTOMATION ADAPTERS
            if not adapter:
                logger.info("using_web_adapter", app=app_clean)
                try:
                    adapter = await self._init_web_adapter(app_clean)
                    if not adapter or not await adapter.open():
                        res = {"status": "failed", "detail": f"app not logged in: {display_name} is not logged in or failed to initialize. Please log in once."}
                        return res
                except Exception as web_init_ex:
                    logger.error("web_adapter_init_failed", app=app_clean, error=str(web_init_ex), exc_info=True)
                    res = {"status": "failed", "detail": f"Web browser automation failed to initialize for {display_name}: {str(web_init_ex)}"}
                    return res

            # STEP 4 — SEARCH BY RECIPIENT NAME IN-APP / DATABASE RESOLUTION
            db_contact = None
            target_id = None
            if self.db:
                db_contact = self.db.resolve_contact(recipient_identifier, app=app_clean)
                if db_contact:
                    target_id = db_contact["identifier"]
                    logger.info("contact_resolved_from_db", name=recipient_identifier, id=target_id)

            found = False
            try:
                if db_contact and target_id:
                    found = await adapter.find_contact_by_name(db_contact["name"])
                    if not found:
                        found = await adapter.find_contact_by_number(target_id)
                else:
                    found = await adapter.find_contact_by_name(recipient_identifier)
                    if not found and (recipient_identifier.startswith("+") or any(char.isdigit() for char in recipient_identifier)):
                        found = await adapter.find_contact_by_number(recipient_identifier)
            except Exception as search_ex:
                logger.warning("contact_search_exception_on_adapter", use_native=use_native, error=str(search_ex))
                found = False

            # If native search failed or raised exception, fall back to web automation before giving up or prompting
            if not found and use_native:
                logger.info("native_search_failed_falling_back_to_web", recipient=recipient_identifier)
                if not native_failure_reason:
                    native_failure_reason = "contact_not_found_on_native"
                path_attempted = "native_then_browser"
                try:
                    await adapter.close()
                except Exception:
                    pass
                adapter = await self._init_web_adapter(app_clean)
                if adapter and await adapter.open():
                    use_native = False
                    if db_contact and target_id:
                        found = await adapter.find_contact_by_name(db_contact["name"]) or await adapter.find_contact_by_number(target_id)
                    else:
                        found = await adapter.find_contact_by_name(recipient_identifier) or (
                            await adapter.find_contact_by_number(recipient_identifier) if (recipient_identifier.startswith("+") or any(char.isdigit() for char in recipient_identifier)) else False
                        )

            # STEP 5 — ASK FOR NUMBER FROM USER VIA VOICE & STORE IN DATABASE IF NOT FOUND
            if not found:
                if stt_callback:
                    capture_sm = ContactCaptureStateMachine(db=self.db, main_state_machine=self.state_machine)
                    capture_res = await capture_sm.execute(
                        recipient_name=recipient_identifier,
                        app_name=app_clean,
                        stt_callback=stt_callback,
                        tts_callback=tts_callback
                    )
                    if capture_res.get("status") == "success" and capture_res.get("number"):
                        norm_phone = capture_res["number"]
                        logger.info("voice_phone_obtained_from_state_machine", number=norm_phone)
                        found = await adapter.find_contact_by_number(norm_phone)
                        if not found and use_native:
                            logger.info("native_number_search_failed_falling_back_to_web", number=norm_phone)
                            if not native_failure_reason:
                                native_failure_reason = "phone_not_found_on_native"
                            path_attempted = "native_then_browser"
                            try:
                                await adapter.close()
                            except Exception:
                                pass
                            adapter = await self._init_web_adapter(app_clean)
                            if adapter and await adapter.open():
                                use_native = False
                                found = await adapter.find_contact_by_number(norm_phone)
                        if not found:
                            res = {"status": "failed", "detail": f"contact not found: Could not find chat for {norm_phone} on {display_name}."}
                            return res
                        target_id = norm_phone
                    else:
                        detail_msg = capture_res.get("detail", f"Contact capture did not succeed for {recipient_identifier}.")
                        res = {"status": capture_res.get("status", "failed"), "detail": f"contact not found: {detail_msg}"}
                        return res
                else:
                    res = {"status": "failed", "detail": f"contact not found: Could not find {recipient_identifier} in {display_name} search."}
                    return res

            # STEP 6 — DESTRUCTIVE GATE VERBAL CONFIRMATION (BEFORE SEND)
            typed = await adapter.type_message(message)
            if not typed:
                res = {"status": "failed", "detail": f"Could not enter message text in {display_name} compose box."}
                return res

            if require_confirmation and self.gate and stt_callback:
                confirm_prompt = f"Send message to {recipient_identifier} on {display_name}?"
                confirmed = await self.gate.request_confirmation(confirm_prompt, stt_source_callback=stt_callback)
                if not confirmed:
                    logger.warning("message_sending_unconfirmed", recipient=recipient_identifier)
                    res = {"status": "failed", "detail": "Message sending was not confirmed by voice."}
                    return res

            sent = await adapter.send()
            if not sent:
                res = {"status": "failed", "detail": f"Failed to transmit message on {display_name}."}
                return res

            await adapter.confirm_sent()

            # Update database last_used_at timestamp
            if self.db:
                self.db.update_contact_last_used(recipient_identifier, app=app_clean)
                if target_id:
                    self.db.update_contact_last_used(target_id, app=app_clean)

            res = {"status": "sent", "detail": f"Successfully sent {display_name} message to {recipient_identifier}."}
            return res

        except Exception as e:
            logger.error("send_message_exception", app=app_clean, error=str(e), exc_info=True)
            res = {"status": "failed", "detail": f"Error during messaging automation: {str(e)}"}
            return res
        finally:
            # DIAGNOSTIC LOG SUMMARY
            logger.info(
                "messaging_automation_diagnostic_summary",
                app=app_clean,
                recipient=recipient_identifier,
                path_attempted=path_attempted,
                native_failure_reason=native_failure_reason,
                final_outcome=res.get("status", "unknown"),
                detail=res.get("detail", "")
            )

    # Legacy helper implementations for backward compatibility
    async def _send_whatsapp(self, page, recipient_identifier: str, message: str) -> Dict[str, str]:
        adapter = get_web_adapter("whatsapp", page)
        if not await adapter.open() or not await adapter.find_contact_by_name(recipient_identifier):
            return {"status": "failed", "detail": f"contact not found: Could not find {recipient_identifier} in WhatsApp."}
        if not await adapter.type_message(message) or not await adapter.send():
            return {"status": "failed", "detail": "WhatsApp automation failed during send."}
        await adapter.confirm_sent()
        return {"status": "sent", "detail": f"Successfully sent WhatsApp message to {recipient_identifier}."}

    async def _send_messenger(self, page, recipient_identifier: str, message: str) -> Dict[str, str]:
        adapter = get_web_adapter("messenger", page)
        if not await adapter.open() or not await adapter.find_contact_by_name(recipient_identifier):
            return {"status": "failed", "detail": f"contact not found: Could not find {recipient_identifier} in Messenger."}
        if not await adapter.type_message(message) or not await adapter.send():
            return {"status": "failed", "detail": "Messenger automation failed during send."}
        await adapter.confirm_sent()
        return {"status": "sent", "detail": f"Successfully sent Messenger message to {recipient_identifier}."}

    async def _send_telegram(self, page, recipient_identifier: str, message: str) -> Dict[str, str]:
        adapter = get_web_adapter("telegram", page)
        if not await adapter.open() or not await adapter.find_contact_by_name(recipient_identifier):
            return {"status": "failed", "detail": f"contact not found: Could not find {recipient_identifier} in Telegram."}
        if not await adapter.type_message(message) or not await adapter.send():
            return {"status": "failed", "detail": "Telegram automation failed during send."}
        await adapter.confirm_sent()
        return {"status": "sent", "detail": f"Successfully sent Telegram message to {recipient_identifier}."}

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
