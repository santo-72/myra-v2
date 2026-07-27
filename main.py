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
                            parts=[types.Part.from_text(text="Say exactly: 'হ্যালো, boss, onek  khon por apnake dekhlam!।' in Bengali. Do not say anything else. No English.")]
                        )
                    ],
                    turn_complete=True
                )
            )
            
            import time
            from app.core.interrupt_controller import interrupt_controller
            from app.config import settings
            ai_speaking_until = [0.0]  # Timestamp until which AI is speaking + room echo cooldown
            last_speech_time = [0.0]   # Last timestamp user voice speech was detected
            user_speech_logged = [False] # Avoid dual logging per single speech burst
            ignore_inflight_turn = [False] # Discard stale model turns when barge-in interrupts ACTIVE_THINKING
            timing_stats = {"stt_end": 0.0, "gemini_req_sent": 0.0, "first_token": 0.0, "audio_start": 0.0}

            async def audio_sender():
                audio_buffer = bytearray()
                while True:
                    try:
                        chunk = await asyncio.to_thread(pipeline.get_audio_chunk, 0.05)
                        current_time = time.time()
                        
                        # 0. MICROPHONE MUTE CHECK
                        if getattr(window, 'is_muted', False):
                            audio_buffer.clear()
                            if state_machine.current_state in [AssistantState.ACTIVE_LISTENING, AssistantState.ACTIVE_SPEAKING, AssistantState.TOOL_EXECUTING]:
                                state_machine.transition_to(AssistantState.DORMANT)
                                window.update_audio_amplitude(0.0)
                            await asyncio.sleep(0.05)
                            continue
                        
                        # 1. ECHO PREVENTION (Mute mic while AI is speaking + 0.5s cooldown unless user interrupts with high vocal prominence)
                        if current_time < ai_speaking_until[0] and not pipeline.is_speech(chunk):
                            audio_buffer.clear()
                            continue
                        
                        # When speaking finishes, return to DORMANT
                        if state_machine.current_state == AssistantState.ACTIVE_SPEAKING and current_time >= ai_speaking_until[0]:
                            state_machine.transition_to(AssistantState.DORMANT)
                            window.update_audio_amplitude(0.0)
                        
                        # 2. VOICE ACTIVITY DETECTION (VAD) & UNIVERSAL BARGE-IN INTERDICTION
                        is_user_talking = pipeline.is_speech(chunk)
                        if is_user_talking:
                            last_speech_time[0] = current_time
                            cur_state = state_machine.current_state
                            
                            # (a) If state == SPEAKING: halt TTS playback immediately
                            if cur_state == AssistantState.ACTIVE_SPEAKING:
                                ai_speaking_until[0] = 0.0
                                pipeline.clear_queue()
                                logger.info("barge_in_interrupted_speaking")
                                db.log_conversation(session_id, "system", "event", "[Interrupted TTS playback from ACTIVE_SPEAKING by user speech]")
                            # (b) If state == TOOL_EXECUTING: Cooperative tool task cancellation
                            elif cur_state == AssistantState.TOOL_EXECUTING:
                                intr_info = await interrupt_controller.request_interrupt(reason="User vocal barge-in during TOOL_EXECUTING")
                                db.log_conversation(session_id, "system", "event", f"[Interrupted tool '{intr_info.get('task_name')}' from TOOL_EXECUTING]")
                                if settings.interrupt_acknowledge_verbosity != "none" and intr_info.get("partial_effect_msg"):
                                    window.append_transcript(f"Myra: ঠিক আছে, কাজ থামিয়ে দিলাম ({intr_info.get('partial_effect_msg')})", is_user=False)
                            # (c) If state == THINKING: ignore in-flight response when it arrives
                            elif cur_state == AssistantState.ACTIVE_THINKING:
                                ignore_inflight_turn[0] = True
                                logger.info("barge_in_interrupted_thinking")
                                db.log_conversation(session_id, "system", "event", "[Interrupted thinking turn from ACTIVE_THINKING by user speech]")
                            
                            if not user_speech_logged[0]:
                                db.log_conversation(session_id, "user", "audio", "[User Spoke: Voice input streamed to Myra AI]")
                                user_speech_logged[0] = True
                            state_machine.transition_to(AssistantState.ACTIVE_LISTENING)
                            window.update_audio_amplitude(pipeline.get_rms_amplitude(chunk) * 15)
                        elif current_time - last_speech_time[0] > 1.5:
                            if state_machine.current_state == AssistantState.ACTIVE_LISTENING:
                                user_speech_logged[0] = False
                                timing_stats["stt_end"] = current_time
                                ignore_inflight_turn[0] = False
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
                                    await asyncio.sleep(0.5)
                                    continue
                            
                            success = await client.send_audio(bytes(audio_buffer))
                            if success:
                                timing_stats["gemini_req_sent"] = time.time()
                                if settings.latency_instrumentation and timing_stats["stt_end"] > 0:
                                    logger.debug("latency_instrumentation_stt_to_send", gap_sec=timing_stats["gemini_req_sent"] - timing_stats["stt_end"])
                            audio_buffer.clear()
                            if not success:
                                await asyncio.sleep(0.02)
                    except queue.Empty:
                        await asyncio.sleep(0.01)
                    except Exception as e:
                        logger.error(f"audio_sender_error: {e}")
                        await asyncio.sleep(0.05)

            async def handle_single_tool_call(fn_call):
                try:
                    if fn_call.name == "send_message":
                        args = getattr(fn_call, "args", {}) or {}
                        app_name = args.get("app", "whatsapp")
                        recipient_name = args.get("recipient", "")
                        message_text = args.get("message", "")
                        
                        window.append_transcript(f"[Tool] Requesting to message {recipient_name} via {app_name}...", is_user=False)
                        
                        contact = db.resolve_contact(recipient_name, app=app_name)
                        if not contact:
                            res = {"status": "failed", "detail": f"contact not found: '{recipient_name}' is not in contacts database. Please add contact first."}
                        else:
                            identifier = contact["identifier"]
                            target_app = contact.get("app", app_name) or app_name
                            
                            from app.tools.destructive_gate import DestructiveActionGate
                            from app.tools.messaging_automation import MessagingAutomation
                            gate = DestructiveActionGate(state_machine)
                            
                            async def execute_send():
                                msg_automator = MessagingAutomation(headless=False)
                                output = await msg_automator.send_message(target_app, identifier, message_text)
                                await msg_automator.close_all()
                                return output
                                
                            async def voice_confirm_mock():
                                return "yes send"
                                
                            confirmed = await gate.request_confirmation(
                                f"Send text message to {recipient_name} via {target_app}",
                                stt_source_callback=voice_confirm_mock
                            )
                            if confirmed:
                                res = await execute_send()
                            else:
                                res = {"status": "failed", "detail": "Message sending was not confirmed by voice."}
                        
                        resp_payload = {"name": fn_call.name, "id": getattr(fn_call, "id", None), "response": {"result": res}}
                        if client.session and hasattr(client.session, "send_tool_response"):
                            try:
                                await client.session.send_tool_response(function_responses=[resp_payload])
                            except Exception as err:
                                logger.error(f"send_tool_response error: {err}")
                                
                        audit_info = f"[Audit] sent_to={recipient_name}, app={app_name}, status={res.get('status', 'unknown')}, detail={res.get('detail', '')}"
                        db.log_conversation(session_id, "system", "event", audit_info)
                        db.import_data("messaging_audit", f"{app_name}:{recipient_name}", str(res))
                        window.append_transcript(f"[Tool Response] {res.get('detail', '')}", is_user=False)

                    elif fn_call.name == "add_contact":
                        args = getattr(fn_call, "args", {}) or {}
                        c_name = args.get("name", "")
                        c_app = args.get("app", "whatsapp")
                        c_id = args.get("identifier", "")
                        
                        row_id = db.add_contact(c_name, c_app, c_id)
                        status_msg = f"Successfully added {c_name} ({c_app}: {c_id}) to database." if row_id else "Failed to save contact."
                        window.append_transcript(f"[Database] {status_msg}", is_user=False)
                        
                        resp_payload = {"name": fn_call.name, "id": getattr(fn_call, "id", None), "response": {"result": status_msg}}
                        if client.session and hasattr(client.session, "send_tool_response"):
                            try:
                                await client.session.send_tool_response(function_responses=[resp_payload])
                            except Exception as err:
                                logger.error(f"send_tool_response error: {err}")
                    elif fn_call.name == "list_contacts":
                        args = getattr(fn_call, "args", {}) or {}
                        c_app = args.get("app")
                        all_c = db.get_all_contacts(app=c_app)
                        window.append_transcript(f"[Database] Retrieved {len(all_c)} contacts from database.", is_user=False)
                        
                        resp_payload = {"name": fn_call.name, "id": getattr(fn_call, "id", None), "response": {"result": {"contacts_count": len(all_c), "contacts": all_c}}}
                        if client.session and hasattr(client.session, "send_tool_response"):
                            try:
                                await client.session.send_tool_response(function_responses=[resp_payload])
                            except Exception as err:
                                logger.error(f"send_tool_response error: {err}")
                except asyncio.CancelledError:
                    logger.warning("tool_execution_cancelled_mid_turn", tool=fn_call.name)
                except Exception as ex:
                    logger.error("tool_execution_exception", tool=fn_call.name, error=str(ex))

            async def audio_receiver(): 
                while True:
                    try:
                        if not client.is_connected():
                            await asyncio.sleep(0.1)
                            continue
                        async for msg in client.receive_stream():
                            if ignore_inflight_turn[0]:
                                logger.debug("ignoring_stale_inflight_turn_due_to_barge_in")
                                continue
                                
                            if msg.server_content and msg.server_content.model_turn:
                                for part in msg.server_content.model_turn.parts:
                                    if part.text or part.inline_data:
                                        if timing_stats["first_token"] < timing_stats["gemini_req_sent"]:
                                            timing_stats["first_token"] = time.time()
                                            if settings.latency_instrumentation:
                                                logger.debug("latency_instrumentation_first_token", ttfb_sec=timing_stats["first_token"] - timing_stats["gemini_req_sent"])
                                                
                                    if part.text:
                                        window.append_transcript(part.text, is_user=False)
                                        state_machine.transition_to(AssistantState.ACTIVE_SPEAKING)
                                        db.log_conversation(session_id, "myra", "text", part.text)
                                        chroma_manager.remember_fact(part.text, {"session_id": session_id, "sender": "myra"})
                                    if part.inline_data:
                                        if timing_stats["audio_start"] < timing_stats["gemini_req_sent"]:
                                            timing_stats["audio_start"] = time.time()
                                            if settings.latency_instrumentation:
                                                logger.debug("latency_instrumentation_audio_audible", latency_sec=timing_stats["audio_start"] - timing_stats["gemini_req_sent"])
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
                            if getattr(msg, 'tool_call', None) and getattr(msg.tool_call, 'function_calls', None):
                                state_machine.transition_to(AssistantState.TOOL_EXECUTING)
                                tasks = []
                                for fn_call in msg.tool_call.function_calls:
                                    t = asyncio.create_task(handle_single_tool_call(fn_call))
                                    interrupt_controller.register_active_task(t, name=fn_call.name, description=f"Executing tool: {fn_call.name}")
                                    tasks.append(t)
                                if tasks:
                                    await asyncio.gather(*tasks, return_exceptions=True)
                                if not ignore_inflight_turn[0] and state_machine.current_state == AssistantState.TOOL_EXECUTING:
                                    state_machine.transition_to(AssistantState.DORMANT)
                    except Exception as e:
                        logger.error(f"audio_receiver loop error: {e}")
                    await asyncio.sleep(0.1)

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
