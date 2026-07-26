import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding='utf-8')
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
        from app.memory.database import LocalDatabase
        from app.memory.manager import MemoryManager
        from google.genai import types
        import queue
        import uuid
        from datetime import datetime
        
        # Initialize local database and import all conversational memories
        session_id = f"sess_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        db = LocalDatabase()
        chroma_manager = MemoryManager()
        db.log_conversation(session_id, "system", "event", f"Session initialized: {session_id}")
        
        # Automatically import system config and base knowledge into local DB
        if not db.get_memory("system_prompt_imported"):
            try:
                with open("config/system_prompt.md", "r", encoding="utf-8") as f:
                    db.import_data("config", "system_prompt.md", f.read())
                    db.save_memory("system_prompt_imported", "true")
            except Exception:
                pass
        
        client = GeminiLiveClient()
        client.set_database(db, chroma_manager, session_id)
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
            
            import time
            ai_speaking_until = [0.0]  # Timestamp until which AI is speaking + room echo cooldown
            last_speech_time = [0.0]   # Last timestamp user voice speech was detected
            user_speech_logged = [False] # Avoid dual logging per single speech burst

            async def audio_sender():
                audio_buffer = bytearray()
                while True:
                    try:
                        chunk = await asyncio.to_thread(pipeline.get_audio_chunk, 0.1)
                        current_time = time.time()
                        
                        # 0. MICROPHONE MUTE CHECK
                        if getattr(window, 'is_muted', False):
                            audio_buffer.clear()
                            if state_machine.current_state in [AssistantState.ACTIVE_LISTENING, AssistantState.ACTIVE_SPEAKING]:
                                state_machine.transition_to(AssistantState.DORMANT)
                                window.update_audio_amplitude(0.0)
                            await asyncio.sleep(0.1)
                            continue
                        
                        # 1. ECHO PREVENTION (Mute mic while AI is speaking + 0.5s cooldown)
                        if current_time < ai_speaking_until[0]:
                            audio_buffer.clear()
                            continue
                        
                        # When speaking finishes, return to DORMANT
                        if state_machine.current_state == AssistantState.ACTIVE_SPEAKING:
                            state_machine.transition_to(AssistantState.DORMANT)
                            window.update_audio_amplitude(0.0)
                        
                        # 2. VOICE ACTIVITY DETECTION (VAD)
                        is_user_talking = pipeline.is_speech(chunk)
                        if is_user_talking:
                            last_speech_time[0] = current_time
                            if not user_speech_logged[0]:
                                db.log_conversation(session_id, "user", "audio", "[User Spoke: Voice input streamed to Myra AI]")
                                user_speech_logged[0] = True
                            state_machine.transition_to(AssistantState.ACTIVE_LISTENING)
                            window.update_audio_amplitude(pipeline.get_rms_amplitude(chunk) * 15)
                        elif current_time - last_speech_time[0] > 1.5:
                            if state_machine.current_state == AssistantState.ACTIVE_LISTENING:
                                user_speech_logged[0] = False
                                state_machine.transition_to(AssistantState.ACTIVE_THINKING)
                                window.update_audio_amplitude(0.0)
                        
                        # 3. SMART BUFFERING & BANDWIDTH OPTIMIZATION
                        audio_buffer.extend(chunk)
                        threshold_bytes = 4800 if (current_time - last_speech_time[0] <= 2.0) else 32000
                        
                        if len(audio_buffer) >= threshold_bytes:
                            if not client.is_connected():
                                logger.warning("Gemini Live disconnected, initiating auto-reconnect...")
                                window.append_transcript("System: Connection dropped. Reconnecting...", is_user=False)
                                reconnected = await client.reconnect()
                                if reconnected:
                                    window.append_transcript("System: Reconnected successfully.", is_user=False)
                                else:
                                    await asyncio.sleep(1)
                                    continue
                            
                            success = await client.send_audio(bytes(audio_buffer))
                            audio_buffer.clear()
                            if not success:
                                await asyncio.sleep(0.1)
                    except queue.Empty:
                        await asyncio.sleep(0.01)
                    except Exception as e:
                        logger.error(f"audio_sender_error: {e}")
                        await asyncio.sleep(0.1)

            async def audio_receiver(): 
                while True:
                    try:
                        if not client.is_connected():
                            await asyncio.sleep(0.5)
                            continue
                        async for msg in client.receive_stream():
                            if msg.server_content and msg.server_content.model_turn:
                                for part in msg.server_content.model_turn.parts:
                                    if part.text:
                                        window.append_transcript(part.text, is_user=False)
                                        state_machine.transition_to(AssistantState.ACTIVE_SPEAKING)
                                        db.log_conversation(session_id, "myra", "text", part.text)
                                        chroma_manager.remember_fact(part.text, {"session_id": session_id, "sender": "myra"})
                                    if part.inline_data:
                                        # 24kHz 16-bit mono audio = 48,000 bytes per second
                                        audio_len_secs = len(part.inline_data.data) / 48000.0
                                        ai_speaking_until[0] = max(ai_speaking_until[0], time.time() + audio_len_secs + 0.5)
                                        state_machine.transition_to(AssistantState.ACTIVE_SPEAKING)
                                        window.update_audio_amplitude(0.5)
                                        try:
                                            await asyncio.to_thread(out_stream.write, part.inline_data.data)
                                        except Exception as e:
                                            logger.error(f"PyAudio write error: {e}")
                                        ai_speaking_until[0] = max(ai_speaking_until[0], time.time() + 0.5)
                    except Exception as e:
                        logger.error(f"audio_receiver loop error: {e}")
                    await asyncio.sleep(0.5)

            async def screen_streamer():
                from app.tools.vision import VisionTools
                import os
                import io
                from PIL import Image
                vision = VisionTools()
                
                while True:
                    try:
                        if getattr(window, 'is_screen_sharing', False) and client.is_connected():
                            os.makedirs("workspace", exist_ok=True)
                            await asyncio.to_thread(vision.take_screenshot, "live_screen.png")
                            screen_path = os.path.join(vision.workspace_root, "live_screen.png")
                            if os.path.exists(screen_path):
                                with Image.open(screen_path) as img:
                                    img.thumbnail((1024, 768))
                                    buf = io.BytesIO()
                                    img.save(buf, format="JPEG", quality=75)
                                    jpeg_data = buf.getvalue()
                                
                                await client.send_image(jpeg_data, mime_type="image/jpeg")
                                db.log_conversation(session_id, "user", "event", "[Screen Shared: Live frame streamed to Myra AI]")
                        await asyncio.sleep(3.0)
                    except Exception as e:
                        logger.error(f"screen_streamer error: {e}")
                        await asyncio.sleep(3.0)

            asyncio.create_task(audio_sender())
            asyncio.create_task(audio_receiver())
            asyncio.create_task(screen_streamer())
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
