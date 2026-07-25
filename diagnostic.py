import asyncio
import logging
import sys
import traceback
import structlog
import pyaudio

# Set up logging format to ensure full visibility of all logs and tracebacks
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = structlog.get_logger(__name__)

async def run_diagnostic():
    print("=" * 65)
    print("          MYRA VOICE SYSTEM END-TO-END DIAGNOSTIC          ")
    print("=" * 65)

    # -------------------------------------------------------------
    # Step 1: Check Configuration & API Key
    # -------------------------------------------------------------
    try:
        from app.config import settings
        print("\n[1/5] Validating Configuration...")
        if not settings.gemini_api_key:
            print("  [X] FAIL: GEMINI_API_KEY is missing or empty in .env!")
            return
        print(f"  [OK] GEMINI_API_KEY loaded (Key Prefix: {settings.gemini_api_key[:8]}...)")
    except Exception as e:
        print(f"  [X] FAIL: Error loading app config: {e}")
        traceback.print_exc()
        return

    # -------------------------------------------------------------
    # Step 2: Initialize Audio Microphone & Speaker Streams
    # -------------------------------------------------------------
    pipeline = None
    p = None
    out_stream = None
    try:
        print("\n[2/5] Initializing Audio Hardware (Mic Input & Speaker Output)...")
        from app.audio.pipeline import AudioPipeline
        pipeline = AudioPipeline(sample_rate=16000, frame_duration_ms=30)
        pipeline.start_listening()
        print("  [OK] sounddevice Microphone stream started (16kHz 16-bit mono PCM).")

        p = pyaudio.PyAudio()
        out_stream = p.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=24000,
            output=True
        )
        print("  [OK] PyAudio Speaker output stream initialized (24kHz 16-bit mono PCM).")
    except Exception as e:
        print(f"  [X] FAIL: Audio device initialization failed: {e}")
        traceback.print_exc()
        if pipeline:
            pipeline.stop_listening()
        return

    # -------------------------------------------------------------
    # Step 3: Connect to Gemini Live Client
    # -------------------------------------------------------------
    client = None
    try:
        print("\n[3/5] Connecting to Gemini Live API WebSocket...")
        from app.core.gemini_live_client import GeminiLiveClient
        client = GeminiLiveClient()
        print(f"  Target Model: {client.model_name}")

        connected = await client.connect()
        if not connected or not client.session:
            print("  [X] FAIL: Gemini Live Client connection attempt returned False.")
            return
        print("  [OK] Connected to Gemini Live API successfully!")
    except Exception as e:
        print(f"  [X] FAIL: Exception raised while connecting to Gemini Live API: {e}")
        traceback.print_exc()
        if pipeline:
            pipeline.stop_listening()
        return

    # -------------------------------------------------------------
    # Step 4 & 5: Send Greeting & Receive Audio Stream
    # -------------------------------------------------------------
    try:
        print("\n[4/5] Sending Text Greeting to Gemini Live Session...")
        greeting_text = "Hello Myra, this is a diagnostic test. Please reply with a spoken greeting."
        await client.session.send(input=greeting_text, end_of_turn=True)
        print(f"  [OK] Sent text prompt: '{greeting_text}'")

        # Concurrent task to stream microphone audio chunks to Gemini
        async def mic_stream_loop():
            try:
                while True:
                    chunk = await asyncio.to_thread(pipeline.get_audio_chunk, 0.1)
                    if chunk:
                        await client.send_audio(chunk)
                    await asyncio.sleep(0.01)
            except asyncio.CancelledError:
                pass
            except Exception as err:
                print(f"  [!] Mic Streaming error: {err}")

        mic_task = asyncio.create_task(mic_stream_loop())

        print("\n[5/5] Listening for Gemini Live Audio Response...")
        received_audio = False
        received_text = False
        total_audio_bytes = 0
        timeout_seconds = 12
        start_time = asyncio.get_event_loop().time()

        while asyncio.get_event_loop().time() - start_time < timeout_seconds:
            try:
                async for msg in client.receive_stream():
                    if msg.server_content and msg.server_content.model_turn:
                        for part in msg.server_content.model_turn.parts:
                            if part.text:
                                received_text = True
                                print(f"  [Gemini Text Response]: {part.text}")
                            if part.inline_data:
                                received_audio = True
                                pcm_bytes = part.inline_data.data
                                total_audio_bytes += len(pcm_bytes)
                                print(f"  [Gemini Audio Response]: Received {len(pcm_bytes)} bytes of PCM audio. Playing...")
                                out_stream.write(pcm_bytes)

                    if msg.server_content and msg.server_content.turn_complete:
                        print("  [OK] Gemini signal: turn complete.")
                        break

                if received_audio or received_text:
                    break

            except Exception as recv_err:
                print(f"  [X] Error receiving from stream: {recv_err}")
                traceback.print_exc()
                break

        mic_task.cancel()

        print("\n" + "=" * 65)
        if received_audio:
            print(f"DIAGNOSTIC SUCCESS: Audio received ({total_audio_bytes} bytes) and played!")
        elif received_text:
            print("DIAGNOSTIC PARTIAL SUCCESS: Text received, but no audio inline data.")
        else:
            print("DIAGNOSTIC FAILURE: No response received within timeout.")
        print("=" * 65)

    except Exception as e:
        print(f"\n[X] FAIL: Diagnostic execution error: {e}")
        traceback.print_exc()

    finally:
        print("\nCleaning up resources...")
        if pipeline:
            pipeline.stop_listening()
        if client:
            pass # await client.disconnect() missing from GeminiLiveClient
        if out_stream:
            out_stream.stop_stream()
            out_stream.close()
        if p:
            p.terminate()
        print("Diagnostic run completed.")

if __name__ == "__main__":
    asyncio.run(run_diagnostic())
