import asyncio
import re
from datetime import datetime
from enum import Enum, auto
import structlog
from typing import Optional, Callable, Awaitable, Dict, Any

from app.config import settings
from app.core.state_machine import StateMachine, AssistantState
from app.core.interrupt_controller import interrupt_controller
from app.tools.messaging.utils import normalize_to_e164, convert_bengali_numerals

logger = structlog.get_logger(__name__)

class ContactCaptureState(Enum):
    INIT = auto()
    AWAITING_NUMBER = auto()
    VALIDATING_NUMBER = auto()
    CONFIRMING_NUMBER = auto()
    SAVING = auto()
    DONE = auto()
    TIMEOUT = auto()
    INVALID_INPUT = auto()
    CANCELLED = auto()
    FAILED = auto()

class ContactCaptureStateMachine:
    """
    Explicit asynchronous state machine for capturing recipient telephone numbers via voice interaction.
    Features strict timeouts, input validation, readback confirmation, bounded retry budget,
    resilient DB persistence, and instantaneous cooperative barge-in cancellation.
    """
    def __init__(self, db: Optional[Any] = None, main_state_machine: Optional[StateMachine] = None):
        self._state: ContactCaptureState = ContactCaptureState.INIT
        self.db = db
        self.main_state_machine = main_state_machine
        self.attempts: int = 0

    @property
    def current_state(self) -> ContactCaptureState:
        return self._state

    def _transition_to(self, new_state: ContactCaptureState, recipient: str = ""):
        old_state = self._state
        if old_state == new_state:
            return
        self._state = new_state
        logger.info(
            "contact_capture_transition",
            old_state=old_state.name,
            new_state=new_state.name,
            timestamp=datetime.now().isoformat(),
            recipient=recipient
        )

    def _set_main_state(self, state: AssistantState):
        if self.main_state_machine:
            try:
                self.main_state_machine.transition_to(state)
            except Exception as e:
                logger.error("error_setting_main_state", error=str(e))

    def _check_interruption(self):
        if interrupt_controller.is_interrupt_requested():
            raise asyncio.CancelledError("User vocal barge-in or interruption requested.")

    async def _speak_and_listen(
        self,
        prompt: str,
        stt_callback: Optional[Callable[[], Awaitable[str]]],
        tts_callback: Optional[Callable[[str], Awaitable[None]]],
        timeout: float
    ) -> Optional[str]:
        self._check_interruption()
        self._set_main_state(AssistantState.ACTIVE_SPEAKING)
        if tts_callback:
            await tts_callback(prompt)
        self._check_interruption()
        
        if not stt_callback:
            logger.warning("contact_capture_no_stt_callback_attached")
            return None
            
        self._set_main_state(AssistantState.ACTIVE_LISTENING)
        try:
            response = await asyncio.wait_for(stt_callback(), timeout=timeout)
            self._check_interruption()
            return response
        except asyncio.TimeoutError:
            raise

    def _is_cancellation(self, text: str) -> bool:
        if not text:
            return False
        clean = text.strip().lower()
        cancel_words = ["বাদ দাও", "থাক", "cancel", "stop", "থামো", "না থাক", "abort", "বাদ", "দরকার নেই"]
        for cw in cancel_words:
            if cw in clean:
                return True
        return False

    def _is_rejection(self, text: str) -> bool:
        if not text:
            return False
        clean = text.strip().lower()
        reject_words = ["না", "no", "ভুল", "wrong", "ঠিক না", "ঠিক নেই", "incorrect"]
        for rw in reject_words:
            if rw in clean:
                return True
        return False

    def _is_affirmation(self, text: str) -> bool:
        if not text:
            return False
        clean = text.strip().lower()
        yes_words = ["হ্যাঁ", "yes", "হাঁ", "ঠিক আছে", "ঠিক", "ok", "correct", "right", "sure", "proceed", "হয়"]
        for yw in yes_words:
            if yw in clean:
                return True
        return False

    def _extract_digits_count(self, text: str) -> int:
        converted = convert_bengali_numerals(text)
        digits = re.sub(r'\D', '', converted)
        return len(digits)

    async def execute(
        self,
        recipient_name: str,
        app_name: str,
        stt_callback: Optional[Callable[[], Awaitable[str]]] = None,
        tts_callback: Optional[Callable[[str], Awaitable[None]]] = None
    ) -> Dict[str, Any]:
        timeout = getattr(settings, "contact_capture_timeout_seconds", 20.0)
        max_retries = getattr(settings, "contact_capture_max_retries", 2)
        self.attempts = 0
        self._transition_to(ContactCaptureState.INIT, recipient=recipient_name)
        
        try:
            self._check_interruption()
            # Step 2: AWAITING_NUMBER
            prompt_msg = f"আমি {recipient_name} নামে কাউকে খুঁজে পাইনি, ওর নাম্বারটা বলবেন?"
            self._transition_to(ContactCaptureState.AWAITING_NUMBER, recipient=recipient_name)
            
            while True:
                self._check_interruption()
                try:
                    user_reply = await self._speak_and_listen(prompt_msg, stt_callback, tts_callback, timeout=timeout)
                except asyncio.TimeoutError:
                    self._transition_to(ContactCaptureState.TIMEOUT, recipient=recipient_name)
                    if tts_callback:
                        await tts_callback("ঠিক আছে, এখন বাদ থাক। পরে আবার চেষ্টা করবেন।")
                    self._set_main_state(AssistantState.ACTIVE_LISTENING)
                    logger.warning("contact_capture_timed_out", recipient=recipient_name)
                    return {"status": "timeout", "number": None, "detail": "Timed out waiting for phone number."}
                    
                if not user_reply:
                    self._transition_to(ContactCaptureState.TIMEOUT, recipient=recipient_name)
                    if tts_callback:
                        await tts_callback("ঠিক আছে, এখন বাদ থাক। পরে আবার চেষ্টা করবেন।")
                    self._set_main_state(AssistantState.ACTIVE_LISTENING)
                    return {"status": "timeout", "number": None, "detail": "No response received from user."}

                # Step 3: VALIDATING_NUMBER
                self._transition_to(ContactCaptureState.VALIDATING_NUMBER, recipient=recipient_name)
                if self._is_cancellation(user_reply):
                    self._transition_to(ContactCaptureState.CANCELLED, recipient=recipient_name)
                    self._set_main_state(AssistantState.ACTIVE_LISTENING)
                    logger.info("contact_capture_cancelled_by_user", recipient=recipient_name)
                    return {"status": "cancelled", "number": None, "detail": "Contact capture cancelled by user."}

                digit_count = self._extract_digits_count(user_reply)
                if digit_count < 5:
                    self._transition_to(ContactCaptureState.INVALID_INPUT, recipient=recipient_name)
                    if self.attempts < max_retries:
                        self.attempts += 1
                        prompt_msg = "নাম্বারটা ঠিক বুঝতে পারলাম না, আবার বলবেন?"
                        self._transition_to(ContactCaptureState.AWAITING_NUMBER, recipient=recipient_name)
                        continue
                    else:
                        self._transition_to(ContactCaptureState.CANCELLED, recipient=recipient_name)
                        if tts_callback:
                            await tts_callback("ঠিক আছে, এখন বাদ থাক। পরে আবার চেষ্টা করবেন।")
                        self._set_main_state(AssistantState.ACTIVE_LISTENING)
                        logger.warning("contact_capture_max_retries_exceeded", recipient=recipient_name)
                        return {"status": "cancelled", "number": None, "detail": "Max retry limit reached after invalid inputs."}

                default_cc = getattr(settings, "default_country_code", "+880")
                normalized_num = normalize_to_e164(user_reply, default_country_code=default_cc)

                # Step 4: CONFIRMING_NUMBER
                self._transition_to(ContactCaptureState.CONFIRMING_NUMBER, recipient=recipient_name)
                confirm_prompt = f"নাম্বারটা কি {normalized_num}? ঠিক থাকলে হ্যাঁ বলুন।"
                try:
                    confirm_reply = await self._speak_and_listen(confirm_prompt, stt_callback, tts_callback, timeout=timeout)
                except asyncio.TimeoutError:
                    self._transition_to(ContactCaptureState.TIMEOUT, recipient=recipient_name)
                    if tts_callback:
                        await tts_callback("ঠিক আছে, এখন বাদ থাক। পরে আবার চেষ্টা করবেন।")
                    self._set_main_state(AssistantState.ACTIVE_LISTENING)
                    logger.warning("contact_capture_confirmation_timed_out", recipient=recipient_name)
                    return {"status": "timeout", "number": None, "detail": "Timed out waiting for confirmation."}

                if confirm_reply and self._is_cancellation(confirm_reply):
                    self._transition_to(ContactCaptureState.CANCELLED, recipient=recipient_name)
                    self._set_main_state(AssistantState.ACTIVE_LISTENING)
                    logger.info("contact_capture_cancelled_at_confirmation", recipient=recipient_name)
                    return {"status": "cancelled", "number": None, "detail": "Contact capture cancelled by user at confirmation step."}

                if confirm_reply and (self._is_rejection(confirm_reply) and not self._is_affirmation(confirm_reply)):
                    if self.attempts < max_retries:
                        self.attempts += 1
                        prompt_msg = "তাহলে সঠিক নাম্বারটা আবার বলবেন?"
                        self._transition_to(ContactCaptureState.AWAITING_NUMBER, recipient=recipient_name)
                        continue
                    else:
                        self._transition_to(ContactCaptureState.CANCELLED, recipient=recipient_name)
                        if tts_callback:
                            await tts_callback("ঠিক আছে, এখন বাদ থাক। পরে আবার চেষ্টা করবেন।")
                        self._set_main_state(AssistantState.ACTIVE_LISTENING)
                        logger.warning("contact_capture_confirmation_retries_exceeded", recipient=recipient_name)
                        return {"status": "cancelled", "number": None, "detail": "Max retry limit reached at confirmation step."}

                # Step 5: SAVING
                self._transition_to(ContactCaptureState.SAVING, recipient=recipient_name)
                if self.db:
                    try:
                        if hasattr(self.db, "upsert_contact_by_phone"):
                            self.db.upsert_contact_by_phone(recipient_name, normalized_num, app=app_name, source="chat_auto_saved", update_last_used=True)
                        else:
                            self.db.add_contact(recipient_name, app_name, normalized_num)
                    except Exception as ex:
                        self._transition_to(ContactCaptureState.FAILED, recipient=recipient_name)
                        if tts_callback:
                            await tts_callback("সেভ করতে সমস্যা হয়েছে")
                        logger.error("contact_capture_db_save_failed", recipient=recipient_name, number=normalized_num, error=str(ex), exc_info=True)
                        self._set_main_state(AssistantState.ACTIVE_LISTENING)
                        # Do not let DB write failure block sending the message itself
                        return {"status": "success", "number": normalized_num, "detail": "Contact captured successfully despite DB save failure."}

                self._transition_to(ContactCaptureState.DONE, recipient=recipient_name)
                self._set_main_state(AssistantState.ACTIVE_LISTENING)
                logger.info("contact_capture_success", recipient=recipient_name, number=normalized_num)
                return {"status": "success", "number": normalized_num, "detail": f"Captured phone number {normalized_num} for {recipient_name}."}

        except asyncio.CancelledError:
            self._transition_to(ContactCaptureState.CANCELLED, recipient=recipient_name)
            self._set_main_state(AssistantState.ACTIVE_LISTENING)
            logger.warning("contact_capture_barge_in_cancelled", recipient=recipient_name)
            return {"status": "cancelled", "number": None, "detail": "Contact capture aborted cleanly due to user barge-in."}
        except Exception as e:
            self._transition_to(ContactCaptureState.FAILED, recipient=recipient_name)
            self._set_main_state(AssistantState.ACTIVE_LISTENING)
            logger.error("contact_capture_unexpected_error", error=str(e), exc_info=True)
            if tts_callback:
                try:
                    await tts_callback("দুঃখিত, একটা সমস্যা হয়েছে, আবার চেষ্টা করুন")
                except Exception:
                    pass
            return {"status": "failed", "number": None, "detail": f"Contact capture failed: {str(e)}"}
