import structlog
from app.auth.voice_auth import VoiceAuthenticator
from app.core.state_machine import StateMachine, AssistantState
from app.core.gemini_live_client import GeminiLiveClient
import asyncio

logger = structlog.get_logger(__name__)

class BargeInManager:
    def __init__(self, authenticator: VoiceAuthenticator, state_machine: StateMachine, live_client: GeminiLiveClient):
        self.authenticator = authenticator
        self.state_machine = state_machine
        self.live_client = live_client
        self.interruption_threshold = 3 # Number of consecutive verified speech frames required to trigger

        self._consecutive_verified_frames = 0

    async def process_frame(self, pcm_data: bytes, sample_rate: int = 16000):
        # We only care about barge-in when the assistant is actively speaking or thinking
        if self.state_machine.current_state not in [AssistantState.ACTIVE_SPEAKING, AssistantState.ACTIVE_THINKING]:
            self._consecutive_verified_frames = 0
            return

        # Check if the frame belongs to the enrolled owner
        is_owner = self.authenticator.verify(pcm_data, sample_rate)
        
        if is_owner:
            self._consecutive_verified_frames += 1
            if self._consecutive_verified_frames >= self.interruption_threshold:
                await self.trigger_interruption()
                self._consecutive_verified_frames = 0
        else:
            self._consecutive_verified_frames = max(0, self._consecutive_verified_frames - 1)

    async def trigger_interruption(self):
        logger.info("barge_in_triggered", reason="owner_voice_detected")
        
        # 1. Stop outgoing audio if applicable (can be done by sending a client event to Gemini)
        # Gemini Live API natively handles barge-in when client sends new audio or explicit cancel
        if self.live_client.session:
            try:
                # We could send a client-side cancel/interruption message, or just switch state
                # In Gemini Live API, streaming new input inherently acts as a barge-in.
                pass
            except Exception as e:
                logger.error("barge_in_error", error=str(e))
                
        # 2. Transition state back to listening
        self.state_machine.transition_to(AssistantState.ACTIVE_LISTENING)
