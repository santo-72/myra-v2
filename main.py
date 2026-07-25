import sys
import asyncio
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer
from app.ui.app_window import AssistantWindow
from app.core.state_machine import StateMachine, AssistantState
import structlog

logger = structlog.get_logger(__name__)

async def main_async(window: AssistantWindow, state_machine: StateMachine):
    """Main async loop to handle core AI tasks alongside the Qt event loop."""
    try:
        from app.core.gemini_live_client import GeminiLiveClient
        from app.audio.pipeline import AudioPipeline
        from google.genai import types
        import queue
        
        client = GeminiLiveClient()
        pipeline = AudioPipeline()
        
        connected = await client.connect()
        if connected:
            import pyaudio
            p = pyaudio.PyAudio()
            out_stream = p.open(format=pyaudio.paInt16, channels=1, rate=24000, output=True)
            
            window.append_transcript("System: Gemini Live Connected.", is_user=False)
            pipeline.start_listening()
            
            # Trigger an initial greeting to test audio playback
            asyncio.create_task(
                client.session.send_client_content(
                    turns=[
                        types.Content(
                            role="user",
                            parts=[types.Part.from_text(text="Say exactly: 'হ্যালো, আমি মায়রা! আমি তৈরি।' in Bengali. Do not say anything else. No English.")]
                        )
                    ],
                    turn_complete=True
                )
            )
            
            async def audio_sender():
                while True:
                    try:
                        chunk = await asyncio.to_thread(pipeline.get_audio_chunk, 0.1)
                        if pipeline.is_speech(chunk):
                            state_machine.transition_to(AssistantState.ACTIVE_LISTENING)
                            window.update_audio_amplitude(pipeline.get_rms_amplitude(chunk) * 10)
                        
                        # Gemini Live requires a continuous audio stream to detect turn-taking naturally
                        await client.send_audio(chunk)
                    except queue.Empty:
                        await asyncio.sleep(0.01)
                    except Exception:
                        await asyncio.sleep(0.01)

            async def audio_receiver():
                async for msg in client.receive_stream():
                    if msg.server_content and msg.server_content.model_turn:
                        for part in msg.server_content.model_turn.parts:
                            if part.text:
                                window.append_transcript(part.text, is_user=False)
                                state_machine.transition_to(AssistantState.ACTIVE_SPEAKING)
                            if part.inline_data:
                                state_machine.transition_to(AssistantState.ACTIVE_SPEAKING)
                                window.update_audio_amplitude(0.5)
                                try:
                                    await asyncio.to_thread(out_stream.write, part.inline_data.data)
                                except Exception as e:
                                    logger.error(f"PyAudio write error: {e}")

            asyncio.create_task(audio_sender())
            asyncio.create_task(audio_receiver())
        else:
            window.append_transcript("System: Offline Mode. No API Key found.", is_user=False)
            async def mock_loop():
                while True:
                    if state_machine.current_state == AssistantState.ACTIVE_LISTENING:
                        await asyncio.sleep(1)
                        window.append_transcript("Hello, Titan! I am listening.", is_user=False)
                        state_machine.transition_to(AssistantState.ACTIVE_SPEAKING)
                        await asyncio.sleep(2)
                        state_machine.transition_to(AssistantState.DORMANT)
                    await asyncio.sleep(0.5)
            asyncio.create_task(mock_loop())

        while True:
            await asyncio.sleep(1)
            
    except asyncio.CancelledError:
        if 'pipeline' in locals():
            pipeline.stop_listening()
        if 'client' in locals():
            await client.disconnect()
        if 'out_stream' in locals():
            out_stream.stop_stream()
            out_stream.close()
            p.terminate()

def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    
    state_machine = StateMachine()
    window = AssistantWindow(state_machine=state_machine)
    window.show()

    # Asyncio integration using QTimer (lightweight approach)
    # A full robust implementation could use qasync library, but this works for basic integration
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    main_task = loop.create_task(main_async(window, state_machine))
    
    def process_asyncio_events():
        loop.stop()
        loop.run_forever()
        
    timer = QTimer()
    timer.timeout.connect(process_asyncio_events)
    timer.start(10) # 10ms intervals

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
